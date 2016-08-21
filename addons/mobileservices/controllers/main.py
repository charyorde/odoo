# -*- coding: utf-8 -*-
import logging
import json
import functools
import werkzeug

from openerp import http
from openerp.http import request
from openerp.addons.website.models.website import slug

PPG = 20
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

    #@http.route([
        #'/products',
        #'/products/page/<int:page>',
        #'/products/category/<model("product.public.category"):category>',
        #'/products/category/<model("product.public.category"):category>/page/<int:page>'
    #], type='json', auth="none", methods=['GET'])
    # def products(self, page=0, category=None, search='', **post):
        #cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        #product_obj = pool['product.template']

        #attrib_list = request.httprequest.args.getlist('attrib')
        #attrib_values = [map(int, v.split("-")) for v in attrib_list if v]
        #attrib_set = set([v[1] for v in attrib_values])

        #domain = self._get_search_domain(search, category, attrib_values)

        #if not context.get('pricelist'):
            #pricelist = self.get_pricelist()
            #context['pricelist'] = int(pricelist)
        #else:
            #pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)

        #product_count = product_obj.search_count(cr, uid, domain, context=context)
        #if search:
            #post["search"] = search
        #if category:
            #category = pool['product.public.category'].browse(cr, uid, int(category), context=context)
            #url = "/shop/category/%s" % slug(category)
        #if attrib_list:
            #post['attrib'] = attrib_list
        #pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)
        #product_ids = product_obj.search(cr, uid, domain, limit=PPG, offset=pager['offset'], order=self._get_search_order(post), context=context)
        #products = product_obj.browse(cr, uid, product_ids, context=context)

        #category_obj = pool['product.public.category']
        #category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        #categs = category_obj.browse(cr, uid, category_ids, context=context)

        #attributes_obj = request.registry['product.attribute']
        #attributes_ids = attributes_obj.search(cr, uid, [], context=context)
        #attributes = attributes_obj.browse(cr, uid, attributes_ids, context=context)

        #from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        #to_currency = pricelist.currency_id
        #compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        #values = {
            #'search': search,
            #'category': category,
            #'attrib_values': attrib_values,
            #'attrib_set': attrib_set,
            #'pager': pager,
            #'pricelist': pricelist,
            #'products': json.dumps(products.__dict__),
             #'bins': table_compute().process(products),
             #'rows': PPR,
            #'styles': styles,
            #'categories': categs,
            #'attributes': attributes,
            #'compute_currency': compute_currency,
             #'keep': keep,
            #'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
            #'attrib_encode': lambda attribs: werkzeug.url_encode([('attrib',i) for i in attribs]),
        #}

        #response = {
            #"jsonrpc": "2.0"
        #}
        #response["result"] = values
        #_logger.info(">>> jsonrpc response %r" % response)

        #return response


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
        """ Get a single pproduct """
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        template_obj = pool['product.template']
        mime, result = 'application/json', { }
        response = {
            "jsonrpc": "2.0"
        }
        return response

    @http.route('/m/product/<model("product.template"):product>/<string:category>', auth='none', type='json', methods=['GET'])
    def product_get_by_category(self, product, category, **kw):
        """ Get a single product from a single category """
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        template_obj = pool['product.template']
        mime, result = 'application/json', { }
        response = {
            "jsonrpc": "2.0"
        }
        return response
