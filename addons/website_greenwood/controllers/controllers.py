# -*- coding: utf-8 -*-
import logging
import json
import tempfile
from urlparse import urljoin

import openerp
from openerp import http, SUPERUSER_ID
from openerp.http import request
from openerp.addons.web.controllers.main import Home, ensure_db, Session
from openerp.addons.website.controllers.main import Website
from openerp.addons.website_sale.controllers.main import website_sale
from openerp.addons.website_greenwood.main import Config, GWCalender
from openerp.addons.website_greenwood.main import _datetime_from_string, _months_list, _days_number_list

import werkzeug.utils
from werkzeug.datastructures import ImmutableMultiDict

import swiftclient

cal = GWCalender()

_logger = logging.getLogger(__name__)


def swift():
    config = Config()
    return config.swift()
    # username = 'admin'
    # password = 'admin'
    # authurl = 'http://192.168.2.249:8080/auth/v1.0/'
    # preauthurl = 'http://192.168.2.249:8080/v1/AUTH_admin/'
    # preauthtoken = 'AUTH_tk6077f64e7fe14dc9bb69f20be778297c'
    # swift = swiftclient.client.Connection(user=username,
    #                                      key=password,
    #                                      authurl=authurl,
    #                                      preauthurl=preauthurl,
    #                                      preauthtoken=preauthtoken,
    #                                      retries=3)
    # return swift

def swift_headers():
    return {

    }

def _swift_config():
    """ TODO: Introduce env switch """
    return dict(container='gw', tempcontainer='gwtemp',
               storageurl='http://192.168.2.249:8080/v1/AUTH_admin/gw',
               tempstorageurl='http://192.168.2.249:8080/v1/AUTH_admin/gwtemp')

def _saveFile(ufile):
    res = swift_upload(ufile, delete_file_from_temp)
    if res:
        return dict(res)
    else:
        return None

def swift_upload(fn, fd, cb=None):
    container, response, filename, filedata = 'gw', dict(), fn, fd
    # filedata = ufile.read()
    # ufile.close()
    filepath = urljoin(_swift_config()['storageurl'], '?%s' % filename)
    try:
        swift().put_object(container, filename, filedata, response_dict=response)
        _logger.info(">>>> put response %r" % response)
        if response['status'] == 201:
            # d = {'filename': filename, 'filepath': filepath}
            d = filename, filepath
            # remove the temp file
            if cb:
                r = cb(filename)
                if r and r['status'] == 200:
                    # return "%s" % d
                    return d
                else:
                    _logger.debug("Couldn't delete file" % filename)
                    # return "%s" % d
                    return d
            return d
    except Exception as e:
        _logger.debug("Failed file upload: %r" % e)
        return None

def delete_file_from_temp(filename):
    container, response = 'gwtemp', dict()
    url = _swift_config()['tempstorageurl']
    try:
        swift.delete_object(container, filename, response_dict=response)
        return response
    except Exception as e:
        _logger.debug("File delete failed: %r" % e)
        return None

def _saveFiles(mapping, key):
    print("Saving files>>>>>>>> %r" % mapping)
    """ :param mapping: Must be of type werkzeug.datastructures.MultiDict() """
    if type(mapping) != ImmutableMultiDict:
        raise NotImplementedError("Only mapping of type MultiDict is supported")
    files = mapping.getlist(key)
    res = []
    for f in files:
        _logger.info("Got a file>>>>>>>> %r" % f)
        filename = f.filename
        filedata = f.read()
        # fn = swift_upload(f, cb=delete_file_from_temp)
        # fn = swift_upload(filename, filedata, cb=delete_file_from_temp)
        fn = swift_upload(filename, filedata)
        if fn:
            # Add fn
            res.append(fn)
            f.close()
        else:
            return None
    return dict(res)


