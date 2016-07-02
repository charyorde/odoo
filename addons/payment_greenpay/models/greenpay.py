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
    }

    _defaults = {
        'acquirer': 'interswitch',
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
