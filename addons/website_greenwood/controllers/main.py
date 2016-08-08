# -*- coding: utf-8 -*-
import logging
import json
import ast
import tempfile
from urlparse import urljoin
import urllib2

import openerp
from openerp import http, SUPERUSER_ID
from openerp.http import request
from openerp.tools.translate import _
from openerp.addons.web.controllers.main import Home, ensure_db, Session
from openerp.addons.website.controllers.main import Website
from openerp.addons.website_sale.controllers.main import website_sale
from openerp.addons.auth_signup.controllers.main import AuthSignupHome
from openerp.addons.auth_signup.res_users import SignupError
from openerp.addons.website_greenwood.main import Config, GWCalender, Swift
from openerp.addons.website_greenwood.main import \
    _datetime_from_string, _months_list, _days_number_list, \
    SWIFT_GW_CONTAINER, SWIFT_GWTEMP_CONTAINER, SWIFT_WEB_CONTAINER

import werkzeug.utils
from werkzeug.datastructures import ImmutableMultiDict

import swiftclient

cal = GWCalender()
config = Config()

_logger = logging.getLogger(__name__)

db_list = http.db_list

db_monodb = http.db_monodb

def swift():
    return config.swift()

def swift_headers():
    return {

    }

def _swift_config():
    """ TODO: Introduce env switch """
    return dict(container='gw', tempcontainer='gwtemp',
               storageurl='http://192.168.2.249:8080/v1/AUTH_admin/gw',
               tempstorageurl='http://192.168.2.249:8080/v1/AUTH_admin/gwtemp')

def _saveFile(ufile):
    filename = ufile.filename
    filedata = ufile.read()
    # res = swift_upload(ufile, delete_file_from_temp)
    res = swift_upload(filename, filedata, delete_file_from_temp)
    if res:
        return dict(res)
    else:
        return None

def _swift_request(fn):
    """ Copies file from one Container into another """
    obj_name = urllib2.quote(fn)
    swift_params = config.get_swift_param('token', 'storageurl')
    _logger.info("\n>>>> swift params %s" % swift_params)
    source = SWIFT_GWTEMP_CONTAINER + '/%s' % obj_name
    dest = SWIFT_GW_CONTAINER + '/%s' % obj_name
    url = swift_params['storageurl'] + '/%s' % dest
    headers = {
        'X-Auth-Token': swift_params['token'],
        'X-Copy-From': '/%s' % source,
        'Content-Length': 0
    }
    _logger.info("\n>>>> headers %s" % headers)
    _logger.info("\n>>>> url %s" % url)

    request = urllib2.Request(url, None, headers)
    request.get_method = lambda: 'PUT'
    done, res = False, None
    try:
        res = urllib2.urlopen(request)
        done = True
    except urllib2.HTTPError as e:
        res = e.read()
        _logger.info(">>> swift error %r" % res)
        e.close()
        return None

    result = res.read()
    _logger.info("\n>>>> no exception result %s" % result)
    res.close()
    filepath = urljoin(swift_params['storageurl'], '/gw/%s' % obj_name)
    _logger.info("\n>>>> return values %r" % [obj_name, filepath])
    return obj_name, filepath

def _save_files_perm(filenames):
    res = []
    for fn in filenames:
        tup = _swift_request(fn)
        if tup:
            res.append(tup)
        else:
            return None
    d = json.dumps(dict(res))
    return ast.literal_eval(d)

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
    """ :param mapping: Must be of type werkzeug.datastructures.MultiDict() """
    if type(mapping) != ImmutableMultiDict:
        raise NotImplementedError("Only mapping of type MultiDict is supported")

    files = mapping.getlist(key)
    res = []
    for f in files:
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

def _get_swift_file(filename):
    """ @todo Male filename a list """
    r = swift.get_object(SWIFT_WEB_CONTAINER, filename, response_dict=gresp)
    _logger.info("\n>>>> swift get response %r" % r)
    return r

