import logging
import json
import base64

from openerp import models, fields, api
from openerp import SUPERUSER_ID
from openerp.http import request

from openerp.addons.website_greenwood.controllers.main import swift, _save_files_perm
from openerp.addons.website_greenwood.main import \
    SWIFT_GW_CONTAINER, SWIFT_GWTEMP_CONTAINER, SWIFT_WEB_CONTAINER, _datetime_from_string

_logger = logging.getLogger(__name__)


class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def profile_get(self, cr, uid, context=None):
        pool = self.pool
        users = pool['res.users']
        partner = users.browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        values = {
            'id': partner.id,
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
            'total_income': partner.total_income, # monthly income
            'annual_income': partner.annual_income,
            'credit_info': self.get_credit_score(cr, uid, context=context),
            'score_interpretation': partner.score_interpretation,
        }

        return values

    def profile_update(self, cr, partner_id, post, context=None):
        pool = self.pool
        partner_obj = pool['res.partner']

        post['debit_date'] = _datetime_from_string(post['debit_date'])
        _logger.info("post %r" % post)

        # @TODO Recompute credit affordability
        partner = partner_obj.browse(cr, SUPERUSER_ID, partner_id, context=context)
        partner_obj._compute_credit_score(cr, partner.user_id.id, context=context)

        #post['identity_id'] = _save_files_perm([post['identity_id']]).keys()[0] if post['identity_id'] else None
        return partner_obj.write(cr, SUPERUSER_ID, [partner_id], post, context=context)

    def postFile(self, cr, uid, filename, data):
        container, response, result = SWIFT_GWTEMP_CONTAINER, dict(), {}
        try:
            filecontent = base64.b64decode(data)
            swift().put_object(container=container, obj=filename, contents=filecontent, response_dict=response)
            mime = 'application/json'
            response_headers = response['headers']
            result['status'] = response['status']
            if response['status'] == 201:
                result['message'] = 'OK'
            else:
                result['message'] = response['reason']
            return result
        except Exception as e:
            print("Failed upload: %r" % e)
            result['status'] = 500
            result['message'] = e.message
            return result

    def get_credit_score(self, cr, uid, context=None):
        pool = self.pool
        orm_user = pool['res.users']
        partner_obj = pool['res.partner']
        computed = partner_obj._compute_credit_score(cr, uid, context=context)
        partner = orm_user.browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        return {
            'credit_score': partner.credit_score,
            'score_interpretation': partner.score_interpretation,
        }

    def logout(self, cr, uid, context=None):
        _logger.info("request type %r" % request)
        request.session.logout(keep_db=True)
