# -*- coding: utf-8 -*-
import json
import logging
import pprint
import urllib2
import werkzeug
import requests
import urlparse

from openerp import http, SUPERUSER_ID
from openerp.http import request
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class GreenpayController(http.Controller):
    _cancel_url = '/payment/greenpay/cancel/'

    @http.route('/cgi-bin/pay', auth="user", type="http", website=True)
    def pay_instant(self, **kw):
        cr, uid, pool, context = request.cr, request.uid, request.registry, request.context
        _logger.info(">>>PAY INSTANT %r" % kw)
        # @TODO
        # - Collect partner shipping details. address, country. Needed on
        #   invoice and payment transaction
        # - Validate whether current user own or has permission
        # to view invoice
        inv_id, lines, order = int(kw.get('ref')), [], None
        invoice_obj = pool['account.invoice']
        payment_obj = pool['payment.acquirer']
        inv = invoice_obj.browse(cr, SUPERUSER_ID, [inv_id])

        sale_order_ids = pool['sale.order'].search(cr, SUPERUSER_ID, [])
        sale_orders = pool['sale.order'].browse(cr, SUPERUSER_ID, sale_order_ids)
        for so in sale_orders:
            if inv_id == so.invoice_ids.id:
                order = so

        for line in inv.invoice_line:
            lines.append({'name': line.name,
                          'quantity': float(line.quantity),
                          'price_unit': line.price_unit,
                          'amount': line.price_subtotal})
        values = {
            'date_invoice': inv.date_invoice,
            'company': inv.company_id.name,
            #'partner_shipping_id': '', # get from so
            'cust_name': inv.partner_id.name,
            'symbol': inv.currency_id.symbol,
            'lines': lines
        }
        values.update(kw)
        if order:
            acquirer = order.payment_acquirer_id
            render_ctx = dict(context, submit_class='btn btn-primary',
                              submit_txt=_('Pay Now'),
                              tx_url='/payment/paystack/pay')
            acquirer.button = payment_obj.render(
                cr, SUPERUSER_ID, acquirer.id,
                '/',
                #order.amount_total,
                int(1.00 * 100),
                inv.currency_id.id,
                partner_id=inv.partner_id.id,
                tx_values={
                    'return_url': '/shop/payment/validate',
                    'acquirer_id': acquirer.id,
                    'order_id': order.id
                },
                context=render_ctx)
            values.update({'partner_shipping_id': '',
                           'acquirer': acquirer})
        return request.render('theme_houzz.invoice', values)

    def _get_return_url(self, **post):
        """ Extract the return URL from the data coming from payment gateway. """
        return_url = post.pop('return_url', '')
        if not return_url:
            custom = json.loads(post.pop('custom', False) or '{}')
            return_url = custom.get('return_url', '/')
        return return_url

    @http.route('/payment/paypal/cancel', type='http', auth="none", csrf=False)
    def greenpay_cancel(self, **post):
        """ When the user cancels the payment: GET on this route """
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        _logger.info('Beginning Payment cancel request with post data %s', pprint.pformat(post))  # debug
        return_url = self._get_return_url(**post)
        return werkzeug.utils.redirect(return_url)


class InterswitchController(http.Controller):
    _cancel_url = '/payment/interswitch/cancel/'

class PaystackController(http.Controller):
    _return_url = '/payment/paystack/return'
    _cancel_url = '/payment/paystack/cancel/'

    def _get_return_url(self, **post):
        """ Extract the return URL from the data coming from payment gateway. """
        return_url = post.pop('return_url', '')
        if not return_url:
            custom = json.loads(post.pop('custom', False) or '{}')
            return_url = custom.get('return_url', '/')
        return return_url

    def paystack_validate_data(self, **post):
        res = False
        cr, uid, pool, context = request.cr, request.uid, request.registry, request.context
        acquirer_obj = pool['payment.acquirer']
        tx_obj = pool['payment.transaction']
        reference = post.get('reference')
        tx = None
        if reference:
            tx_ids = tx_obj.search(cr, SUPERUSER_ID, [('reference', '=', reference)], context=context)
            if tx_ids:
                tx = tx_obj.browse(cr, SUPERUSER_ID, tx_ids[0], context=context)
        paystack_urls = acquirer_obj._get_paystack_endpoints(cr, SUPERUSER_ID, tx and tx.acquirer_id and tx.acquirer_id.environment or 'prod', context=context)
        validate_url = urlparse.urljoin(paystack_urls['paystack_verify_reference_url'], reference)
        #urequest = urllib2.Request(validate_url)
        #uopen = urllib2.urlopen(urequest)
        #resp = uopen.read()
        acquirer_id = tx.acquirer_id.id
        headers = acquirer_obj._make_header(cr, SUPERUSER_ID, acquirer_id, context=context)
        resp = requests.get(validate_url, headers=headers)
        _logger.info('Paystack verify response %r' % resp)
        if resp.status_code == 200:
            data = resp.json()
            _logger.info('Paystack: validated data')
            res = tx_obj.s2s_feedback(cr, SUPERUSER_ID, tx.id, data, context=context)
            if res:
                # @TODO: mark invoice as paid
                # pool['account.voucher'].proforma_voucher(cr, uid, voucher_id)
                # send sales receipt
                pass
        else:
            _logger.warning('Paystack: unrecognized paystack answer, received %s' % resp.text)
        return res

    @http.route('/payment/paystack/return', type='http', auth="none")
    def paypal_dpn(self, **post):
        _logger.info('Beginning Paystack form_feedback with post data %s', pprint.pformat(post))  # debug
        return_url = self._get_return_url(**post)
        self.paystack_validate_data(**post)
        return werkzeug.utils.redirect(return_url)

    @http.route('/payment/paystack/pay', type='http', auth="none", csrf=False, methods=['POST'])
    def s2s_handler(self, **post):
        cr, uid, pool, context = request.cr, request.uid, request.registry, request.context
        _logger.info("Processing new payment %r" % post)
        res = pool['payment.transaction']._paystack_s2s_send(cr, SUPERUSER_ID, post, {}, context=context)
        #res = pool['payment.transaction'].create(cr, uid, post, {}, context=context)
        if res[1]:
            #data = json.dumps(dict((k,v) for k, v in [res]))
            data = res[1]['data']
            return werkzeug.utils.redirect(data['authorization_url'])
        else:
            # delete the tx
            pool['payment.transaction'].unlink(cr, SUPERUSER_ID, res[0])
            return_url = self._get_return_url(**post)
            return werkzeug.utils.redirect(return_url)


    @http.route('/payment/paystack/cancel', type='http', auth="none")
    def paypal_cancel(self, **post):
        """ When the user cancels its Paystack payment: GET on this route """
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        _logger.info('Beginning Paystack cancel with post data %s', pprint.pformat(post))  # debug
        return_url = self._get_return_url(**post)
        return werkzeug.utils.redirect(return_url)
