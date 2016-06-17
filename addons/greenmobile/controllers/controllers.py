# -*- coding: utf-8 -*-
from openerp import http

# class Greenmobile(http.Controller):
#     @http.route('/greenmobile/greenmobile/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/greenmobile/greenmobile/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('greenmobile.listing', {
#             'root': '/greenmobile/greenmobile',
#             'objects': http.request.env['greenmobile.greenmobile'].search([]),
#         })

#     @http.route('/greenmobile/greenmobile/objects/<model("greenmobile.greenmobile"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('greenmobile.object', {
#             'object': obj
#         })