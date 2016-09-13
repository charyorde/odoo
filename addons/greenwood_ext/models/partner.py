import math
import logging
import exceptions

from openerp import models, fields, api
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)

BVNSCORE = 30
TENANCYSCORE = 10
EMPSCORE = 10
CREDITRECORD = 20
INCOMESCORE = 15
MEXPENSES = 15


class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    annual_income = fields.Float(string='Annual income', required=True, default=float(0.0))
    credit_score = fields.Float(string='Credit score', default=float(0.0), required=True)
    score_interpretation = fields.Char(string="Score Interpretation")

    def _validate_bvn(self, cr, uid, context=None):
        """ Does user have BVN number?

        Is BVN linked with Greenwood supported banks """
        users = self.pool['res.users']
        partner = users.browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        bvn = partner.bvn
        return BVNSCORE if bvn != 0 else 0

    def _validate_employer(self, cr, uid, context=None):
        """ Is the employer in the list of approved companies """

        users = self.pool['res.users']
        company = self.pool['res.company']
        partner = users.browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        empname = partner.empname
        companies = company.name_search(cr, SUPERUSER_ID, name=empname, operator='=')
        return [EMPSCORE for c in companies if empname in c]

    def _validate_mexpenses(self, cr, uid, context=None):
        """ Is it less than monthly income? """
        users = self.pool['res.users']
        partner = users.browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        mexpenses = partner.mexpenses
        monthlyincome = partner.total_income
        return MEXPENSES if mexpenses < monthlyincome else 0

    def _validate_total_income(self, cr, uid, purchase_price, context=None):
        """ Is monthly able to pay 50% of the pruchase of the goods after
        monthly expenses is deducted?

        Is total annual income able to pay 70% of the purchase price of the good """
        users = self.pool['res.users']
        partner = users.browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        mexpenses = partner.mexpenses
        income_monthly = partner.total_income
        annual_income = partner.annual_income
        return int(0)

    def _validate_creditrecord(self, cr, uid, context=None):
        """ Based on credit score received from credit registry """
        return int(0)

    def _validate_tenancy(self, cr, uid, context=None):
        """ Does user have a valid tenancy agreement? """
        users = self.pool['res.users']
        partner = users.browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        tenancy = partner.tenancy
        return TENANCYSCORE if tenancy != 'None' else 0

    def _compute_credit_score(self, cr, uid, context=None):
        users = self.pool['res.users']
        partner = users.browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        prefix = '_validate'
        bvn_score = getattr(self, prefix + '_bvn')(cr, uid, context=context)
        emp_score = getattr(self, prefix + '_employer')(cr, uid, context=context)
        tenancy_score = getattr(self, prefix + '_tenancy')(cr, uid, context=context)
        cr_score = getattr(self, prefix + '_creditrecord')(cr, uid, context=context)
        total_income_score = getattr(self, prefix + '_total_income')(cr, uid, float(0.0), context=context)
        mexpenses_score = getattr(self, prefix + '_mexpenses')(cr, uid, context=context)

        emp_score_value = emp_score[0] if emp_score else 0

        params = [bvn_score, emp_score_value, tenancy_score,
                  cr_score, total_income_score,
                  mexpenses_score]

        _logger.info("score params %r" % params)

        try:
            score = math.fsum(params) / 100
        except exceptions.ArithmeticError as e:
            raise e

        values = {
            #'id': partner.id,
            'credit_score': score,
        }

        _logger.info("values %r" % values)

        return self.pool['res.partner'].write(cr, SUPERUSER_ID, [partner.id], values, context=context)
