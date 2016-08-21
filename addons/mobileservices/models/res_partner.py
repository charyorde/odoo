import logging
import json

from openerp import models, fields, api
from openerp import SUPERUSER_ID
from openerp.http import request

_logger = logging.getLogger(__name__)


class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def profile_get(self, cr, uid, context=None):
        pool = self.pool
        users = pool['res.users']
        partner = users.browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        values = {
            'name': partner.name,
            'company_id': partner.company_id.id,
            'create_date': partner.create_date,
            'street': partner.street,
            'street2': partner.street2,
            'city': partner.city,
            'display_name': partner.display_name,
            'zip': partner.zip,
            'title': partner.title.id,
            'function': partner.function,
            'country_id': partner.country_id.id,
            'state_id': partner.state_id.id,
            'email': partner.email,
            'is_company': partner.is_company,
            'credit_limit': partner.credit_limit,
            'debit_limit': partner.debit_limit,
            'active': partner.active,
            'lang': partner.lang,
            'phone': partner.phone,
            'mobile': partner.mobile,
            'uid': partner.user_id.id,
            'birthdate': partner.birthdate,
            'notify_email': partner.notify_email,
            'opt_out': partner.opt_out,
            'bvn': partner.bvn,
            'bvn_linked_bank': partner.bvn_linked_bank,
            'empname': partner.empname,
            'tenancy': partner.tenancy,
            'approval_status': partner.approval_status,
            'companyname': partner.companyname,
            'identity_id': partner.identity_id,
            'mexpenses': partner.mexpenses,
            'company_type': partner.company_type,
            'payslips': partner.payslips,
            'debit_date': partner.debit_date,
            'company_reg_id': partner.company_reg_id,
            'bank_account_number': partner.bank_account_number,
            'bank_name': partner.bank_name,
            'cr_credit_score': partner.cr_credit_score,
            'total_income': partner.total_income,
        }

        return values

    def profile_update(self, cr, uid, **kw):
        pass

    def logout(self, cr, uid, context=None):
        _logger.info("request type %r" % request)
        request.session.logout(keep_db=True)
