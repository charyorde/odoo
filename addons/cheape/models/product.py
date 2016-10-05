import logging

from openerp import models, fields, api

from openerp.osv import osv
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _

#config = Config()

PPG = 20 # Products Per Page
PPR = 4  # Products Per Row

_logger = logging.getLogger(__name__)

class res_product(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    bid_total = fields.Float(string="Bid total", required=True, default=float(0.0), help="Total bids on a Cheape product")
    max_bid_total = fields.Float(string="Max bid total", required=True, default=float(0.0), help="The maximum bid total allowed for this product")

    def cheape_products(self, cr, uid):
        pass

