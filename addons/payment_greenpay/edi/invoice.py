import urlparse
import logging

from openerp.osv import osv, fields
#from openerp import models, fields
from openerp.addons.edi import EDIMixin

from werkzeug import url_encode
_logger = logging.getLogger(__name__)

class account_invoice(osv.osv, EDIMixin):
    _inherit = 'account.invoice'

    def _edi_greenpay_url(self, cr, uid, ids, field, arg, context=None):
        _logger.info("Composing greenpay_url")
        res = dict.fromkeys(ids, False)
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        for inv in self.browse(cr, uid, ids, context=context):
            if inv.type == 'out_invoice':
                params = {
                    'ref': int(inv.id),
                    'number': inv.number,
                    "amount": inv.residual,
                    "currency": inv.currency_id.name,
                    'email': inv.partner_id.email,
                }
                #res[inv.id] = urlparse.urljoin(base_url, "/cgi-bin/pay?" + url_encode(params))
                res[inv.id] = "cgi-bin/pay?" + url_encode(params)
        return res

    _columns = {
        'greenpay_url': fields.function(_edi_greenpay_url, type='char', string='GreenPay Url')
    }

