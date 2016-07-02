# -*- coding: utf-8 -*-
import urlparse
import urllib2
import logging

# from openerp import models, fields, api, SUPERUSER_ID
from openerp import api, SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools import float_round
from openerp.tools.float_utils import float_compare, float_repr

from openerp.addons.payment_greenpay.controllers.main import InterswitchController

_logger = logging.getLogger(__name__)


class payment_interswitch(osv.Model):
    _name = 'payment.acquirer'
    _inherit = 'payment.acquirer'

    def _get_interswitch_endpoints(self, cr, uid, environment, context=None):
        if environment == 'prod':
            return {
                'interswitch_form_url': 'http://interswitch',
                'interswitch_rest_url': 'http://interswitch',
            }
        else:
            return 'https://stageserv.interswitchng.com/test_paydirect/pay'
            # return {
            #    'interswitch_form_url': 'http://localhost:3009/v1/',
            #    'interswitch_rest_url': 'http://localhost:3009/v1/mock-payment',
            #}

    def _get_providers(self, cr, uid, context=None):
        providers = super(payment_interswitch, self)._get_providers(cr, uid, context=context)
        providers.append(['interswitch', 'Interswitch'])
        return providers

    # def interswitch_compute_fees(self, cr, uid, id, amount, currency_id, country_id, context=None):
    #    """ Add Interswitch fees. see form_preprocess_values in payment_acquirer
    #    Get Interswitch fees and return it here"""
    #    acquirer = self.browse(cr, uid, id, context=context)
    #    country = self.pool['res.country'].browse(cr, uid, country_id, context=context)
    #    pass

    def interswitch_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        """ This form should return extra tx and partner values to be made
        part of the transaction. see payment_acquirer.render"""
        base_url = self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)

        _logger.info("partner_values %r" % partner_values)
        _logger.info("tx_values %r" % tx_values)
        # Interswitch tx_values
        itx_tx_values = {
            # 'amount': float_repr(float_round(partner_values['amount'], 2) * 100, 0),
            'site_redirect_url': '%s%s' % (base_url, tx_values['return_url']),
            'tnx_ref': tx_values['tx_id'],
            'product_id': '',
            'pay_item_id': '',
            'cancel_url': '%s' % urlparse.urljoin(base_url, InterswitchController._cancel_url),
            'hash': '',
            'cust_id': tx_values['partner'].user_id,
            'cust_name': ' '.join([partner_values['first_name'], partner_values['last_name']]),
        }
        tx_values.update(itx_tx_values)
        return partner_values, tx_values

    def interswitch_get_form_action_url(self, cr, uid, id, context=None):
        """ Callback URL given to interswitch """
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_interswitch_endpoints(cr, uid, acquirer.environment, context=context)['interswitch_form_url']

    def _interswitch_generate_token(self, acquirer, inout, values):
        """ Generate the shasign for incoming or outgoing communications
        For every communication exchanged between Greenwood
        and gateway, it must contain a 64-bit token.
        """
        # Validate all keys contained in the data sent/received in and out
        pass

class TxInterswitch(osv.Model):
    _inherit = 'payment.transaction'

    # tx_token = fields.Char(help="A token is generated per new transaction")
    _interswitch_valid_tx_status = []

    def interswitch_create(self, cr, uid, values, context=None):
        # For monthly payment, set tx state to draft
        # For 30% down payment, collect the money but still set tx state to
        # draft
        values['state'] = 'draft'

    def interswitch_s2s_do_transaction(self, cr, uid, id, context=None, **kwargs):
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

        _logger.debug('Interswitch response = %s', result)

        return self._interswitch_s2s_validate_tree(tx, tree)

    def _interswitch_s2s_validate_tree(self, tx, tree, tries=2):
        status = int(tree.get('STATUS') or 0)
        if status in self._interswitch_valid_tx_status:
            # increment paid field
            tx.write({

            })
            return True
        else:
            # Increment default count for this customer
            return False

    def _interswitch_form_get_tx_from_data(self, cr, uid, data, context=None):
        """ Given a data dict coming from gateway, verify it and
        find the related transaction record. Create a payment. """
        pass
