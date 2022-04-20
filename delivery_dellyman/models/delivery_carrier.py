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

from geopy import distance

TIMEOUT = 20
REQUEST_HEADER = {"Content-type": "application/json"}


class DeliverCarrier(models.Model):
    _inherit = "delivery.carrier"

    dellyman_api_key = fields.Char(string="API Key")
    delivery_type = fields.Selection(selection_add=[("dellyman", "Dellyman")])
    dellyman_base_price = fields.Float(string="Base Price", required=False, default=500)
    dellyman_rate_per_km = fields.Float(
        default=20, required=False, string="Rate Per Km"
    )
    dellyman_base_distance = fields.Float(
        default=10, required=False, string="Base Distance"
    )
    dellyman_algorithm_ids = fields.One2many(
        comodel_name="dellyman.algorithm",
        inverse_name="delivery_carrier_id",
        ondelete="cascade",
    )

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
                "error_message": _(
                    "Error: this delivery method is not available for this address."
                ),
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

    def dellyman_send_shipping(self, pickings):
        url = "https://dev.dellyman.com/api/v3.0/BookOrder"
        headers = {
            "Authorization": "Bearer %s" % (self.dellyman_api_key),
        }
        payload = {
            "CustomerID": 2,
            "CustomerAuth": "dfSVhQ8jQh0trncHkdELvwHgskI1Rj0w",
            "CompanyID": 762,
            "PaymentMode": "pickup",
            "Vehicle": "Bike",
            "PickUpContactName": "Administrator",
            "PickUpContactNumber": "07068937300",
            "PickUpGooglePlaceAddress": "3 Allen Avenue Lagos Lagos",
            "PickUpLandmark": " ",
            "IsInstantDelivery": 1,
            "PickUpRequestedDate": "",
            "PickUpRequestedTime": "",
            "DeliveryRequestedTime": "",
            "Packages": [
                {
                    "PackageDescription": "Allen/OUT/00024",
                    "DeliveryContactName": "Babatope Ajepe",
                    "DeliveryContactNumber": "07055667789",
                    "DeliveryGooglePlaceAddress": "73 Allen Avenue Ikeja Lagos",
                    "DeliveryLandmark": "",
                }
                for picking in pickings
            ],
        }
        res = requests.post(url, json=payload, headers=headers)
        print(res.text, "!!!!!!!!!!!!!!!!!!!!!!!!1")


class DellymanAlgorithm(models.Model):
    _name = "dellyman.algorithm"
    _desscription = "Dellyman Algorithm"

    name = fields.Char(string="Name", required=True)
    to_amount = fields.Integer(string="Price To", required=True)
    percentage = fields.Float(string="Percentage", required=True)
    from_amount = fields.Integer(string="Price From", required=True)
    delivery_carrier_id = fields.Many2one(comodel_name="delivery.carrier")
