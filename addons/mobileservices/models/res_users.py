import logging
import json
import time
import random
import base64

import openerp
from openerp import models, fields, api
from openerp.addons.auth_signup.res_users import SignupError
from openerp import SUPERUSER_ID
from openerp.http import request
from openerp.addons.mobileservices.queue import produce

from hashids import Hashids

_logger = logging.getLogger(__name__)


class res_users(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    userhash = fields.Char(help="A unique hash per user")
    gcm_token = fields.Char(string="Android device token")
    apn_token = fields.Char(string="iOS device token")
    session_token = fields.Char(help="Can be used as jsessionid or session_id")

    def mobile_login(self, cr, uid, post, context=None):
        db, login, password = post.get('db'), post.get('login'), post.get('password')
        user_id = self._login(db, login, password)
        if user_id:
            # Get mobile token
            u = self.browse(cr, uid, [user_id])
            payload = ":".join([login, str(time.time()), str(user_id)])
            session_token = base64.b64encode(payload)
            vals = {'session_token': session_token}
            if not u.userhash:
                vals['userhash'] = self._generate_userhash()
            self.pool['res.users'].write(cr, uid, [user_id], vals, context=context)
            message = {'session_token': session_token, 'email': login, 'uid': user_id}
            params = {
                'exchange': 'users',
                'routing_key': 'socket',
                'type': 'direct',
            }
            produce(message, **params)
            values = {
                'uid': user_id,
                'gcm_token': u.gcm_token,
                'apn_token': u.apn_token,
                'session_token': session_token
            }
            return values
        return user_id

    def user_update(self):
        pass

    def mobile_signup(self, cr, uid, post, context=None):
        pool = self.pool
        icp = pool['ir.config_parameter']
        config = {
            'signup_enabled': icp.get_param(cr, SUPERUSER_ID, 'auth_signup.allow_uninvited') == 'True',
            'reset_password_enabled': icp.get_param(cr, SUPERUSER_ID, 'auth_signup.reset_password') == 'True',
        }
        username = post.get('username')
        company_name = post.get('company_name') or 'Greenwood'
        if company_name:
            company_ids = pool['res.company'].search(cr, SUPERUSER_ID, [('name', '=', company_name)], context=context)
            company_id = company_ids[0]

        values = {
            'login': post.get('email'),
            'name': post.get('name'),
            'password': post.get('password'),
            'confirm_password': post.get('confirmpass'),
            'token': None,
            'company_id': company_id,
            'userhash': username
        }
        values.update(config)
        db, login, password = pool['res.users'].signup(cr, SUPERUSER_ID, values, None)
        user_id = self.search(cr, SUPERUSER_ID, [('login', '=', values['login'])], context=context)
        if user_id and not username:
            userhash = self._generate_userhash()
            pool['res.users'].write(cr, SUPERUSER_ID, user_id, {'userhash': userhash}, context=context)
        cr.commit()
        return [db, login, password] if all([k for k in [db, login, password]]) else None

    def _generate_userhash(self):
        salt = fields.Datetime.now()
        hashids = Hashids(min_length=6, salt=salt)
        #return hashids.encode(int(time.time()), int('%.0f' % random.random()))
        return hashids.encode(int(time.time()), random.randint(1, int(time.time())))

    def create_userhash(self, cr, uid, user_id, context=None):
        """ Create userhash if user has none """
        userhash = self._generate_userhash()
        values = {
            'userhash': userhash,
        }
        return self.pool['res.users'].write(cr, SUPERUSER_ID, [user_id], values, context=context)

    def change_username(self, cr, uid, user_id, username, context=None):
        try:
            self._validate_userhash(cr, uid, username, context=context)
            # write since it doesn't exist
            self.write(cr, uid, [user_id], {'userhash': username}, context=context)
            validated = {'result': True, 'message': 'OK'}
        except AssertionError as e:
            validated = {'result': False, 'message': e.message}
        return validated

    def _validate_userhash(self, cr, uid, value, context=None):
        userid = self.search(cr, uid, [('userhash', '=', value)], context=context)
        assert len(userid) < 1, 'Username already exists'

    def mobile_reset_password(self, uid):
        # Should we just use the web reset_password?
        pass

    def facebook_login(self, cr, uid, profile, context=None):
        _logger.info("Facebook login profile %r" % profile)
        provider = profile['p']
        context = profile['c']
        return self.mobile_auth_oauth(cr, uid, provider, profile, context=context)

    def mobile_auth_oauth(self, cr, uid, provider, params, context=None):
        access_token = params.get('access_token')
        #validation = self._mobile_auth_oauth_validation(cr, uid, provider, access_token, context=context)
        validation = {
            'name': params.get('name'),
            'email': params.get('email'),
            'user_id': params.get('id')
        }
        # required check
        if not validation.get('user_id'):
            # Workaround
            if validation.get('id'):
                validation['user_id'] = validation['id']
            else:
                raise openerp.exceptions.AccessDenied()
        # retrieve and sign in user
        login = self._mobile_auth_oauth_signin(cr, uid, provider, validation, params, context=context)
        if not login:
            raise openerp.exceptions.AccessDenied()

        user_ids = self.search(cr, uid, [("login", "=", login)])
        user = self.browse(cr, uid, user_ids[0], context=context)
        # return user credentials
        return (user.id, login, access_token)

    def _mobile_auth_oauth_validation(self, cr, uid, provider, access_token, context=None):
        """ return the validation data corresponding to the access token """
        p = self.pool.get('auth.oauth.provider').browse(cr, uid, provider, context=context)
        validation = self._auth_oauth_rpc(cr, uid, p.validation_endpoint, access_token, context=context)
        if validation.get("error"):
            raise Exception(validation['error'])
        if p.data_endpoint:
            data = self._auth_oauth_rpc(cr, uid, p.data_endpoint, access_token, context=context)
            validation.update(data)
        return validation

    def _mobile_auth_oauth_signin(self, cr, uid, provider, validation, params, context=None):
        """ retrieve and sign in the user corresponding to provider and validated access token
            :param provider: oauth provider id (int)
            :param validation: result of validation of access token (dict)
            :param params: oauth parameters (dict)
            :return: user login (str)
            :raise: openerp.exceptions.AccessDenied if signin failed

            This method can be overridden to add alternative signin methods.
        """
        try:
            oauth_uid = validation['user_id']
            user_ids = self.search(cr, uid, [("oauth_uid", "=", oauth_uid), ('oauth_provider_id', '=', provider)])
            if not user_ids:
                raise openerp.exceptions.AccessDenied()
            assert len(user_ids) == 1
            user = self.browse(cr, uid, user_ids[0], context=context)
            user.write({'oauth_access_token': params['access_token']})
            return user.login
        except openerp.exceptions.AccessDenied, access_denied_exception:
            if context and context.get('no_user_creation'):
                return None
            token = None
            values = self._generate_signup_values(cr, uid, provider, validation, params, context=context)
            try:
                _, login, _ = self.signup(cr, uid, values, token, context=context)
                return login
            except SignupError:
                raise access_denied_exception

    def forgot_password(self, cr, uid, login, context=None):
        try:
            assert login, "No login provided"
            self.reset_password(cr, uid, login, context=context)
            msg = "An email has been sent with credentials to reset your password"
        except Exception, e:
            msg = e.message
            _logger.exception('error when resetting password')
        return msg