def _validate_form_person():
    pass

def _validate_form_company():
    pass


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

        verb = 'Update' if not profile.bvn else 'Edit'
        values = {
            'bvn': profile.bvn,
            'address': profile.street,
            'job_position': profile.function,
            'userid': profile.user_id.id,
            'phone': profile.phone,
            'debit_date': profile.debit_date,
            'profile': profile,
            'verb': verb,
        }
        _logger.info(">>> values %r" % values)
        company_type = profile.company_type
        if company_type == 'person':
            values['identity_id'] = profile.identity_id
            values['empname'] = profile.empname
            values['payslips'] = profile.payslips
            values['mexpenses'] = profile.mexpenses
            values['tenancy'] = profile.tenancy
            return request.render('theme_houzz.profile', values)
        else:
            values['companyname'] = profile.companyname
            values['company_reg_id'] = profile.company_reg_id
            return request.render('theme_houzz.profile_company', values)

    @http.route('/profile/add', type='http', website=True, auth="user")
    def add(self, redirect=None, **kw):
        """ Add new profile """
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        greenwood_account_obj = pool['res.partner']
        users = request.registry.get('res.users')
        res_partner_obj = pool.get('res.partner')
        redirect = request.params.get('redirect')
        values = {
            'uid': uid,
            'cyear': cal.current_year(),
            'months_short': _months_list('short'),
            'days': _days_number_list(),
        }

        if request.httprequest.method == 'POST':
            partner = users.browse(cr, SUPERUSER_ID, uid, context=context).partner_id
            params = request.params.copy()
            print("\n>>>POST params %r" % params)
            params['uid'] = uid
            params['partner_id'] = partner.id
            account_type = request.params['company_type']
            print "\n>>Request.files", request.httprequest.files
            files = request.httprequest.files

            values['company_type'] = account_type
            values['bvn'] = params['bvn']
            values['empname'] = params['empname']
            values['mexpenses'] = params['mexpenses']
            values['address'] = params['address']
            values['job_position'] = params['job_position']
            values['debit_date_month'] = params['debit_date_month']
            values['debit_date_day'] = params['debit_date_day']
            values['gw_idfn'] = params['gw_idfn']
            values['gw_pyslpfn'] = params['gw_pyslpfn']
            values['gw_tncyfn'] = params['gw_tncyfn']
            values['companyname'] = params['companyname']
            values['company_reg_id'] = params['company_reg_id']

            # If account_type is individual and none of gw_* is set, send
            # back error result
            gw_idfn, gw_pyslpfn, gw_tncyfn = params['gw_idfn'] or False, params['gw_pyslpfn'] or False, params['gw_tncyfn'] or False
            fileFields = [gw_idfn, gw_pyslpfn, gw_tncyfn]

            nofile = False
            for r in range(1, 4):
                for f in fileFields:
                    if f is False:
                        nofile = True
                        break
                else:
                    continue

            if account_type == 'person' and nofile:
                values['error'] = 'Please attach the required files'
                return request.render('theme_houzz.account_verify', values)

            profile = self._create_profile(account_type, request, params)

            if profile:
                _logger.info("\n>>> Profile written successfully")
                qs = request.httprequest.query_string
                if 'redirect=' in qs:
                    redirect = qs.split('=')[1]
                if not redirect:
                    redirect = '/profile'
                return http.redirect_with_hash(redirect)
            params['error'] = _('Some fields fail validation')
            return request.render('theme_houzz.account_verify', params)

        values['res_partner'] = res_partner_obj.browse(cr, SUPERUSER_ID, 44, context=context),
        values['greenwood_account'] = greenwood_account_obj

        return request.render('theme_houzz.account_verify', values)

    def _create_profile(self, account_type, request, params):
        _logger.info("website_greenwood: Creating new profile")
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
        identity_id = "%s" % _save_files_perm([params['gw_idfn']])
        tenancy = "%s" % _save_files_perm([params['gw_tncyfn']])
        payslips = "%s" % _save_files_perm([params['gw_pyslpfn']])
        approval_status = gw_account_obj.browse(cr, SUPERUSER_ID, partner_id, context=context).approval_status

        values = {
            'company_type': 'person',
            'bvn': request.params['bvn'],
            'user_id': uid,
            'debit_date': debit_date,
            'empname': request.params['empname'],
            'companyname': 'None',
            'identity_id': identity_id,
            'phone': params['phone'],
            'company_reg_id': 'None',
            'payslips': payslips,
            'total_income': float(params['total_income']),
            'mexpenses': float(request.params['mexpenses']),
            'tenancy': tenancy,
            'street': request.params['address'],
            'function': request.params['job_position'],
            'approval_status': 'pending',
            'notify_email': 'none',
        }
        request.session.credit_status = 'pending'
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
            'phone': params['phone'],
            'payslips': 'None',
            'total_income': float(0.0),
            'mexpenses': float(0.0),
            'tenancy': 'None',
            # 'address': request.params['address'],
            'street': request.params['address'],
            #'job_position': request.params['job_position'],
            'function': request.params['job_position'],
            # 'approval_status': greenwood_account_obj.credit_status([uid]),
            'approval_status': 'pending',
            'is_company': 't',
            'notify_email': 'none',
        }
        request.session.credit_status = 'pending'
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
            _logger.info("\n>>> params %r" % params)
            values = params
            greenwood_account_obj.write(cr, SUPERUSER_ID, [partner_id], values, context=context)
            # greenwood_account_obj.write(params)
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
            return request.render('theme_houzz.profile_edit_person', values)
        else:
            values['companyname'] = profile.companyname
            values['company_reg_id'] = profile.company_reg_id
            return request.render('theme_houzz.profile_edit_company', values)


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
        _logger.info("User credit status %s" % request.session.credit_status)
        if request.session.uid and request.session.credit_status not in cstatuses:
            redirect = '?redirect=%s' % request.httprequest.path
            return werkzeug.utils.redirect('/profile/add{0}'.format(redirect))
        elif not request.session.uid:
            return werkzeug.utils.redirect('/web/login', 303)
        else:
            return super(GreenwoodOrderController, self).checkout(post=post)

    @http.route()
    def payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.acquirer. State at this point :

         - a draft sale order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.acquirer website but closed the tab without
           paying / canceling
        """
        cr, uid, context = request.cr, request.uid, request.context
        payment_obj = request.registry.get('payment.acquirer')
        sale_order_obj = request.registry.get('sale.order')

        order = request.website.sale_get_order(context=context)

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        shipping_partner_id = False
        if order:
            if order.partner_shipping_id.id:
                shipping_partner_id = order.partner_shipping_id.id
            else:
                shipping_partner_id = order.partner_invoice_id.id

        values = {
            'order': request.registry['sale.order'].browse(cr, SUPERUSER_ID, order.id, context=context)
        }
        values['errors'] = sale_order_obj._get_errors(cr, uid, order, context=context)
        values.update(sale_order_obj._get_website_data(cr, uid, order, context))

        if not values['errors']:
            acquirer_ids = payment_obj.search(cr, SUPERUSER_ID, [('website_published', '=', True), ('company_id', '=', order.company_id.id)], context=context)
            values['acquirers'] = list(payment_obj.browse(cr, uid, acquirer_ids, context=context))
            render_ctx = dict(context, submit_class='btn btn-primary', submit_txt=_('Pay Now'))
            for acquirer in values['acquirers']:
                acquirer.button = payment_obj.render(
                    cr, SUPERUSER_ID, acquirer.id,
                    '/',
                    order.amount_total,
                    order.pricelist_id.currency_id.id,
                    partner_id=shipping_partner_id,
                    tx_values={
                        'return_url': '/shop/payment/validate',
                    },
                    context=render_ctx)
        values['cyear'] = cal.current_year()

        order_line = order.website_order_line
        product = order_line.product_id
        categ_name = product.categ_id.name
        _logger.info("categ name %s" % categ_name)
        if categ_name not in ['Monthly Payments', '6 Month Prepayment']:
            values['should_pay_now'] = True
        else:
            values['should_pay_now'] = False

        return request.website.render("website_sale.payment", values)

    @http.route()
    def payment_transaction(self, acquirer_id):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        cr, uid, context = request.cr, request.uid, request.context
        payment_obj = request.registry.get('payment.acquirer')
        transaction_obj = request.registry.get('payment.transaction')
        order = request.website.sale_get_order(context=context)

        if not order or not order.order_line or acquirer_id is None:
            return request.redirect("/shop/checkout")

        assert order.partner_id.id != request.website.partner_id.id

        # find an already existing transaction
        tx = request.website.sale_get_transaction()
        if tx:
            tx_id = tx.id
            if tx.sale_order_id.id != order.id or tx.state in ['error', 'cancel'] or tx.acquirer_id.id != acquirer_id:
                tx = False
                tx_id = False
            elif tx.state == 'draft':  # button cliked but no more info -> rewrite on tx or create a new one ?
                tx.write(dict(transaction_obj.on_change_partner_id(cr, SUPERUSER_ID, None, order.partner_id.id, context=context).get('values', {}), amount=order.amount_total))
        if not tx:
            tx_id = transaction_obj.create(cr, SUPERUSER_ID, {
                'acquirer_id': acquirer_id,
                'type': 'form',
                'amount': order.amount_total,
                'currency_id': order.pricelist_id.currency_id.id,
                'partner_id': order.partner_id.id,
                'partner_country_id': order.partner_id.country_id.id,
                'reference': request.env['payment.transaction'].get_next_reference(order.name),
                'sale_order_id': order.id,
            }, context=context)
            request.session['sale_transaction_id'] = tx_id
            tx = transaction_obj.browse(cr, SUPERUSER_ID, tx_id, context=context)

        # update quotation
        request.registry['sale.order'].write(
            cr, SUPERUSER_ID, [order.id], {
                'payment_acquirer_id': acquirer_id,
                'payment_tx_id': request.session['sale_transaction_id']
            }, context=context)

        return payment_obj.render(
            cr, SUPERUSER_ID, tx.acquirer_id.id,
            tx.reference,
            order.amount_total,
            order.pricelist_id.currency_id.id,
            tx_id=tx.id,
            partner_id=order.partner_shipping_id.id or order.partner_invoice_id.id,
            tx_values={
                'tx': tx,
                'tx_id': tx.id,
                'return_url': '/shop/payment/validate',
            },
            context=dict(context, submit_class='btn btn-primary', submit_txt=_('Pay Now')))

    @http.route()
    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :
        """
        cr, uid, context = request.cr, request.uid, request.context
        email_act = None
        sale_order_obj = request.registry['sale.order']

        # @TODO - Create contract for this sale order
        # Attach this sale order to the contract
        # Get this Sale order invoice and attach it to the contract
        gw_payment = request.registry['greenpay.payment']
        # save the user payment details in gw_account model
        _logger.info("payment post %r" % post)

        if transaction_id is None:
            tx = request.website.sale_get_transaction()
        else:
            tx = request.registry['payment.transaction'].browse(cr, uid, transaction_id, context=context)

        if sale_order_id is None:
            order = request.website.sale_get_order(context=context)
        else:
            order = request.registry['sale.order'].browse(cr, SUPERUSER_ID, sale_order_id, context=context)
            assert order.id == request.session.get('sale_last_order_id')

        if not order:
            return request.redirect('/shop')

        _logger.info("order object %r" % order)
        acquirer = request.registry['payment.acquirer'].browse(cr, SUPERUSER_ID, order.payment_acquirer_id, context=context)
        _logger.info("acquirer object %s, %r" % (acquirer.name, acquirer))

        vals = {
            'partner_id': order.partner_id.id,
            'card_number': post['card_number'],
            'expiry': int('%d%d' % (int(post['expiry_month']), int(post['expiry_year']))),
            'cvv': post['cvv'],
            'pin': post['pin'],
            'acquirer': 'interswitch',
        }
        gw_payment.create(cr, SUPERUSER_ID, vals, context=context)
        # if (not order.amount_total and not tx) or tx.state in ['pending', 'done']:
            # if (not order.amount_total and not tx):
                # Orders are confirmed by payment transactions, but there is none for free orders,
                # (e.g. free events), so confirm immediately
                # order.with_context(dict(context, send_email=True)).action_button_confirm()
        # elif tx and tx.state == 'cancel':
            # cancel the quotation
            # sale_order_obj.action_cancel(cr, SUPERUSER_ID, [order.id], context=request.context)

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset(context=context)
        # if tx and tx.state == 'draft':
        #    return request.redirect('/shop')

        return request.redirect('/shop/confirmation')


