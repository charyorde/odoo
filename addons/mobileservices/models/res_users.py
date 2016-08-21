import logging
import json

from openerp import models, fields, api
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
