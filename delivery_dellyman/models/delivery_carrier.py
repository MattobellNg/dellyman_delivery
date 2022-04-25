import json
import requests
from werkzeug.urls import url_join

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round
from odoo.tools.misc import flatten
import requests

import urllib
import datetime
from statistics import mean


try:
    from geopy import distance
except Exception:
    raise UserError("Please install geopy via pip install")

TIMEOUT = 20
REQUEST_HEADER = {"Content-type": "application/json"}


class DeliverCarrier(models.Model):
    _inherit = "delivery.carrier"

    dellyman_login = fields.Char(string="Login")
    dellyman_api_key = fields.Char(string="API Key")
    dellyman_password = fields.Char(string="Password")
    dellyman_base_url = fields.Char(string="Base URL")
    delivery_type = fields.Selection(selection_add=[("dellyman", "Dellyman")])
    dellyman_base_price = fields.Float(string="Base Price", required=False, default=500)
    dellyman_rate_per_km = fields.Float(default=20, required=False, string="Rate Per Km")
    dellyman_base_distance = fields.Float(default=10, required=False, string="Base Distance")
    dellyman_algorithm_ids = fields.One2many(
        comodel_name="dellyman.algorithm",
        inverse_name="delivery_carrier_id",
        ondelete="cascade",
    )
    dellyman_companyid = fields.Integer(string="Company ID", default=762)

    def get_distance_between_store_and_delivery(self, order):
        partner_shipping_id = order.partner_shipping_id

        partner_latitude = partner_shipping_id.partner_latitude
        partner_longitude = partner_shipping_id.partner_longitude

        company_latitude = self.company_id.partner_id.partner_latitude
        company_longitude = self.company_id.partner_id.partner_longitude
        if not partner_latitude or not partner_longitude:
            partner_shipping_id.geo_localize()
            partner_latitude = partner_shipping_id.partner_latitude
            partner_longitude = partner_shipping_id.partner_longitude

        if not company_latitude or not company_longitude:
            self.company_id.partner_id.geo_localize()
            company_latitude = self.company_id.partner_id.partner_latitude
            company_longitude = self.company_id.partner_id.partner_longitude

        store = (company_latitude, company_longitude)
        partner = (partner_latitude, partner_longitude)
        return distance.distance(partner, store).km

    def dellyman_rate_shipment(self, order):
        cr = self.env.cr
        carrier = self._match_address(order.partner_shipping_id)
        if not carrier:
            return {
                "success": False,
                "price": 0.0,
                "error_message": _("Error: this delivery method is not available for this address."),
                "warning_message": False,
            }
        amount_total = order.amount_total
        sql = """SELECT percentage * 0.01  FROM dellyman_algorithm WHERE %s  BETWEEN SYMMETRIC from_amount AND to_amount LIMIT 1"""

        cr.execute(sql, (amount_total,))
        percentage = flatten(cr.fetchall())
        price = (
            percentage[0] * amount_total
            if percentage[0] * amount_total > self.dellyman_base_price
            else self.dellyman_base_price
        )

        distance = self.get_distance_between_store_and_delivery(order)
        if distance > self.dellyman_base_distance:
            distance = distance - self.dellyman_base_price
            price = price + (distance * self.dellyman_rate_per_km)

        return {
            "success": True,
            "price": price,
            "error_message": False,
            "warning_message": False,
        }

    def _dellyman_customer_details(self):
        dellyman = self.env.ref("delivery_dellyman.delivery_carrier_dellyman")
        headers = {
            "Authorization": "Bearer %s" % (dellyman.dellyman_api_key),
        }
        url = url_join(dellyman.dellyman_base_url, "/api/v3.0/Login")
        payload = {"Email": dellyman.dellyman_login, "Password": dellyman.dellyman_password}
        res = requests.post(url, json=payload, headers=headers).json()
        return {
            "CustomerID": res.get("CustomerID"),
            "CustomerAuth": res.get("CustomerAuth"),
            "CompanyID": dellyman.dellyman_companyid,
        }

    def dellyman_send_shipping(self, pickings):
        dellyman = self.env.ref("delivery_dellyman.delivery_carrier_dellyman")
        url = url_join(dellyman.dellyman_base_url, "/api/v3.0/BookOrder")

        headers = {
            "Authorization": "Bearer %s" % (self.dellyman_api_key),
        }
        customer_details = self._dellyman_customer_details()
        for picking in pickings:
            payload = {
                "PaymentMode": "pickup",
                "Vehicle": picking.carrier_type,
                "PickUpContactName": picking.company_id.partner_id.name,
                "PickUpContactNumber": picking.company_id.partner_id.phone,
                "PickUpGooglePlaceAddress": picking.company_id.partner_id._display_address(),
                "PickUpLandmark": " ",
                "IsInstantDelivery": 1,
                "PickUpRequestedDate": "",
                "PickUpRequestedTime": "",
                "DeliveryRequestedTime": "",
                "Packages": [
                    {
                        "PackageDescription": move_line.product_id.name,
                        "DeliveryContactName": picking.partner_id.name,
                        "DeliveryContactNumber": picking.partner_id.phone,
                        "DeliveryGooglePlaceAddress": picking.partner_id._display_address(),
                    }
                    for move_line in picking.move_lines
                ],
            }
            payload.update(customer_details)
            exact_price = self._get_exact_price(picking)
            res = requests.post(url, json=payload, headers=headers).json()
            print(res, '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!@', payload)
        if res.get("ResponseCode") != 101:
            raise UserError( res.get("ResponseMessage"))
        return [{"exact_price": exact_price, "tracking_number": res.get("OrderID")}]

    def _get_exact_price(self, pickings):
        return pickings.mapped("sale_id").delivery_price


class DellymanAlgorithm(models.Model):
    _name = "dellyman.algorithm"
    _desscription = "Dellyman Algorithm"

    name = fields.Char(string="Name", required=True)
    to_amount = fields.Integer(string="Price To", required=True)
    percentage = fields.Float(string="Percentage", required=True)
    from_amount = fields.Integer(string="Price From", required=True)
    delivery_carrier_id = fields.Many2one(comodel_name="delivery.carrier")
