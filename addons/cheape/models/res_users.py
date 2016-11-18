import logging
import json
import time
import base64

import openerp
from openerp import models, fields, api
from openerp.addons.auth_signup.res_users import SignupError
from openerp import SUPERUSER_ID
from openerp.http import request

#import jwt
from openerp.addons.mobileservices.queue import produce

_logger = logging.getLogger(__name__)


class res_users(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    def cheape_signup(self, cr, uid, post, context=None):
        pool = self.pool
        icp = pool['ir.config_parameter']
        # @todo set company_id to Cheape
        company_ids = pool['res.company'].search(cr, uid, [('name', '=', 'Cheape')], context=context)
        company_id = company_ids[0]

        config = {
            'signup_enabled': icp.get_param(cr, SUPERUSER_ID, 'auth_signup.allow_uninvited') == 'True',
            'reset_password_enabled': icp.get_param(cr, SUPERUSER_ID, 'auth_signup.reset_password') == 'True',
        }
        username, login = post.get('username'), post.get('login')
        values = {
            'login': login,
            'name': post.get('name'),
            'password': post.get('password'),
            'confirm_password': post.get('confirmpass'),
            'token': None,
            'company_id': company_id,
            'userhash': username
        }
        values.update(config)
        db, login, password = pool['res.users'].signup(cr, SUPERUSER_ID, values, None)
        user_id = self.search(cr, uid, [('login', '=', login)], context=context)
        #if user_id:
            #payload = ":".join([login, str(time.time()), str(user_id)])
            #auth_token = jwt.encode(payload, login, algorithm='HS256')
            #session_token = base64.b64encode(payload)
            #params = {
                #'exchange': 'users',
                #'routing_key': 'socket',
                #'type': 'direct',
            #}
            #message = {'session_token': session_token, 'email': login, 'uid': user_id}
            #pool['res.users'].write(cr, SUPERUSER_ID, user_id, {'session_token': session_token}, context=context)
            #produce(message, params)
        if user_id and not username:
            userhash = self._generate_userhash()
            pool['res.users'].write(cr, SUPERUSER_ID, user_id, {'userhash': userhash}, context=context)
        cr.commit()

        # If we get here, award free bidpacks
        if all([k for k in [db, login, password]]):
            reward = pool['cheape.rewards']._get_reward(cr, SUPERUSER_ID, 'signup', context=context)
            params = {
                'action': 'signup',
                'login': login,
                'name': reward.name
            }
            pool['cheape.reward'].create(cr, SUPERUSER_ID, params, context=context)
            params['qty'] = int(reward.label)
            pool['res.partner'].topup_bidpacks(cr, SUPERUSER_ID, params, context=context)
        return [db, login, password, auth_token] if all([k for k in [db, login, password]]) else None

    def account_update(self, cr, uid, user_id, post, context=None):
        ret = None
        username = post.get('username')
        if username:
            validated = self.change_username(cr, uid, user_id, username, context=context)
            _logger.info("change_username: %r" % validated)
            ret = validated
        return ret