class WebsiteGreenwood(http.Controller):
    _cp_path = '/'

    @http.route('/signup', type='http', website=True, auth="none")
    def signup(self, redirect=None, **kw):

        if request.httprequest.method == 'GET':
            return request.render('web.signup')

        # Authenticate the user immediately
        uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
        if uid is not False:
            request.params['login_success'] = True
            if not redirect:
                redirect = '/'
            return http.redirect_with_hash(redirect)

    @http.route('/profile', type="http", auth="user", website=True)
    def profile(self, redirect='None'):
        """ View user profile """
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        if not uid:
            redirect = '?%s' % 'redirect=/profile'
            werkzeug.utils.redirect('/web/login%s' % redirect, 303)

        gw_account_obj = pool['res.partner']
        partner_id = gw_account_obj._get_partner_id(cr, SUPERUSER_ID, uid, context=context)
        profile = gw_account_obj.browse(cr, SUPERUSER_ID, partner_id, context=context)
        values = {
            'bvn': profile.bvn,
            'address': profile.street,
            'job_position': profile.function,
            'userid': profile.user_id.id,
            'phone': profile.phone,
            'debit_date': profile.debit_date,
            'profile': profile,
        }
        _logger.info(">>> values %r" % values)
        company_type = profile.company_type
        if company_type == 'person':
            values['identity_id'] = profile.identity_id
            values['empname'] = profile.empname
            values['payslips'] = profile.payslips
            values['mexpenses'] = profile.mexpenses
            values['tenancy'] = profile.tenancy
            return request.render('theme_bootswatch.profile', values)
        else:
            values['companyname'] = profile.companyname
            values['company_reg_id'] = profile.company_reg_id
            return request.render('theme_bootswatch.profile', values)

    @http.route('/profile/add', type='http', website=True, auth="user")
    def add(self, redirect=None, **kw):
        """ Add new profile """
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        # greenwood_account_obj = pool['website_greenwood.account']
        greenwood_account_obj = pool['res.partner']
        users = request.registry.get('res.users')
        res_partner_obj = pool.get('res.partner')
        redirect = request.params.get('redirect')
        if request.httprequest.method == 'POST':
            partner = users.browse(cr, SUPERUSER_ID, uid, context=context).partner_id
            params = request.params.copy()
            print("\n>>>POST params %r" % params)
            params['uid'] = uid
            params['partner_id'] = partner.id
            account_type = request.params['company_type']
            profile = self._create_profile(account_type, request, params)

            if profile:
                _logger.info("\n>>> Profile written successfully")
                if not redirect:
                    redirect = '/profile'
                return http.redirect_with_hash(redirect)
            params['error'] = _('Some fields fail validation')
            return request.render('theme_bootswatch.account_verify', params)
        values = {
            'uid': uid,
            'res_partner': res_partner_obj.browse(cr, SUPERUSER_ID, 44, context=context),
            'greenwood_account': greenwood_account_obj,
            'cyear': cal.current_year(),
            'months_short': _months_list('short'),
            'days': _days_number_list(),
        }
        print "\n\n>>>>res_partner\n", values['res_partner'].company_type
        return request.render('theme_bootswatch.account_verify', values)

    def _create_profile(self, account_type, request, params):
        _logger.info("website_greenwood: Creating new profile")
        print("\n>>>website_greenwood: Creating new profile")
        if account_type == 'person':
            return self.profile_individual(request, params)
        elif account_type == 'company':
            return self.profile_corporate(request, params)

    def profile_individual(self, request, params):
        cr, uid, context = request.cr, request.uid, request.context
        gw_account_obj = request.registry.get('res.partner')
        # Accepts data in '%Y-%m-%d %H:%M:%S' format
        idate = '-'.join([params['cyear'], params['debit_date_month'],
            params['debit_date_day']
        ])
        debit_date = _datetime_from_string(idate)

        partner_id = params['partner_id']
        identity_id = "%s" % _saveFile(request.params['identity_id'])
        tenancy = "%s" % _saveFile(request.params['tenancy'])
        payslips = "%s" % _saveFiles(request.params['payslips'])
        approval_status = gw_account_obj.browse(cr, SUPERUSER_ID, partner_id, context=context).approval_status

        values = {
            'company_type': 'person',
            'bvn': request.params['bvn'],
            'uid': uid,
            'debit_date': debit_date,
            'empname': request.params['empname'],
            'companyname': 'None',
            'identity_id': identity_id,
            'company_reg_id': 'None',
            'payslips': payslips,
            'mexpenses': request.params['mexpenses'],
            'tenancy': tenancy,
            'address': request.params['address'],
            'job_position': request.params['job_position'],
            'approval_status': approval_status,
        }
        return gw_account_obj.write(cr, SUPERUSER_ID, [partner_id], values, context=context)

    def profile_corporate(self, request, params):
        """ A corporate account as corporate """
        cr, uid, context = request.cr, request.uid, request.context
        greenwood_account_obj = request.registry.get('res.partner')
        # Accepts data in '%Y-%m-%d %H:%M:%S' format
        idate = '-'.join([params['cyear'], params['debit_date_month'],
            params['debit_date_day']
        ])
        debit_date = _datetime_from_string(idate)

        partner_id = params['partner_id']
        domain = [('id', '=', params['partner_id'])]
        _logger.info(">>> %s" % domain)
        approval_status = greenwood_account_obj.browse(cr, SUPERUSER_ID, partner_id, context=context).approval_status

        values = {
            'company_type': 'company',
            'bvn': request.params['bvn'],
            'user_id': uid,
            'debit_date': debit_date,
            'empname': 'None',
            'companyname': request.params['companyname'],
            'identity_id': 'None',
            'company_reg_id': request.params['company_reg_id'],
            'payslips': 'None',
            'mexpenses': float(0.0),
            'tenancy': 'None',
            # 'address': request.params['address'],
            'street': request.params['address'],
            #'job_position': request.params['job_position'],
            'function': request.params['job_position'],
            # 'approval_status': greenwood_account_obj.credit_status([uid]),
            'approval_status': approval_status,
            'is_company': 't',
            'notify_email': 'none',
        }
        return greenwood_account_obj.write(cr, SUPERUSER_ID, [partner_id], values, context=context)
        # return greenwood_account_obj.create(cr, uid, values, context=context)

    @http.route('/profile/<int:user_id>/edit', auth="user", type="http", website=True)
    def edit(self, user_id, redirect=None, **post):
        """ Greenwood profile edit """
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        if user_id != uid:
            return request.redirect('/page/401', code=401)

        greenwood_account_obj = pool['res.partner']
        partner_id = greenwood_account_obj._get_partner_id(cr, SUPERUSER_ID, uid, context=context)
        profile = greenwood_account_obj.browse(cr, SUPERUSER_ID, partner_id, context=context)
        _logger.info("\n>>> profile %r" % profile)

        if request.httprequest.method == 'POST':
            params = request.params.copy()
            greenwood_account_obj.write(params)
            redirect = '/profile'
            return http.redirect_with_hash(redirect)
        # For Get Load the model and return values to client
        values = {
            'bvn': profile.bvn,
            'address': profile.street,
            'job_position': profile.function,
            'userid': profile.user_id.id,
            'phone': profile.phone,
            'debit_date': profile.debit_date, # edit is not allowed when a customer is currently on a contract
        }
        _logger.info(">>> values %r" % values)
        company_type = profile.company_type
        if company_type == 'person':
            values['identity_id'] = profile.identity_id
            values['empname'] = profile.empname
            values['payslips'] = profile.payslips
            values['mexpenses'] = profile.mexpenses
            values['tenancy'] = profile.tenancy
            return request.render('theme_bootswatch.profile_edit_person', values)
        else:
            values['companyname'] = profile.companyname
            values['company_reg_id'] = profile.company_reg_id
            return request.render('theme_bootswatch.profile_edit_company', values)


