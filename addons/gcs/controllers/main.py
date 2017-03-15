# -*- coding: utf-8 -*-
from openerp import http

# class Gcs(http.Controller):
#     @http.route('/gcs/gcs/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/gcs/gcs/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('gcs.listing', {
#             'root': '/gcs/gcs',
#             'objects': http.request.env['gcs.gcs'].search([]),
#         })

#     @http.route('/gcs/gcs/objects/<model("gcs.gcs"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('gcs.object', {
#             'object': obj
#         })