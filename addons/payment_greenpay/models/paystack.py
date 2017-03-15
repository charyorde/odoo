# -*- coding: utf-8 -*-
import urlparse
import urllib2
import logging
import json
import requests

from openerp import api, SUPERUSER_ID
#from openerp.osv import osv, fields
from openerp import models, fields, api
from openerp.tools import float_round
from openerp.tools.float_utils import float_compare, float_repr

from openerp.addons.payment_greenpay.controllers.main import PaystackController

_logger = logging.getLogger(__name__)


class payment_paystack(models.Model):
    _name = 'payment.acquirer'
    _inherit = 'payment.acquirer'

    paystack_api_access_token = fields.Char(string="Access Token")
    paystack_api_test_access_token = fields.Char(string="Test Access Token",
                                                 default="sk_test_cc3888953b8fed26272697c15f4894f94ec7ef54")

    def _get_paystack_endpoints(self, cr, uid, environment, context=None):
        return {'paystack_form_url':
                'https://api.paystack.co/transaction/initialize',
                'paystack_verify_reference_url':
                'https://api.paystack.co/transaction/verify/reference'}

    def _get_providers(self, cr, uid, context=None):
        providers = super(payment_paystack, self)._get_providers(cr, uid, context=context)
        providers.append(['paystack', 'PayStack'])
        return providers

    def paystack_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        """ This form should return extra tx and partner values to be made
        part of the transaction. see payment_acquirer.render"""
        pool = self.pool
        base_url = pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)
        user_obj = pool['res.users']
        _logger.info("partner_values %r" % partner_values)
        _logger.info("tx_values %r" % tx_values)
        tx = tx_values.get('tx')
        partner = tx_values['partner']
        user_id = partner.user_id.id or user_obj.search(cr, uid, [('partner_id', '=', partner.id)])[0]
        custom = {'custom_fields': [{'user_id': user_id,
                                     'cancel_url': '%s' % urlparse.urljoin(base_url, PaystackController._cancel_url),
                                     'currency': tx_values['currency'].symbol,
                                     'acquirer_id': tx_values['acquirer_id'],
                                     'order_id': tx_values['order_id']}]}

        # Paystack tx_values
        itx_tx_values = {
            'amount': tx_values['amount'],
            'callback_url': '%s' % urlparse.urljoin(base_url, PaystackController._return_url),
            'reference': tx_values.get('reference'),
            'email': partner_values['email'],
            'metadata': json.dumps(custom)
        }
        tx_values.update(itx_tx_values)
        return partner_values, tx_values

    def paystack_get_form_action_url(self, cr, uid, id, context=None):
        """ Callback URL given to paystack """
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_paystack_endpoints(cr, uid, acquirer.environment, context=context)['paystack_form_url']

    def _paystack_get_access_token(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        token = acquirer.paystack_api_test_access_token
        if acquirer.environment == 'production':
            token = acquirer.paystack_api_access_token
        return token

    def _make_header(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        token = self._paystack_get_access_token(cr, uid, id)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % token,
        }
        return headers



class TxPaystack(models.Model):
    _inherit = 'payment.transaction'

    # tx_token = fields.Char(help="A token is generated per new transaction")
    #_paystack_valid_tx_status = []

    # ----------------------
    # FORM RELATED METHODS
    # ----------------------
    def _paypal_form_get_tx_from_data(self, cr, uid, data, context=None):
        reference, txn_id = data.get('reference'), data.get('txn_id')
        if not reference or not txn_id:
            error_msg = 'Paystack: received data with missing reference (%s) or txn_id (%s)' % (reference, txn_id)
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        tx_ids = self.pool['payment.transaction'].search(cr, uid, [('reference', '=', reference)], context=context)
        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'Paystack: received data for reference %s' % (reference)
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return self.browse(cr, uid, tx_ids[0], context=context)

    #def _paypal_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        #pass

    #def _paypal_form_validate(self, cr, uid, tx, data, context=None):
        #pass

    # --------------------------------------------------
    # SERVER2SERVER RELATED METHODS
    # --------------------------------------------------

    def _paystack_s2s_send(self, cr, uid, values, cc_values, context=None):
        acquirer_obj = self.pool['payment.acquirer']
        order_obj = self.pool['sale.order']
        meta = json.loads(values['metadata'])['custom_fields'][0]
        acquirer_id = meta['acquirer_id']
        order = order_obj.browse(cr, uid, [meta['order_id']])
        tx_values = {
            'acquirer_id': acquirer_id,
            'type': 'server2server',
            #'amount': order.amount_total,
            'amount': int(1.0 * 100),
            'currency_id': order.pricelist_id.currency_id.id,
            'partner_id': order.partner_id.id,
            'partner_country_id': order.partner_id.country_id.id,
            'reference': self.get_next_reference(cr, uid, order.name),
            'sale_order_id': order.id,
        }
        tx_id = self.create(cr, uid, tx_values, context=context)
        tx = self.browse(cr, uid, tx_id, context=context)
        # update sale order
        order_obj.write(
            cr, SUPERUSER_ID, [order.id], {
                'payment_tx_id': tx_id
            }, context=context)

        token = acquirer_obj._paystack_get_access_token(cr, uid, acquirer_id)
        headers = acquirer_obj._make_header(cr, uid, acquirer_id)
        values['reference'] = tx_values['reference']
        _logger.info("Paystack payload %r" % values)
        data = json.dumps(values)
        url = acquirer_obj.paystack_get_form_action_url(cr, uid, acquirer_id)
        resp = requests.post(url, headers=headers, data=data)
        _logger.info("Paystack init response %r" % resp.text)
        if resp.status_code == 200:
            res = (tx_id, resp.json())
        else:
            res = (tx_id, False)
        return res

    #def paystack_create(self, cr, uid, values, context=None):
        # return self.s2s_create(cr, uid, values, context=None)

    def _paystack_s2s_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        invalid_parameters = []
        _logger.info('Received a response from Paystack %s', data)
        values = data.get('data')
        if values.get('domain') == "test":
            _logger.warning(
                'Received a notification from Paystak test environment'
            ),
        if tx.acquirer_reference and values.get('reference') != tx.acquirer_reference:
            invalid_parameters.append(('reference', values.get('reference'), tx.acquirer_reference))

        return invalid_parameters

    def _paystack_s2s_validate(self, cr, uid, tx, data, context=None):
        _logger.info('Validating Paystack payment %r' % data)
        values = data.get("data")
        status = values.get('status')
        customer = values.get("customer")
        data = {
            'acquirer_reference': values.get('reference'),
            'partner_reference': customer.get('id')
        }
        if status == "success":
            _logger.info('Validated Paystack payment for tx %s: set as done' % (tx.reference))
            data.update(state='done', date_validate=values.get('transaction_date', fields.datetime.now()))
            return tx.write(data)
        else:
            error = 'Received unrecognized status for Paystack payment %s: %s, set as error' % (tx.reference, status)
            _logger.info(error)
            data.update(state='error', state_message=error)
            return tx.write(data)

    def unlink(self, cr, uid, id, context=None):
        order_obj = self.pool['sale.order']
        order_id = order_obj.search(cr, uid, [('payment_tx_id', '=', id)], context=context)
        order = order_obj.browse(cr, uid, order_id)
        order_obj.write(
            cr, uid, [order.id], {
                'payment_tx_id': None
            }, context=context)
        return super(TxPaystack, self).unlink(cr, uid, id, context=context)

    def paystack_s2s_do_transaction(self, cr, uid, id, context=None, **kwargs):
        """ Interact with the gateway s2s """
        tx_id = self.browse(cr, uid, id, context=context)
        tx = self.browse(cr, uid, tx_id, context=context)
        account = tx.acquirer_id
        reference = tx.reference

        data = {}

        # Generate new token
        # data['SHASIGN'] = self.pool['payment.acquirer']._ogone_generate_shasign(tx.acquirer_id, 'in', data)

        direct_order_url = 'https://api.paystack.co/transaction/charge_authorization'

        request = urllib2.Request(direct_order_url, urlencode(data))
        result = urllib2.urlopen(request).read()
