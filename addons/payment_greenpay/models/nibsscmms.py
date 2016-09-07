import logging

# from openerp import models, fields, api, SUPERUSER_ID
from openerp import api, SUPERUSER_ID
from openerp.osv import osv, fields

from openerp.addons.payment_greenpay.controllers.main import InterswitchController


class nibss_cmms(osv.Model):
    _name = 'payment.acquirer'
    _inherit = 'payment.acquirer'

    def _get_nibss_cmms_endpoints(self, cr, uid, environment, context=None):
        if environment == 'prod':
            return {
                'cmms_form_url': 'https://stageserv.nibss.com/test_paydirect/pay',
            }
        else:
            return {
                'cmms_form_url': 'https://stageserv.nibss.com/test_paydirect/pay',
            }

    def _get_providers(self, cr, uid, context=None):
        providers = super(nibss_cmms, self)._get_providers(cr, uid, context=context)
        providers.append(['nibsscmms', 'Nibss cmms'])
        return providers

    def nibsscmms_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)

        _logger.info("partner_values %r" % partner_values)
        _logger.info("tx_values %r" % tx_values)
        tx = tx_values.get('tx')

        itx_tx_values = {
            'site_redirect_url': '%s%s' % (base_url, tx_values.get('return_url') or tx_values.get('site_redirect_url')),
            'tnx_ref': tx_values.get('tx_id') if tx_values.get('tx_id') else 0,
            'product_id': '',
            'pay_item_id': '',
            'cancel_url': '%s' % urlparse.urljoin(base_url, InterswitchController._cancel_url),
            'hash': '',
            'cust_id': tx_values['partner'].user_id.id,
            'cust_name': ' '.join([partner_values['first_name'], partner_values['last_name']]),
            'site_name': base_url,
            'local_date_time': tx.create_date if tx else 0,

        }

        tx_values.update(itx_tx_values)
        return partner_values, tx_values

    def nibsscmms_get_form_action_url(self, cr, uid, id, context=None):
        """ Callback URL given to interswitch """
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_nibss_cmms_endpoints(cr, uid, acquirer.environment, context=context)['interswitch_form_url']

class TxNibssCmms(osv.Model):
    _inherit = 'payment.transaction'

    _interswitch_valid_tx_status = []

    def nibsscmms_create(self, cr, uid, values, context=None):
        # For monthly payment, set tx state to draft
        # For 30% down payment, collect the money but still set tx state to
        # draft
        values['state'] = 'draft'

