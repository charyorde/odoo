from openerp import models, fields, api


class product_template(models.Model):
    """ All promo sales on available on the front page """
    _name = 'product.template'
    _inherit = 'product.template'
    promo_sale = fields.Boolean(string="Is it a promo sale", default=False,
                                help="Uncheck to disable promo sale")
    # promo_image = fields.Binary(string="Promo Image",
    #                            help="This field holds the image used as the promo image on the frontpage. It's scaled to 1024x1024px.")
    promo_image = fields.Char(string="Promo Image",
                                help="This field holds the image used as the promo image on the frontpage. It's scaled to 1024x1024px.")
    promo_image_scale = fields.Selection([('320x230', '320px by 230px'),
                                          ('320x155', '320px by 155px'),
                                          ('1440x640', '1440px x 640px'),
                                          ('660x400', '660px x 400px'),
                                          ('130x100', '130px by 100px'),
                                          ('390x300', '390px by 300px')], default='320x230', string="Promo image scale",
                                         help="The image would be scaled based on the selected pixels")
    block_type = fields.Selection([('main', 'Main'),
                                           ('featured', 'Featured'),
                                           ('most-viewed', 'Most Viewed'),
                                           ('reco', 'Recommended')],
                                          default='featured',
                                          string="Website block type",
                                          help="In which section of the website do you want to display this image")

    fin_structure = fields.Selection([('monthly', 'Monthly Payments'),
                                      ('6mrp', '6 Months Repayment Plan'),
                                      ('balloon', 'Balloon Payment')],
                                     string="Finance Structure", default='monthly')

    fin_structure_desc = fields.Text(string="Description", default='None')

    # gw_payment_acquirer = fields.Many2one('payment.acquirer', 'Payment Acquirer')

    # swift_etag = fields.Char(string="Swift etag")

    def onchange_promo_image_scale(self, cr, uid, ids, type):
        return {}

    def onchange_block_type(self, cr, uid, ids, type):
        return {}

    def get_product_promo_images(self, cr):
        pass

    @api.model
    def get_product_promo_image(self, id):
        # template_obj = self.pool.get('product.template')
        template_obj = self.env['product.template']
        context = self.env.context
        cr = self.env.cr
        # promo_image = template_obj.browse(cr, uid, [id], context=context).promo_image
        # promo_image = template_obj.browse(args).promo_image
        promo_image = template_obj.browse(int(id)).promo_image
        return promo_image

    @api.multi
    def write(self, vals):
        updated = super(product_template, self).write(vals)
        if updated:
            return updated
        return False
