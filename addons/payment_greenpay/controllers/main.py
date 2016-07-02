# -*- coding: utf-8 -*-
import json
import logging
import pprint
import urllib2
import werkzeug

from openerp import http, SUPERUSER_ID

_logger = logging.getLogger(__name__)


class GreenpayController(http.Controller):
    _cancel_url = '/payment/greenpay/cancel/'

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

#     @http.route('/payment_greenpay/payment_greenpay/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/payment_greenpay/payment_greenpay/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('payment_greenpay.listing', {
#             'root': '/payment_greenpay/payment_greenpay',
#             'objects': http.request.env['payment_greenpay.payment_greenpay'].search([]),
#         })

#     @http.route('/payment_greenpay/payment_greenpay/objects/<model("payment_greenpay.payment_greenpay"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('payment_greenpay.object', {
#             'object': obj
#         })

class InterswitchController(http.Controller):
    _cancel_url = '/payment/interswitch/cancel/'
