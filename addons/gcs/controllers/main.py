# -*- coding: utf-8 -*-
from openerp import http

# class CloudController(http.Controller):
#    @http.route('/cloud/gcs/', auth='public')
#    def index(self, **kw):
#        return "Hello, world"

#    @http.route('/cloud/products/', auth='public')
#    def product_list(self, **kw):
#        results = http.request.env['product.template'].get_cloud_products()
#        return request.make_response(html_escape(simplejson.dumps(result)))

#     @http.route('/gcs/gcs/objects/<model("gcs.gcs"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('gcs.object', {
#             'object': obj
#         })
