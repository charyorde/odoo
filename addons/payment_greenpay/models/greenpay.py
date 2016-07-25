from openerp.osv import osv, fields
from openerp import api

class greenpay_payment(osv.Model):
    _name = 'greenpay.payment'

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Customer', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, required=True, change_default=True, select=True, track_visibility='always'),
        'card_number': fields.char(required=True),
        'expiry': fields.char(required=True),
        'cvv':fields.integer(required=True),
        'pin': fields.integer(),
        'acquirer': fields.char(),
        'token': fields.char(),
        'bank_name': fields.selection(
            [('FCMB', 'FCMB'),
             ('Union Bank', 'Union Bank'),
             ('Stanbic IBTC', 'Stanbic IBTC'),
             ('Sterling Bank', 'Sterling Bank'),
             ('Skye Bank', 'Skye Bank'),
             ('Zenith Bank', 'Zenith Bank')], 'Bank Name', required=True),
        'bank_account_number': fields.integer('Bank Account Number', required=True),
    }

    _defaults = {
        'acquirer': 'interswitch',
        'card_number': 'None',
        'expiry': 'None',
        'cvv': 0,
        'bank_name': '',
        'bank_account_number': 0,
    }

    def create(self, cr, uid, vals, context=None):
        return super(greenpay_payment, self).create(cr, uid, vals, context=context)

    @api.multi
    def write(self, vals):
        updated = super(greenpay_payment, self).write(vals)
        if updated:
            return updated
        return False

    def encrypt(self, params):
        """ Encrypt customer card details """
        pass