class GreenwoodOrderController(website_sale):

    # @http.route()
    # def cart(self, **post):
    #    print "\n\n>>>>>>>>/shop/cart override>>>>>\n"
    #    print "\nrequest.path is", request.httprequest.path
    #    print "\nrequest.request is", request.httprequest
        # _logger.info("/shop/cart override")
        # If user is not logged in, redirect to /verify?redirect=/shop/cart
        # if not request.session.uid:
        #    qp = '?'
        #    return werkzeug.utils.redirect('/verify', 303)
        # return super(GreenwoodOrderController, self).cart(post=post)
    #    pass

    @http.route()
    def checkout(self, **post):
        cstatuses = ['pending', 'accepted']
        if request.session.uid and request.session.credit_status not in cstatuses:
            redirect = '?redirect=%s' % request.httprequest.path
            return werkzeug.utils.redirect('/profile/add{0}'.format(redirect))
        else:
            return werkzeug.utils.redirect('/web/login', 303)
            # return super(GreenwoodOrderController, self).checkout(post=post)


# class GreenwoodSession(Session):
#    @http.route('/web/session/logout', auth='none', type='http')
#    def logout(self, redirect='/web'):
#        ir_config_id = request.registry['ir.config_parameter'].search(request.cr, SUPERUSER_ID, [('key','=','web.base.url')])
#        base_url = request.registry['ir.config_parameter'].browse(request.cr, SUPERUSER_ID, ir_config_id[0], request.context).value
#        request.session.logout(keep_db=True)
#        return werkzeug.utils.redirect(base_url, 303)


