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

    def cheape_signup(self, cr, uid, login, name, password, passconfirm, context=None):
        pool = self.pool
        icp = pool['ir.config_parameter']
        # @todo set company_id to Cheape
        company_ids = pool['res.company'].search(cr, uid, [('name', '=', 'Cheape')], context=context)
        company_id = company_ids[0]

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
            'company_id': company_id,
        }
        values.update(config)
        db, login, password = pool['res.users'].signup(cr, SUPERUSER_ID, values, None)
        user_id = self.search(cr, uid, [('login', '=', login)], context=context)
        if user_id:
            userhash = self._generate_userhash()
            pool['res.users'].write(cr, SUPERUSER_ID, user_id, {'userhash': userhash}, context=context)
        cr.commit()

        # If we get here, award free bidpacks
        if all([k for k in [db, login, password]]):
            params = {
                'action': 'signup',
                'login': login
            }
            pool['cheape.reward'].unlock_reward(cr, SUPERUSER_ID, params, context=context)
        return [db, login, password] if all([k for k in [db, login, password]]) else None
