# -*- coding: utf-8 -*-
from odoo import http

# class DeliveryDellyman(http.Controller):
#     @http.route('/delivery_dellyman/delivery_dellyman/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/delivery_dellyman/delivery_dellyman/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('delivery_dellyman.listing', {
#             'root': '/delivery_dellyman/delivery_dellyman',
#             'objects': http.request.env['delivery_dellyman.delivery_dellyman'].search([]),
#         })

#     @http.route('/delivery_dellyman/delivery_dellyman/objects/<model("delivery_dellyman.delivery_dellyman"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('delivery_dellyman.object', {
#             'object': obj
#         })