import logging

from openerp import models, fields, api

from openerp.osv import osv
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _

from openerp.addons.website_greenwood.main import Config
config = Config()

PPG = 20 # Products Per Page
PPR = 4  # Products Per Row

_logger = logging.getLogger(__name__)

class res_product(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    bid_total = fields.Float(string="Bid total", required=True, default=float(0.0), help="Total bids on a Cheape product")
    max_bid_total = fields.Float(string="Max bid total", required=True, default=float(0.0), help="The maximum bid total allowed for this product")

    def cheape_products(self, cr, uid, page=0, search='', category=None, kw=None, context=None):
        pool = self.pool
        post = dict()
        domain = self._get_search_domain(search, category, None) # attrib_values not supported yet
        # We want only Greenwood products
        company_ids = pool['res.company'].search(cr, uid, [('name', '=', 'Cheape')], context=context)
        company_id = company_ids[0]
        domain += [('company_id', '=', company_id)]

        pricelist = self.get_pricelist(cr, uid)
        product_obj = pool.get('product.template')

        url = '/shop'
        product_count = product_obj.search_count(cr, uid, domain, context=context)
        if search:
            post["search"] = search
        if category:
            category = pool['product.public.category'].browse(cr, uid, int(category), context=context)
            url = "/shop/category/%s" % slug(category)

        website = pool['website'].browse(cr, uid, 1, context=context)
        pager = website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)
        product_ids = product_obj.search(cr, uid, domain, limit=PPG, offset=pager['offset'], order=self._get_search_order(post), context=context)
        # Return only products
        _logger.info("islive %s" % kw.get('islive'))
        cr.execute("SELECT id FROM cheape_livebid WHERE power_switch = %s", (kw.get('islive'),))
        livebid_ids = [d[0] for d in cr.fetchall()]
        livebids = pool['cheape.livebid'].browse(cr, uid, livebid_ids, context=context)
        _logger.info("livebids %r" % livebids)
        livebid_product_ids = [livebid.product_id.id for livebid in livebids]
        _logger.info("livebid_product_ids %r" % livebid_product_ids)
        #ids = set(livebid_product_ids + product_ids)
        ids = livebid_product_ids
        products = product_obj.browse(cr, uid, ids, context=context)

        category_obj = pool['product.public.category']
        category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        categs = category_obj.browse(cr, uid, category_ids, context=context)

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        _logger.info("products %r" % products.__dict__)

        # Iterate through the product template, retrieving the products
        product_list = []
        partner_ids = pool['res.partner'].browse(cr, SUPERUSER_ID, [], context=context).commercial_partner_id.id
        if products:
            for product in products:
                sellers = product.seller_ids.name.display_name
                lb_product_id = self.pool['cheape.livebid'].search(cr, SUPERUSER_ID, [('product_id', '=', product.id)])
                livebid_product = self.pool['cheape.livebid'].browse(cr, SUPERUSER_ID, lb_product_id)
                product_list.append({'id': product.id,
                                     'name': product.name,
                                     'price': product.list_price,
                                     'product_imageurl': '{0}/web/binary/image?model=product.template&field=image_medium&id={1}'.format(config.settings()['mobile_virtual_host'], product.id),
                                     'product_imageurl_big': '{0}/web/binary/image?model=product.template&field=image&id={1}'.format(config.settings()['mobile_virtual_host'], product.id),
                                     'sellers': sellers,
                                     'fin_structure_desc': product.fin_structure_desc,
                                     'fin_structure': product.fin_structure,
                                     'contract_term': product.contract_term,
                                     'livebid_id': livebids.filtered(lambda l: l.product_id.id == product.id).product_id.id,
                                     'bid_total': product.bid_total,
                                     'max_bid_price': product.max_bid_total
                                     }
                                    )

        # @todo For logged in user, flag items that user has in cart

        values = {
            'products': product_list,
        }

        return values

