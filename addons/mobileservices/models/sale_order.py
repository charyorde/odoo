from openerp import models
from openerp import SUPERUSER_ID


class sale_order(models.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'

    def create_order(self, cr, uid, data, context=None):
        pool = self.pool
        orm_user = pool['res.users']
        product_obj = pool['product.product']
        sol = pool['sale.order.line']
        user_id = data.get('user_id')
        company_ids = pool['res.company'].search(cr, uid, [('name', '=', 'Cheape')], context=context)
        company_id = company_ids[0]
        partner = orm_user.browse(cr, uid, [user_id], context).partner_id
        currency = dict(pool['res.currency'].name_search(cr, uid, name=data['currency']))
        pricelist_id = pool['product.pricelist'].search(cr, uid,
                                                        [('currency_id', 'in', currency.keys()),
                                                         ('company_id', '=', company_id)])
        acquirer = dict(pool['payment.acquirer'].name_search(cr, uid, name='Paystack'))

        values = {
            'user_id': user_id,
            'partner_id': partner.id,
            'pricelist_id': pricelist_id[0],
            'section_id': pool['ir.model.data'].get_object_reference(cr, uid, 'website', 'salesteam_website_sales')[1],
            'company_id': company_id,
            'payment_acquirer_id': acquirer.keys()[0]
        }
        sale_order_id = self.create(cr, SUPERUSER_ID, values, context=context)
        cr.commit()
        values = self.onchange_partner_id(cr, SUPERUSER_ID, [], partner.id, context=context)['value']
        self.write(cr, SUPERUSER_ID, [sale_order_id], values, context=context)

        # create sale_order_line too
        product_tmpl_ids = data.get('product_id')
        product_ids = product_obj.search(cr, uid, [('product_tmpl_id', 'in', product_tmpl_ids)])
        products = product_obj.browse(cr, uid, product_ids)
        vals = self.prepare_products(cr, uid, sale_order_id, products)
        for val in vals:
            sol.create(cr, uid, val, context=context)
            cr.commit()

        order = self.browse(cr, uid, sale_order_id, context=context)
        return order if order else None

    def prepare_products(self, cr, uid, order_id, products, qty=1):
        values = []
        for product in products:
            values.append({
                'name': product.name,
                'product_id': product.id, 'order_id': order_id,
                'product_uom_qty': qty,
                'product_uom': product.uom_id.id
            })
        return values
