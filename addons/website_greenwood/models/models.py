# -*- coding: utf-8 -*-

from openerp import models, fields, api


class greenwood_account(models.Model):
    # _name = 'website_greenwood.account'
    _name = 'res.partner'
    _inherit = 'res.partner'

    # accountid = fields.Char(string='Greenwood account ID', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    # A Greenwood account can be individual or corporate
    # account_type = fields.Selection(
    #    [('individual', 'Individual'), ('corporate', 'Corporate')],
    #    'Account type', required=True, default='individual',
    #    help='A Greenwood account')
    bvn = fields.Integer(string="BVN")
    # uid = fields.Integer(related='res.partner.id', required=True)
    # uid = fields.Many2one('res.users', default=lambda self: self.env.user)
    # debit_date = fields.Char(default=create_debit_date, required=True, help='The preferred debit date of the recurrent sale')
    debit_date = fields.Datetime(string='Preferred debit date', required=True, default=fields.Datetime.now())
    empname = fields.Char(string="Employer",required=True,
                          # default=lambda self: 'None' if self.company_type != 'individual' else 'individual',
                          help='Your employer name')
    companyname = fields.Char(string="Company name",required=True,
                          # default=lambda self: 'None' if self.company_type != 'individual' else 'individual',
                          help='Your company name')
    identity_id = fields.Char(default='None', string="Upload your ID",
                              help='National passport preferred')
    company_reg_id = fields.Char(string="Reg Id",required=True,
                                 help='Company registration id')
    payslips= fields.Char(string='Latest payslips', required=True)

    # An individual account total monthly expenses
    mexpenses = fields.Float(string="Total monthly expenses", required=True)

    # address = fields.Char(string="Address", required=True,help="Your permanent address")
    # An individual account tenancy agreement
    tenancy = fields.Char(string="Tenancy Agreement", required=True)
    # Job position
    # job_position = fields.Char(string="Job Position", required=True)

    # A Greenwood account can be in pending, suspended, denied
    # or accepted state
    approval_status = fields.Char(default='pending',required=True)

    def create_debit_date(self, v):
        pass

    def create_payslip(self):
        pass

    def create_tenancy(self):
        pass

    @api.depends('company_type')
    def _compute_by_account_type(self):
        print "\n>>>>self", self
        if self.company_type != 'individual':
            return 'None'

    # @api.model
    # def create(self, vals):
    #    if vals.get('accountid', 'New') == 'New':
    #        vals['accountid'] = self.env['ir.sequence'].next_by_code('website_greenwood.account') or 'New'
    #        return super(greenwood_account, self).create(values)

    # @api.multi
    # def write_old(self, cr, uid, ids, values, context=None):
    #    updated = super(website_greenwood, self).write(cr, uid, ids, values, context=context)
    #    print("\n>>> updated write %s" % updated)
    #    if updated:
    #        return True
    #    return False

    @api.multi
    def write(self, vals):
        updated = super(greenwood_account, self).write(vals)
        if updated:
            return updated
        return False


    @api.multi
    def _get_greewood_account(self, val):
        pass

    @api.multi
    def credit_status(self, val):
        """ Get a Greenwood account credit status """
        approval_status = self.search([('uid', '=', val)]).approval_status
        if not approval_status:
            return 'pending'
        return approval_status

    @api.multi
    def _update_greenwood_account(self, val):
        pass

    @api.multi
    def find_user_by_userid(self, val):
        return self.search([('user_id', '=', val)])

    def _get_partner_id(self, cr, uid, id, context='None'):
        partner = self.pool['res.users'].browse(cr, uid, id, context=context).partner_id
        return partner.id
