import logging
import json
import ast

from openerp import models, fields, api
from openerp import SUPERUSER_ID

from openerp.addons.website_sale.models.sale_order import website
from openerp.addons.web.http import request

PPG = 20 # Products Per Page
PPR = 4  # Products Per Row

_logger = logging.getLogger(__name__)


class product_template(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    def _get_search_domain(self, search, category, attrib_values):
        # domain = website.sale_product_domain()
        # domain = request.website.sale_product_domain()
        # domain = self.pool.get('website').sale_product_domain()
        domain = [("sale_ok", "=", True)]

        if search:
            for srch in search.split(" "):
                domain += [
                    '|', '|', '|', ('name', 'ilike', srch), ('description', 'ilike', srch),
                    ('description_sale', 'ilike', srch), ('product_variant_ids.default_code', 'ilike', srch)]

        if category:
            domain += [('public_categ_ids', 'child_of', int(category))]

        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domain += [('attribute_line_ids.value_ids', 'in', ids)]
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domain += [('attribute_line_ids.value_ids', 'in', ids)]

        return domain

    def get_pricelist(self, cr, uid, context=None):
        pool = self.pool
        partner = pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        pricelist = partner.property_product_pricelist
        if not pricelist:
            _logger.error('Fail to find pricelist for partner "%s" (id %s)', partner.name, partner.id)
        return pricelist

    def _get_search_order(self, post):
        # OrderBy will be parsed in orm and so no direct sql injection
        return 'website_published desc,%s' % post.get('order', 'website_sequence desc')

    def products_list(self, cr, uid, page=0, search='', category=None, context=None):
        pool = self.pool
        post = dict()
        _logger.info("cr in products_list %r" % cr)
        _logger.info("request in products_list %r" % request)
        domain = self._get_search_domain(search, category, None) # attrib_values not supported yet

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
        products = product_obj.browse(cr, uid, product_ids, context=context)

        category_obj = pool['product.public.category']
        category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        categs = category_obj.browse(cr, uid, category_ids, context=context)

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        _logger.info("products %r" % products.__dict__)

        # Iterate through the product template, retrieving the products
        product_list = []
        if products:
            for product in products:
                _logger.info("product %r" % [product.id, product.name, product.list_price])
                product_list.append({'id': product.id,
                                     'name': product.name,
                                     'price': product.list_price}
                                    )

        values = {
            # 'products': ast.literal_eval(json.dumps(products.__dict__)),
            # 'products': json.dumps(products.__dict__),
            'products': product_list,
        }

        return values

    def cart_items(self, cr, uid, context=None):
        pool = self.pool
        website = pool['website'].browse(cr, uid, 1, context=context)
        order = website.sale_get_order()
        if order:
            from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
            to_currency = order.pricelist_id.currency_id
            compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)
        else:
            compute_currency = None

        values = {
            'order': order,
            'compute_currency': compute_currency,
            'suggested_products': [],
        }

        _logger.info("compute_currency value %r" % compute_currency)
        _logger.info("order value %r" % order)
        if order:
            _order = order
            if not context.get('pricelist'):
                _order = order.with_context(pricelist=order.pricelist_id.id)
            values['suggested_products'] = _order._cart_accessories()

        return values

    def add_to_cart(self, cr, uid, product_id, line_id, add_qty=None):
        pass

    def suggested_products(self, cr, uid, context=None):
        pass