# class GreenwoodSession(Session):
#    @http.route('/web/session/logout', auth='none', type='http')
#    def logout(self, redirect='/web'):
#        ir_config_id = request.registry['ir.config_parameter'].search(request.cr, SUPERUSER_ID, [('key','=','web.base.url')])
#        base_url = request.registry['ir.config_parameter'].browse(request.cr, SUPERUSER_ID, ir_config_id[0], request.context).value
#        request.session.logout(keep_db=True)
#        return werkzeug.utils.redirect(base_url, 303)


class GreenwoodWebLogin(Website):

    @http.route()
    def index(self, **kw):
        cr, context, pool = request.cr, request.context, request.registry
        # promo/main/
        # promo/featured
        # promo/reco
        # promo/most-viewed
        product_template_obj = pool.get('product.template')
        product_ids = product_template_obj.search(cr, SUPERUSER_ID, [('promo_sale','=',True)])
        _logger.info(">>> Product ids %r" % product_ids)
        _logger.info(">>> App %r" % request.httprequest.app)
        main_section = []
        for id in product_ids:
            product = product_template_obj.browse(cr, SUPERUSER_ID, [id])
            _logger.info(">>> Products %r" % product)
            if product.block_type == 'main':
                main_section.append(('/object/bin/{0}/{1}'.format(product.promo_image, product.promo_image_scale), product.name))

        _logger.info("main_section images %r" % main_section)
        kw['main'] = main_section
        _logger.info(">>> params %r" % kw)
        r = super(GreenwoodWebLogin, self).index(**kw)
        return r


    @http.route()
    def web_login(self, redirect=None, *args, **kw):
        r = super(GreenwoodWebLogin, self).web_login(redirect=redirect, *args, **kw)
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        # Get website_greenwood oodel for this user
        users = request.registry.get('res.users')
        res_partner_obj = pool.get('res.partner')
        partner = users.browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        # set request.session.credit_status
        request.session.credit_status = partner.approval_status
        if not redirect and request.session.uid:
            _logger.info(">>> No redirect")
            if request.registry['res.users'].has_group(request.cr, request.session.uid, 'base.group_user'):
                redirect = '/web?' + request.httprequest.query_string
            else:
                _logger.info(">>> Redirecting to /")
                redirect = '/'
            return http.redirect_with_hash(redirect)
        _logger.info(">>> There's redirect %s" % redirect)
        if redirect and '/web' in redirect:
            if request.registry['res.users'].has_group(request.cr, request.session.uid, 'base.group_user'):
                redirect = redirect
            else:
                _logger.info("User credit status %s" % request.session.credit_status)
                redirect = '/'
            return http.redirect_with_hash(redirect)
        return r


