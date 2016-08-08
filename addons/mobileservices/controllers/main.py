# -*- coding: utf-8 -*-
import logging
import json
import functools

from openerp import http
from openerp.http import request

_logger = logging.getLogger(__name__)


class OAuthTokenValidator(object):

    """ A middleware to validate access token on all external HTTP
    requests
    """

    def __init__(self, app, token=None):
        self.app = app
        self.request_token = token

    def __call__(self, environ, start_response):
        def _validate_oauth_token(token):
            # invoke UAS token_validate service
            token = 'xyz'
            return start_response(token)
        _logger.info(">>> token validator %r" % self.app)
        # response = urllib.request
        return self.app(environ, start_response('200 OK', [('Content-Type', 'text/plain')]))


def oauth_token_validator(f=None, token=None):
    if f is None:
        _logger.info(">>> oauth token validator partial %r" % token)
        return functools.partial(oauth_token_validator, token=token)
    @functools.wraps(f)
    def wrapper(*args, **kw):
        _logger.info(">>> oauth token validator %r" % token)
        return f(*args, **kw)
    return wrapper


class Mobileservices(http.Controller):

    @http.route("/m/test", type="json", auth="none")
    def test(self):
        _logger.info(">>> request.session.db: %r" % request.session.db)
        # request.session.db = request.session.db or 'gw8'
        # _logger.info(">>> request object: %r" % token)
        # mime, result = 'application/json', { }
        return {
            "token": "3344448jvjvvkk",
        }

    @http.route('/m/ping', type='http', auth='none', methods=['GET', 'POST'])
    @oauth_token_validator(token='eeeier8r8494944jfjf')
    def ping(self, **kw):
        print(">>> request object: %r" % request)
        app = OAuthTokenValidator(request.httprequest.app)
        print(">>> OAuthTokenValidator: %r" % app)
        _logger.info(">>> request object: %r" % request)
        _logger.info(">>> OAuthTokenValidator: %r" % app)
        mime, result = 'application/json', { }
        response = {
            "message": "OK",
            "status": 200
        }
        return http.Response(json.dumps(response), status=response['status'], headers=[('Content-Type', mime)])

    @http.route('/m/signup', auth='public', type='json', methods=['POST'], website=True)
    def signup(self, **kw):
        _logger.info(">>> request object: %r" % request)
        app = OAuthTokenValidator(request.app)
        _logger.info(">>> OAuthTokenValidator: %r" % app)
        mime, result = 'application/json', { }
        response = {
            "jsonrpc": "2.0"
        }
        return response

    @http.route('/m/signup/facebook', auth='none', type='json')
    def signup_facebook(self, **kw):
        return http.request.render('mobileservices.listing', {
            'root': '/mobileservices/mobileservices',
            'objects': http.request.env['mobileservices.mobileservices'].search([]),
        })

    @http.route('/m/product/list', auth='none', type='json', methods=['GET'])
    def list(self, **kw):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        template_obj = pool['product.template']
        return http.request.render('mobileservices.listing', {
            'root': '/mobileservices/mobileservices',
            'objects': http.request.env['mobileservices.mobileservices'].search([]),
        })

    @http.route('/m/profile/create', auth='none', type='json', methods=['POST'])
    def profile_create(self):
        mime, result = 'application/json', { }
        response = {
            "jsonrpc": "2.0"
        }
        return response

    @http.route('/m/profile/update', auth='none', type='json', methods=['PUT'])
    def profile_update(self):
        mime, result = 'application/json', { }
        response = {
            "jsonrpc": "2.0"
        }
        return response

    @http.route('/m/product/cart/add', auth='none', type='json', methods=['POST'])
    def product_cart_add(self):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        template_obj = pool['product.template']
        mime, result = 'application/json', { }
        response = {
            "jsonrpc": "2.0"
        }
        return response

    @http.route('/m/product/cart/delete', auth='none', type='json', methods=['POST'])
    def product_cart_delete(self):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        template_obj = pool['product.template']
        mime, result = 'application/json', { }
        response = {
            "jsonrpc": "2.0"
        }
        return response

    @http.route('/m/product/cart/update', auth='none', type='json', methods=['POST'])
    def product_cart_update(self):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        template_obj = pool['product.template']
        mime, result = 'application/json', { }
        response = {
            "jsonrpc": "2.0"
        }
        return response

    @http.route('/m/product/checkout', auth='none', type='json', methods=['POST'])
    def product_checkout(self):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        template_obj = pool['product.template']
        mime, result = 'application/json', { }
        response = {
            "jsonrpc": "2.0"
        }
        return response

    @http.route('/m/product/payment', auth='none', type='json', methods=['POST'])
    def product_payment(self):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        template_obj = pool['product.template']
        mime, result = 'application/json', { }
        response = {
            "jsonrpc": "2.0"
        }
        return response

    @http.route('/m/product/<model("product.template"):product>', auth='none', type='json', methods=['GET'])
    def product_get(self, product):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        template_obj = pool['product.template']
        mime, result = 'application/json', { }
        response = {
            "jsonrpc": "2.0"
        }
        return response

    @http.route('/m/product/<model("product.template"):product>/<string:category>', auth='none', type='json', methods=['GET'])
    def product_get_by_category(self, product, category, **kw):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        template_obj = pool['product.template']
        mime, result = 'application/json', { }
        response = {
            "jsonrpc": "2.0"
        }
        return response
