# -*- coding: utf-8 -*-
from openerp import http

# class Statics(http.Controller):
#     @http.route('/statics/statics/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/statics/statics/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('statics.listing', {
#             'root': '/statics/statics',
#             'objects': http.request.env['statics.statics'].search([]),
#         })

#     @http.route('/statics/statics/objects/<model("statics.statics"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('statics.object', {
#             'object': obj
#         })