class GreenwoodWebSignup(AuthSignupHome):

    @http.route()
    def web_auth_signup(self, redirect=None, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                self.do_signup(qcontext)
                return self.web_login(redirect=None, *args, **kw)
            except (SignupError, AssertionError), e:
                if request.env["res.users"].sudo().search([("login", "=", qcontext.get("login"))]):
                    qcontext["error"] = _("Another user is already registered using this email address.")
                else:
                    _logger.error(e.message)
                    qcontext['error'] = _("Could not create a new account.")

        return request.render('auth_signup.signup', qcontext)



class Service(http.Controller):
    @http.route("/file/upload/<string:field>/<string:cont>", auth="user")
    def uploadFileToTemp(self, field, cont, **post):
        """ Temp location is a temp container storage location on
        swift """
        print "\n>>Uploaded files", post
        ufile = post[field]
        filename = ufile.filename
        filedata = ufile.read()
        ufile.close()
        container, response, result = cont, dict(), {}
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

    @http.route("/object/bin/<string:filename>/<string:resize>")
    def getSwiftBinaryFile(self, filename, resize=None):
        headers = [('Content-Type', 'image/png')]
        try:
            image_base64 = _get_swift_file(filename)
            if resize:
                resize = kw.get('resize').split('x')
                if len(resize) == 2 and int(resize[0]) and int(resize[1]):
                    width = int(resize[0])
                    height = int(resize[1])
                    image_base64 = openerp.tools.image_resize_image(base64_source=image_base64, size=(width, height), encoding='base64', filetype='PNG')
            image_data = base64.b64decode(image_base64)
        except Exception:
            ncache = int(0)
            headers.append(('Cache-Control', 'no-cache' if ncache == 0 else 'max-age=%s' % (ncache)))
        headers.append(('Content-Length', len(image_data)))

        return request.make_response(image_data, headers)

    @http.route("/gw/product/update", type='json')
    def saveProductPromoImage(self, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        _logger.info(">>> Post %r" % post)
        template_obj = pool['product.template']
        values = {
            'promo_image': urllib2.quote(post['filename'])
        }
        updated = template_obj.write(cr, SUPERUSER_ID, [int(post['id'])], values, context=context)
        mime, result = 'application/json', { 'updated': updated }
        if updated:
            result['status'] = 200
        else:
            result['status'] = 417

        response = {
            "jsonrpc": "2.0"
        }
        response["result"] = result
        response["id"] = int(post['id'])
        _logger.info(">>> jsonrpc response %r" % response)

        return response


    # Incomplete
    @http.route("/file/binary/get/<string:filename>")
    def getBinaryFile(self, filename, section):
        # Based on section, get the resize value
        cr, uid, context = request.cr, request.uid, request.context
        headers = [('Content-Type', 'image/png')]
        try:
            res = Model.read(cr, uid, [id], [last_update, field], context)[0]
            retag = hashlib.md5(res.get(last_update)).hexdigest()
            image_base64 = res.get(field)
            image_base64 = openerp.tools.image_resize_image(base64_source=image_base64, size=(width, height), encoding='base64', filetype='PNG')
            image_data = base64.b64decode(image_base64)

        except Exception as e:
            headers.append(('Cache-Control', 'no-cache' if ncache == 0 else 'max-age=%s' % (ncache)))
        headers.append(('Content-Length', len(image_data)))
        return request.make_response(image_data, headers)

    @http.route('/creditassessment/import', auth="public", type='json')
    def import_credit_assessment(self, **post):
        """ Import credit assessment from CSV """
        return {
            "jsonrpc": "2.0",
            "id": null
        }

    @http.route('/affordability/compute', type='json')
    def compute_credit_affordability(self):
        """ Uses credit fields in res_partner (such as
        BVN, crc credit score, total income, monthly expenses, employer,
        affordability (salary must be able to pay at least 30%)) to check customer's credit eligibility

        Based on the score, the credit status is updated
        Response = {
        "score": "",
        "affordability": "N10,000 per month"
        }
        """

        pass

