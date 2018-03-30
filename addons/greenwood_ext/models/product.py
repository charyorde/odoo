# -*- coding: utf-8 -*-

from openerp import models, fields, api
import openerp.addons.decimal_precision as dp


class product_template(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'


    fin_structure = fields.Selection([('monthly', 'Monthly Payments'),
                                      ('6mrp', '6 Months Repayment Plan'),
                                      ('balloon', 'Balloon Payment')],
                                    string="Finance Structure", default='monthly')
    contract_term = fields.Selection([('12 months', '12 months'),
                                      ('18 months', '18 months'),
                                      ('24 months', '24 months'),
                                      ('36 months', '36 months'),
                                      ('48 months', '48 months')],
                                     string="Contract term", default='12 months')
    fin_structure_desc = fields.Text(string="Description", default='')
    fin_note = fields.Text(string="Payment note", default='')
    product_imagefile = fields.Char(string="Product image", default='placeholder.png', required=True)
    auto_insurance = fields.Float(string='Auto insurance', digits_compute=dp.get_precision('Product Price'), help="Yearly auto insurance")
    vehicle_servicing = fields.Float(string="Vehicle Servicing", digits_compute=dp.get_precision('Product Price'), help="3 Months Vehicle Servicing")
