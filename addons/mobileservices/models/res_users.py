import logging
import json

import openerp
from openerp import models, fields, api
from openerp.addons.auth_signup.res_users import SignupError
from openerp import SUPERUSER_ID
from openerp.http import request

_logger = logging.getLogger(__name__)


class res_users(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    def mobile_signup(self, cr, uid, login, name, password, passconfirm, context=None):
        pool = self.pool
        icp = pool['ir.config_parameter']
        config = {
            'signup_enabled': icp.get_param(cr, SUPERUSER_ID, 'auth_signup.allow_uninvited') == 'True',
            'reset_password_enabled': icp.get_param(cr, SUPERUSER_ID, 'auth_signup.reset_password') == 'True',
        }
        values = {
            'login': login,
            'name': name,
            'password': password,
            'confirm_password': passconfirm,
            'token': None,
        }
        values.update(config)
        db, login, password = pool['res.users'].signup(cr, SUPERUSER_ID, values, None)
        cr.commit()
        return [db, login, password] if all([k for k in [db, login, password]]) else None

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
