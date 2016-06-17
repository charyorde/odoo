# -*- coding: utf-8 -*-
import urlparse
import urllib2
import logging

# from openerp import models, fields, api, SUPERUSER_ID
from openerp import api, SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools import float_round
from openerp.tools.float_utils import float_compare, float_repr

from openerp.addons.payment_greenpay.controllers.main import GreenpayController

_logger = logging.getLogger(__name__)


class payment_greenpay(osv.Model):
    # _name = 'payment_greenpay.payment_greenpay'
    _inherit = 'payment.acquirer'

    def _get_interswitch_endpoints(self, cr, uid, environment, context=None):
        if environment == 'prod':
            return {
                'interswitch_form_url': 'http://interswitch',
                'interswitch_rest_url': 'http://interswitch',
            }
        else:
            return {
                'interswitch_form_url': 'http://localhost:3009/v1/',
                'interswitch_rest_url': 'http://localhost:3009/v1/mock-payment',
            }

    def _get_providers(self, cr, uid, context=None):
        providers = super(payment_greenpay, self)._get_providers(cr, uid, context=context)
        providers.append(['greenpay', 'Greenpay'])
        return providers

    def greenpay_compute_fees(self, cr, uid, id, amount, currency_id, country_id, context=None):
        """ Returns the fees that's sent to Interswitch """
        acquirer = self.browse(cr, uid, id, context=context)
        country = self.pool['res.country'].browse(cr, uid, country_id, context=context)
        pass

    def greenpay_form_generate_values(self, cr, uid, id, values, context=None):
        """ This form contains the full transaction details values """
        base_url = self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)

        tx_values = {
            'amount': float_repr(float_round(values['amount'], 2) * 100, 0),
            'cancel_url': '%s' % urlparse.urljoin(base_url, GreenpayController._cancel_url),
        }
        return tx_values

    def greenpay_get_form_action_url(self, cr, uid, id, context=None):
        """ The POST endpoint to be interchanged with interswitch """
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_interswitch_endpoints(cr, uid, acquirer.environment, context=context)['interswitch_form_url']

    def _greenpay_generate_token(self, acquirer, inout, values):
        """ Generate the shasign for incoming or outgoing communications
        For every communication exchanged between Greenwood
        and gateway, it must contain a 64-bit token.
        """
        # Validate all keys contained in the data sent/received in and out
        pass

class TxGreenpay(osv.Model):
    _inherit = 'payment.transaction'

    # tx_token = fields.Char(help="A token is generated per new transaction")
    _greenpay_valid_tx_status = []

    def greenpay_s2s_do_transaction(self, cr, uid, id, context=None, **kwargs):
        """ Interact with the gateway s2s """
        tx_id = self.browse(cr, uid, id, context=context)
        tx = self.browse(cr, uid, tx_id, context=context)
        account = tx.acquirer_id
        reference = tx.reference

        data = {}

        # Generate new token
        # data['SHASIGN'] = self.pool['payment.acquirer']._ogone_generate_shasign(tx.acquirer_id, 'in', data)

        direct_order_url = 'https://secure.interswitch.com/ncol/%s/orderdirect.asp' % (tx.acquirer_id.environment)

        request = urllib2.Request(direct_order_url, urlencode(data))
        result = urllib2.urlopen(request).read()

        _logger.debug('Ogone response = %s', result)

        return self._greenpay_s2s_validate_tree(tx, tree)

    def _greenpay_s2s_validate_tree(self, tx, tree, tries=2):
        status = int(tree.get('STATUS') or 0)
        if status in self._greenpay_valid_tx_status:
            # increment paid field
            tx.write({

            })
            return True
        else:
            # Increment default count for this customer
            return False

    def _greenpay_form_get_tx_from_data(self, cr, uid, data, context=None):
        """ Given a data dict coming from gateway, verify it and
        find the related transaction record. Create a payment. """


class AccountPaymentGreenpayConfig(osv.TransientModel):
    _inherit = 'account.config.settings'

    _columns = {
        'module_payment_greenpay': fields.boolean(
            'Greenpay',
            help='-It installs the module payment_greenpay.'),
    }
