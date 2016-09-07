# -*- coding: utf-8 -*-
from openerp import http

# class GreenwoodExt(http.Controller):
#     @http.route('/greenwood_ext/greenwood_ext/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/greenwood_ext/greenwood_ext/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('greenwood_ext.listing', {
#             'root': '/greenwood_ext/greenwood_ext',
#             'objects': http.request.env['greenwood_ext.greenwood_ext'].search([]),
#         })

#     @http.route('/greenwood_ext/greenwood_ext/objects/<model("greenwood_ext.greenwood_ext"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('greenwood_ext.object', {
#             'object': obj
#         })