# class GreenwoodWebLogin(Home):
    # @http.route()
    # def web_login(self, redirect='None', *args, **kw):
    #    ir_config_id = request.registry['ir.config_parameter'].search(request.cr, SUPERUSER_ID, [('key','=','web.base.url')])
    #    base_url = request.registry['ir.config_parameter'].browse(request.cr, SUPERUSER_ID, ir_config_id[0], request.context).value
    #    r = super(GreenwoodWebLogin, self).web_login(redirect=redirect, *args, **kw)
        # Get website_greenwood model for this user
        # get user's credit status
        # set request.session.credit_status


class Service(http.Controller):
    @http.route("/file/upload/<string:field>", auth="user")
    def uploadFileToTemp(self, field, **post):
        """ Temp location is a temp container storage location on
        swift """
        # print "\n>>Uploaded files", request.httprequest.files
        print "\n>>Uploaded files", post
        ufile = post[field]
        filename = ufile.filename
        filedata = ufile.read()
        ufile.close()
        # namedfile = tempfile.mkstemp()
        # namedfile.write(base64.decodeString(filedata))
        container, response, result = 'gwtemp', dict(), {}
        try:
            swift().put_object(container=container, obj=filename, contents=filedata, response_dict=response)
            mime = 'application/json'
            response_headers = response['headers']
            result['status'] = response['status']
            if response['status'] == 201:
                result['message'] = 'OK'
            else:
                result['message'] = response['reason']
            jsonobj = json.dumps(result)
            return http.Response(jsonobj, status=result['status'], headers=[('Content-Type', mime)])
        except Exception as e:
            print("Failed upload: %r" % e)
            result['status'] = 500
            result['message'] = e.message
            return http.Response(json.dumps(result), status=result['status'])

    @http.route("/files/upload/<string:field>", auth="user")
    def uploadFilesToTemp(self, field, **post):
        print "\n>>Uploaded files", post
        print "\n>>Request.files", request.httprequest.files
        files = request.httprequest.files
        _logger.info("\n>>> File storage files %s" % type(files))
        res = _saveFiles(files, field)
        mime, result = 'application/json', {}
        if res:
            result['message'] = 'OK'
            result['status'] = 200
        else:
            _logger.info("res error %s" % res)
            result['message'] = 'error'
            result['status'] = 502
        jsonobj = json.dumps(result)
        return http.Response(jsonobj, status=result['status'], headers=[('Content-Type', mime)])

    @http.route("/file/delete")
    def deleteFileFromTemp(self):
        pass

