# -*- coding: utf-8 -*-
from openerp import http

# class Cheape(http.Controller):
#     @http.route('/cheape/cheape/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/cheape/cheape/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('cheape.listing', {
#             'root': '/cheape/cheape',
#             'objects': http.request.env['cheape.cheape'].search([]),
#         })

#     @http.route('/cheape/cheape/objects/<model("cheape.cheape"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('cheape.object', {
#             'object': obj
#         })