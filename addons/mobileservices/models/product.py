import logging
import json
import ast
import random

from openerp import models, fields, api
from openerp.osv import osv
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _

from werkzeug.wrappers import Response

from openerp.addons.website_greenwood.main import Config
from openerp.addons.website_greenwood.controllers.main import _get_swift_file
# from openerp.addons.website_sale.models.sale_order import website
from openerp.addons.web.http import request

config = Config()

PPG = 20 # Products Per Page
PPR = 4  # Products Per Row

_logger = logging.getLogger(__name__)

_logger.info("settings %r" % config.settings())

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
        domain = self._get_search_domain(search, category, None) # attrib_values not supported yet
        # We want only Greenwood products
        domain += [('company_id', '=', 1)]

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

        _logger.info("Companies %r" % pool['res.company'].name_search(cr, SUPERUSER_ID, name='Greenwood', operator='='))
        # Iterate through the product template, retrieving the products
        product_list = []
        partner_ids = pool['res.partner'].browse(cr, SUPERUSER_ID, [], context=context).commercial_partner_id.id
        if products:
            for product in products:
                # seller_ids in partner_ids
                #sellers = filter(lambda x: x.name.id in partner_ids, product.seller_ids)
                #sellers = filter(lambda x: x.name.display_name, product.seller_ids)
                sellers = product.seller_ids.name.display_name
                _logger.info("product %r" % [product.id, product.name, product.list_price])
                product_list.append({'id': product.id,
                                     'name': product.name,
                                     'price': product.list_price,
                                     'product_imageurl': '{0}/web/binary/image?model=product.template&field=image_medium&id={1}'.format(config.settings()['mobile_virtual_host'], product.id),
                                     'product_imageurl_big': '{0}/web/binary/image?model=product.template&field=image&id={1}'.format(config.settings()['mobile_virtual_host'], product.id),
                                     'sellers': sellers,
                                     'fin_structure_desc': product.fin_structure_desc,
                                     'fin_structure': product.fin_structure,
                                     'contract_term': product.contract_term,
                                     }
                                    )

        # @todo For logged in user, flag items that user has in cart

        values = {
            'products': product_list,
        }

        return values

    def cart_items(self, cr, uid, context=None):
        pool = self.pool
        orm_user = pool['res.users']
        website = pool['website'].browse(cr, SUPERUSER_ID, 1, context=context)
        partner = orm_user.browse(cr, SUPERUSER_ID, uid, context).partner_id

        #order = request.website.sale_get_order()
        order = self.sale_order_latest(cr, SUPERUSER_ID, partner.id, context=context)

        if order:
            from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
            to_currency = order.pricelist_id.currency_id
            compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)
        else:
            compute_currency = None

        values = {}
        p = []

        if order:
            for line in order.website_order_line:
                p.append({
                    'id': line.product_id.id,
                    'price': line.product_id.lst_price,
                    'name': line.product_id.name,
                    'contract_term': line.product_id.contract_term,
                    'product_imageurl': '{0}/web/binary/image?model=product.template&field=image_medium&id={1}'.format(config.settings()['mobile_virtual_host'], line.product_id.id),
                })

            values.update({
                'lines': p,
                'order': {
                    'id': order.id,
                    'name': order.name,
                    'date_order': order.date_order,
                    'partner_id': order.partner_id.id,
                    'amount_tax': order.amount_tax,
                    'fiscal_position': order.fiscal_position.id,
                    'amount_untaxed': order.amount_untaxed,
                    'state': order.state,
                    'pricelist_id': order.pricelist_id.id,
                    # 'section_id': order.section_id.id,
                    'partner_invoice_id': order.partner_invoice_id.id,
                    'user_id': order.user_id.id,
                    # 'date_confirm': order.date_confirm,
                    'amount_total': order.amount_total,
                    'partner_shipping_id': order.partner_shipping_id.id,
                    'order_policy': order.order_policy,
                    'payment_tx_id': order.payment_tx_id.id,
                    'payment_acquirer_id': order.payment_acquirer_id.id,
                    'picking_policy': order.picking_policy,
                    'shipped': order.shipped,
                    #'campaign_id': order.campaign_id.id,
                }
            })

        values.update({
            #'compute_currency': compute_currency,
            'suggested_products': [],
        })

        if order:
            # _order = order
            # We change context because we don't have one
            _order = order.with_context(pricelist=order.pricelist_id.id)
            # values['suggested_products'] = _order._cart_accessories()

        # @todo serialize products in values['suggested_products']
        return {'sale_order': values }

    def sale_order_latest(self, cr, uid, partner_id, sale_order_id=None, update_pricelist=None, context=None):
        """ Get a user latest sale order.
        Odoo retrieves latest sale_order via session. Since
        we don't have access to session on mobile, we query
        it raw """
        pool = self.pool
        sale_order_obj = pool['sale.order']
        sale_order = None

        if not partner_id and sale_order_id:
            sale_order = sale_order_obj.browse(cr, SUPERUSER_ID, [sale_order_id], context=context)
        else:
            partner_obj = pool['res.partner']
            partner = partner_obj.browse(cr, SUPERUSER_ID, partner_id, context=context)
            sale_order_ids = sale_order_obj.search(cr, uid, [("partner_id", "=", partner_id), ("state", "=", "draft")], context=context)
            if sale_order_ids:
                sale_order = sale_order_obj.browse(cr, SUPERUSER_ID, sale_order_ids[0], context=context)

        pricelist_id = partner.property_product_pricelist.id

        # update the pricelist
        if sale_order and update_pricelist:
            values = {'pricelist_id': pricelist_id}
            values.update(sale_order.onchange_pricelist_id(pricelist_id, None)['value'])
            sale_order.write(values)
            for line in sale_order.order_line:
                if line.exists():
                    sale_order._cart_update(product_id=line.product_id.id, line_id=line.id, add_qty=0)

        return sale_order

    def sale_order_by_partner_id(self, cr, uid, partner_id, context=None):
        """ find draft orders by partner_id or None """
        pool = self.pool
        sale_order_obj = pool['sale.order']
        sale_order = sale_order_obj.browse(cr, uid, [partner_id], context=context)

        # For each of sale_order as order, return orders with state = 'draft'
        # Update them with their lates prices
        orders = []
        for order in sale_order:
            if order.state == 'draft':
                _logger.info("Draft orders %r" % order)
                orders.append({'id': order.id,
                               'name': order.name,
                               'date_order': order.date_order,
                               'partner_id': order.partner_id.id,
                               'amount_tax': order.amount_tax,
                               'fiscal_position': order.fiscal_position,
                               }
                        )

        # orders = order [if order.state == 'draft' for order in sale_order]
        return sale_order or None

    def checkout_form_validate(self, data):
        pool = self.pool

        error = dict()
        for field_name in self._get_mandatory_billing_fields():
            if not data.get(field_name):
                error[field_name] = 'missing'

        # email validation
        if data.get('email') and not tools.single_email_re.match(data.get('email')):
            error["email"] = 'error'

        return error

    def confirm_order(self, cr, uid, data, context=None):
        pool = self.pool
        orm_user = pool['res.users']
        partner = orm_user.browse(cr, SUPERUSER_ID, uid, context).partner_id

        #order = request.website.sale_get_order(context=context)
        order = self.sale_order_latest(cr, SUPERUSER_ID, partner.id, context=context)

        _logger.info("Post data %r" % data)
        values = self.checkout_values(cr, uid, data)
        values["error"] = self.checkout_form_validate(values["checkout"])
        if values["error"]:
            return values

        order_id = self.checkout_form_save(cr, uid, values["checkout"], context=context)

        self.sale_order_latest(cr, SUPERUSER_ID, partner.id, update_pricelist=True, context=None)

        # If order.id exists, create a transaction using cmms payment acquirer
        ret = {}
        tx_id = self.create_tx(cr, uid, 22, order_id, context=context)
        if tx_id:
            ret['order_id'] = order_id
            ret['tx_id'] = tx_id

        return ret

    def checkout_form_save(self, cr, uid, checkout, context=None):
        """ Called within confirm_order. Saves the order """
        pool = self.pool
        website = pool['website'].browse(cr, uid, 1, context=context)
        orm_partner = pool['res.partner']
        orm_user = pool['res.users']
        order_obj = pool['sale.order']

        order = website.sale_get_order(force_create=1, context=context)

        _logger.info("checkout order %r" % order)

        billing_info = {'customer': True}
        billing_info.update(self.checkout_parse('billing', checkout, True))

        # set partner_id
        partner_id = None
        if request.uid != website.user_id.id:
            partner_id = orm_user.browse(cr, SUPERUSER_ID, uid, context=context).partner_id.id

        # save partner informations
        if partner_id and website.partner_id.id != partner_id:
            orm_partner.write(cr, SUPERUSER_ID, [partner_id], billing_info, context=context)

        order_info = {
            'partner_id': partner_id,
            'message_follower_ids': [(4, partner_id), (3, website.partner_id.id)],
            'partner_invoice_id': partner_id,
        }
        order_info.update(order_obj.onchange_partner_id(cr, SUPERUSER_ID, [], partner_id, context=context)['value'])
        address_change = order_obj.onchange_delivery_id(cr, SUPERUSER_ID, [], order.company_id.id, partner_id,
                                                        checkout.get('shipping_id'), None, context=context)['value']
        order_info.update(address_change)
        if address_change.get('fiscal_position'):
            fiscal_update = order_obj.onchange_fiscal_position(cr, SUPERUSER_ID, [], address_change['fiscal_position'],
                                                               [(4, l.id) for l in order.order_line], context=None)['value']
            order_info.update(fiscal_update)

        order_info.pop('user_id')
        order_info.update(partner_shipping_id=checkout.get('shipping_id') or partner_id)

        order_obj.write(cr, SUPERUSER_ID, [order.id], order_info, context=context)

        return order.id or None

    def create_tx(self, cr, uid, acquirer_id, sale_order_id=None, context=None):
        pool = self.pool
        website = pool['website'].browse(cr, uid, 1, context=context)

        orm_user = pool['res.users']
        partner = orm_user.browse(cr, SUPERUSER_ID, uid, context).partner_id
        payment_obj = pool['payment.acquirer']
        transaction_obj = pool['payment.transaction']
        #order = website.sale_get_order(context=context)
        order = None
        if sale_order_id:
            order = self.sale_order_latest(cr, SUPERUSER_ID, None, sale_order_id=sale_order_id, context=context)
        else:
            order = self.sale_order_latest(cr, SUPERUSER_ID, partner.id, context=context)

        if not order or not order.order_line or acquirer_id is None:
            return None

        # find an already existing transaction
        tx = self.sale_get_transaction(partner.id)
        if tx:
            tx_id = tx.id
            if tx.sale_order_id.id != order.id or tx.state in ['error', 'cancel'] or tx.acquirer_id.id != acquirer_id:
                tx = False
                tx_id = False
            elif tx.state == 'draft':  # button cliked but no more info -> rewrite on tx or create a new one ?
                tx.write(dict(transaction_obj.on_change_partner_id(cr, SUPERUSER_ID, None, order.partner_id.id, context=context).get('values', {}), amount=order.amount_total))
        if not tx:
            tx_id = transaction_obj.create(cr, SUPERUSER_ID, {
                'acquirer_id': acquirer_id,
                'type': 'form',
                'amount': order.amount_total,
                'currency_id': order.pricelist_id.currency_id.id,
                'partner_id': order.partner_id.id,
                'partner_country_id': order.partner_id.country_id.id,
                'reference': pool['payment.transaction'].get_next_reference(order.name),
                'sale_order_id': order.id,
            }, context=context)
            #request.session['sale_transaction_id'] = tx_id
            tx = transaction_obj.browse(cr, SUPERUSER_ID, tx_id, context=context)

        # update quotation
        pool['sale.order'].write(
            cr, SUPERUSER_ID, [order.id], {
                'payment_acquirer_id': acquirer_id,
                'payment_tx_id': tx_id
            }, context=context)

        _logger.info("New transaction created %r" % tx_id)
        # create a contract here?

        # create a separate sale_order for tax and insurance attached to this
        # user

        return tx_id or None

    def sale_get_transaction(self, cr, partner_id, sale_order_id, context=None):
        pool = self.pool
        transaction_obj = pool['payment.transaction']
        ids = transaction_obj.search(cr, SUPERUSER_ID, [("partner_id", "=", partner_id), ("sale_order_id", "=", sale_order_id)], context=context)
        tx = transaction_obj.browse(cr, SUPERUSER_ID, ids, context=context)
        return tx

    def checkout(self, cr, uid, context=None):
        pool = self.pool
        website = pool['website'].browse(cr, uid, 1, context=context)
        orm_user = pool['res.users']
        partner = orm_user.browse(cr, SUPERUSER_ID, uid, context).partner_id
        order = self.sale_order_latest(cr, SUPERUSER_ID, partner.id, context=context)
        if not order:
            order = website.sale_get_order(force_create=1, context=context)
        values = self.checkout_values(cr, uid)
        return values

    def checkout_values(self, cr, uid, data=None, context=None):
        pool = self.pool
        website = pool['website'].browse(cr, uid, 1, context=context)
        sale_order_obj = pool['sale.order']

        orm_partner = pool['res.partner']
        orm_user = pool['res.users']
        orm_country = pool['res.country']
        state_orm = pool['res.country.state']

        country_ids = orm_country.search(cr, SUPERUSER_ID, [], context=context)
        countries = orm_country.browse(cr, SUPERUSER_ID, country_ids, context)
        states_ids = state_orm.search(cr, SUPERUSER_ID, [], context=context)
        states = state_orm.browse(cr, SUPERUSER_ID, states_ids, context)
        partner = orm_user.browse(cr, SUPERUSER_ID, uid, context).partner_id

        order = None
        checkout = {}
        shipping_id = None
        shipping_ids = []

        if not data:
            # We're not allowing anon users
            #checkout.update( self.checkout_parse("billing", partner) )
            #shipping_ids = orm_partner.search(cr, SUPERUSER_ID, [("parent_id", "=", partner.id), ('type', "=", 'delivery')], context=context)
            # create an order
            #values = {
                #'user_id': uid,
                #'partner_id': partner.id,
                #'pricelist_id': partner.property_product_pricelist.id,
                #'section_id': pool['ir.model.data'].get_object_reference(cr, uid, 'website', 'salesteam_website_sales')[1],
            #}
            #sale_order_id = sale_order_obj.create(cr, SUPERUSER_ID, values, context=context)
            # If partner id changes, update it
            #values = sale_order_obj.onchange_partner_id(cr, SUPERUSER_ID, [], partner.id, context=context)['value']
            #sale_order_obj.write(cr, SUPERUSER_ID, [sale_order_id], values, context=context)

            #order = sale_order_obj.browse(cr, SUPERUSER_ID, sale_order_id, context=context)
            _logger.info("website.user_id.id %r" % website.user_id.id)
            if uid != website.user_id.id:
                checkout.update( self.checkout_parse("billing", partner) )
                # type = delivery indicates shipping_info. type = contact
                # indicate partner info
                shipping_ids = orm_partner.search(cr, SUPERUSER_ID, [("parent_id", "=", partner.id), ('type', "=", 'delivery')], context=context)
            else:
                order = website.sale_get_order(force_create=1, context=context)
                if order.partner_id:
                    domain = [("partner_id", "=", order.partner_id.id)]
                    user_ids = pool['res.users'].search(cr, SUPERUSER_ID, domain, context=dict(context or {}, active_test=False))
                    if not user_ids or website.user_id.id not in user_ids:
                        checkout.update( self.checkout_parse("billing", order.partner_id) )

        else:
            # Process shipping and billing details
            # For mobile, automatically set billing to shipping
            _logger.info("checkout_values data %r" % data)
            checkout = self.checkout_parse('billing', data.get('checkout'))
            try:
                shipping_id = int(data["shipping_id"])
            except ValueError:
                pass
            if shipping_id == -1:
                checkout.update(self.checkout_parse('shipping', data.get('checkout')))

        if shipping_id is None:
            if not order:
                # Get an existing order
                order = self.sale_order_latest(cr, SUPERUSER_ID, partner.id, context=context)
                #order = website.sale_get_order(context=context)
            if order and order.partner_shipping_id:
                shipping_id = order.partner_shipping_id.id

        shipping_ids = list(set(shipping_ids) - set([partner.id]))

        if shipping_id == partner.id:
            shipping_id = 0
        elif shipping_id > 0 and shipping_id not in shipping_ids:
            shipping_ids.append(shipping_id)
        elif shipping_id is None and shipping_ids:
            shipping_id = shipping_ids[0]

        ctx = dict(show_address=1)
        shippings = []
        if shipping_ids:
            shippings = shipping_ids and orm_partner.browse(cr, SUPERUSER_ID, list(shipping_ids), ctx) or []
        if shipping_id > 0:
            shipping = orm_partner.browse(cr, SUPERUSER_ID, shipping_id, ctx)
            checkout.update( self.checkout_parse("shipping", shipping) )

        checkout['shipping_id'] = shipping_id

        countrylist = []
        stateslist = []
        for country in countries:
            #countrylist.append([country.id, country.name,])
            countrylist.append({'id': country.id, 'name': country.name,})
            #stateslist.append(self.country_states(cr, country.id))

        #_logger.info("stateslist %r" % self.country_states(cr, 235))
        _logger.info("checkout_values checkout %r" % checkout)
        return {
            'countries': countrylist,
            #'states': stateslist,
            'checkout': checkout,
            'shipping_id': partner.id != shipping_id and shipping_id or 0,
            'shippings': shippings,
            'error': {},
            'has_check_vat': hasattr(pool['res.partner'], 'check_vat')
        }

    def add_to_cart(self, cr, uid, product_id, line_id=None, add_qty=1, set_qty=1, context=None, **kwargs):
        """ When add to cart button is clicked, Odoo updates sale_order_line
        If it's the first ever item added to cart by this user, Odoo creates
        a sale_order for it. Subsequent items added to cart creates a
        sale_order_line and update the sale_order
        """
        ids = [1]
        pool = self.pool
        website = pool['website'].browse(cr, uid, 1, context=context)
        sale_order_obj = pool['sale.order']
        sol = pool['sale.order.line']
        orm_user = pool['res.users']
        partner = orm_user.browse(cr, SUPERUSER_ID, uid, context).partner_id
        # Create a sale order for this partner using the public user template
        # (3)

        order = self.sale_order_latest(cr, SUPERUSER_ID, partner.id, context=context)
        # If user doesnt have a sale_order, create it
        if not order:
            values = {
                'user_id': uid,
                'partner_id': partner.id,
                'pricelist_id': partner.property_product_pricelist.id,
                'section_id': pool['ir.model.data'].get_object_reference(cr, uid, 'website', 'salesteam_website_sales')[1],
            }
            sale_order_id = sale_order_obj.create(cr, SUPERUSER_ID, values, context=context)
            values = sale_order_obj.onchange_partner_id(cr, SUPERUSER_ID, [], partner.id, context=context)['value']
            sale_order_obj.write(cr, SUPERUSER_ID, [sale_order_id], values, context=context)
            order = sale_order_obj.browse(cr, SUPERUSER_ID, sale_order_id, context=context)

        _logger.info("order %r" % order)
        # Perform cart_update.
        for so in order:
            if so.state != 'draft':
                raise osv.except_osv(_('Error!'), _('It is forbidden to modify a sale order which is not in draft status'))
            if line_id != False:
                line_ids = so._cart_find_product_line(product_id, line_id, context=context, **kwargs)
                if line_ids:
                    # Item is already in cart
                    line_id = line_ids[0]

            # Create line if no line with product_id can be located
            if not line_id:
                values = self._website_product_id_change(cr, SUPERUSER_ID, ids, so.id, product_id, qty=1, context=context)
                line_id = sol.create(cr, SUPERUSER_ID, values, context=context)
                if add_qty:
                    add_qty -= 1

            # compute new quantity
            if set_qty:
                quantity = set_qty
            elif add_qty != None:
                quantity = sol.browse(cr, SUPERUSER_ID, line_id, context=context).product_uom_qty + (add_qty or 0)

            # Remove zero of negative lines
            if quantity <= 0:
                sol.unlink(cr, SUPERUSER_ID, [line_id], context=context)
            else:
                # update line
                values = self._website_product_id_change(cr, SUPERUSER_ID, ids, so.id, product_id, qty=quantity, line_id=line_id, context=context)
                values['product_uom_qty'] = quantity
                sol.write(cr, SUPERUSER_ID, [line_id], values, context=context)

        return {'line_id': line_id, 'quantity': quantity}

    def _website_product_id_change(self, cr, uid, ids, order_id, product_id, qty=0, line_id=None, context=None):
        pool = self.pool
        so = pool['sale.order'].browse(cr, SUPERUSER_ID, order_id, context=context)

        _logger.info("sale order %r" % so)
        values = pool['sale.order.line'].product_id_change(cr, SUPERUSER_ID, [],
            pricelist=so.pricelist_id.id,
            product=product_id,
            partner_id=so.partner_id.id,
            fiscal_position=so.fiscal_position.id,
            qty=qty,
            context=dict(context or {}, company_id=so.company_id.id)
        )['value']

        if line_id:
            line = pool['sale.order.line'].browse(cr, SUPERUSER_ID, line_id, context=context)
            values['name'] = line.name
        else:
            product = pool['product.product'].browse(cr, uid, product_id, context=context)
            values['name'] = product.description_sale and "%s\n%s" % (product.display_name, product.description_sale) or product.display_name

        values['product_id'] = product_id
        values['order_id'] = order_id
        if values.get('tax_id') != None:
            values['tax_id'] = [(6, 0, values['tax_id'])]
        return values

    def suggested_products(self, cr, product_id, context=None):
        product = self.pool['product.template'].browse(cr, SUPERUSER_ID, product_id, context=context)
        s = set(j.id for j in (product.alternative_product_ids or []))
        product_ids = random.sample(s, min(len(s),3))
        products = self.pool['product.template'].browse(cr, SUPERUSER_ID, product_ids, context=context)
        product_list = []
        if products:
            for product in products:
                sellers = product.seller_ids.name.display_name
                product_list.append({'id': product.id,
                                    'name': product.name,
                                    'price': product.list_price,
                                    'product_imageurl': '{0}/web/binary/image?model=product.template&field=image_medium&id={1}'.format(config.settings()['mobile_virtual_host'], product.id),
                                    'product_imageurl_big': '{0}/web/binary/image?model=product.template&field=image&id={1}'.format(config.settings()['mobile_virtual_host'], product.id),
                                    'sellers': sellers,
                                    'fin_structure_desc': product.fin_structure_desc,
                                    'fin_structure': product.fin_structure,
                                    'contract_term': product.contract_term,
                                    }
                                    )
        return product_list

    def _cart_suggested_products(self):
        pass

    def checkout_parse(self, address_type, data, remove_prefix=False):
        """ data is a dict OR a partner browse record
        """
        # set mandatory and optional fields
        assert address_type in ('billing', 'shipping')
        if address_type == 'billing':
            all_fields = self._get_mandatory_billing_fields() + self._get_optional_billing_fields()
            prefix = ''
        else:
            all_fields = self._get_mandatory_shipping_fields() + self._get_optional_shipping_fields()
            prefix = 'shipping_'

        # set data
        if isinstance(data, dict):
            query = dict((prefix + field_name, data[prefix + field_name])
                for field_name in all_fields if prefix + field_name in data)
        else:
            query = dict((prefix + field_name, getattr(data, field_name))
                for field_name in all_fields if getattr(data, field_name))
            if address_type == 'billing' and data.parent_id:
                query[prefix + 'street'] = data.parent_id.name

        if query.get(prefix + 'state_id'):
            query[prefix + 'state_id'] = int(query[prefix + 'state_id'])
        if query.get(prefix + 'country_id'):
            query[prefix + 'country_id'] = int(query[prefix + 'country_id'])

        if query.get(prefix + 'vat'):
            query[prefix + 'vat_subjected'] = True

        # query = self._post_prepare_query(query, data, address_type)

        if not remove_prefix:
            return query

        return dict((field_name, data[prefix + field_name]) for field_name in all_fields if prefix + field_name in data)

    def country_states(self, cr, country_id):
        pool = self.pool
        state_orm = pool['res.country.state']

        states = []
        states_ids = state_orm.search(cr, SUPERUSER_ID, [("country_id", "=", country_id)], context=None)
        states_obj = state_orm.browse(cr, SUPERUSER_ID, states_ids, context=None)
        for state in states_obj:
            #states.append([state.id, state.name])
            states.append({'id': state.id, 'state': state.name,})
        return states

    mandatory_billing_fields = ["name", "phone", "email", "street2", "city", "country_id"]
    optional_billing_fields = ["street", "state_id", "vat", "vat_subjected", "zip"]
    mandatory_shipping_fields = ["name", "phone", "street", "city", "country_id"]
    optional_shipping_fields = ["state_id", "zip"]

    def _get_mandatory_billing_fields(self):
        return self.mandatory_billing_fields

    def _get_optional_billing_fields(self):
        return self.optional_billing_fields

    def _get_mandatory_shipping_fields(self):
        return self.mandatory_shipping_fields

    def _get_optional_shipping_fields(self):
        return self.optional_shipping_fields
