# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import requests
from werkzeug.urls import url_join

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round

import urllib
import datetime
from statistics import mean

TIMEOUT = 20
REQUEST_HEADER = {"Content-type": "application/json"}


class DeliverCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(selection_add=[("dellyman", "Dellyman")])

    dellyman_base_price = fields.Float(string="Price", default=100, help="Base price")

    dellyman_baseurl = fields.Char(string="Base URL")
    dellyman_apiid = fields.Char(string=" API ID")
    dellyman_apisecret = fields.Char(string="API Secret")
    dellyman_token = fields.Char(string="Token")
    dellyman_customer_auth = fields.Char(string="Customer Auth")
    dellyman_customer_id = fields.Char(string="Customer ID")
    dellyman_name = fields.Char(string="Username")
    dellyman_email = fields.Char(string="Email")
    dellyman_password = fields.Char(string="Password")
    dellyman_phonenumber = fields.Char(string="Phone")
    dellyman_company_id = fields.Char(string="Delivery CompanyID", default=643)

    def action_get_dellyman_token(self):
        """ 
        @API call response 
            {
                "authentication_token": "xda8qt147uf72s1z1mp06xafcln9o35tae9ovkiw",
                "ResponseCode": 100,
                "ResponseMessage": "Authentication Success",
            }
        """

        data = {"APISecret": self.dellyman_apisecret, "APIID": self.dellyman_apiid}
        endpoint = urllib.parse.urljoin(self.dellyman_baseurl, "api/v1.0/Authentication")

        try:
            req = requests.post(endpoint, data=json.dumps(data), headers=REQUEST_HEADER, timeout=TIMEOUT, verify=False,)
            req.raise_for_status()
        except requests.HTTPError:

            raise UserError(_("Please make sure that the APIID and API secret field are set"))

        res = req.json()
        if res.get("ResponseCode") != 100:
            raise UserError(res)
        self.dellyman_token = res.get("authentication_token")
        return res

    def action_get_dellyman_customer_auth(self, response):
        # after getting the authentication token, we need to validate/login with the token
        endpoint = urllib.parse.urljoin(self.dellyman_baseurl, "/api/v1.0/CustomerValidation")

        REQUEST_HEADER.update(
            {
                "Authorization": "Bearer %s" % self.dellyman_token,
                "APIID": self.dellyman_apiid,
                "APISecret": self.dellyman_apisecret,
            }
        )

        payload = {
            "Email": self.dellyman_email,
            "Password": self.dellyman_password,
        }
        req = requests.post(endpoint, data=json.dumps(payload), headers=REQUEST_HEADER, timeout=TIMEOUT)
        res = req.json()
        self.dellyman_customer_auth = res.get("CustomerAuth")
        self.dellyman_customer_id = res.get("CustomerID")
        REQUEST_HEADER["CustomerAuth"] = res.get("CustomerAuth")
        REQUEST_HEADER["CustomerID"] = res.get("CustomerAuth")
        return res

    def dellyman_authenticate(self):
        """Dellyman token and customer auth expires after 24 hours.

        """
        res = self.action_get_dellyman_token()
        return self.action_get_dellyman_customer_auth(res)

    def dellyman_calculate_amount_values(self, order):
        partner = order.partner_id
        company = order.company_id.partner_id
        partner_address = "%s %s %s %s" % (partner.street, partner.state_id.name, partner.city, partner.country_id.name)
        company_address = "%s %s %s %s" % (company.street, company.state_id.name, company.city, company.country_id.name)

        return {
            "CustomerID": int(self.dellyman_customer_id),
            "VehicleID": 1,
            "IsCoD": 1,
            "PickupRequestedTime": "06 AM to 09 PM",
            "PickupRequestedDate": datetime.date.today().strftime("%d/%m/%Y"),
            "PickupAddress": partner_address,
            "DeliveryAddress": [company_address],
        }

    def dellyman_rate_shipment(self, sale_order):
        endpoint = urllib.parse.urljoin(self.dellyman_baseurl, "/api/v1.0/CustomerCalculateAmount")
        data = self.dellyman_calculate_amount_values(sale_order)
        req = requests.post(endpoint, data=json.dumps(data), headers=REQUEST_HEADER, timeout=TIMEOUT)
        res = req.json()
        distance = mean([company.get("Distance") for company in res.get("Companies", [])])
        price = distance * self.dellyman_base_price
        return {"success": True, "price": price, "error_message": False, "warning_message": False}

    def dellyman_send_shipping(self, pickings):
        sale_id = pickings.mapped("sale_id")
        partner = sale_id.partner_id
        partner_address = "%s %s %s %s" % (partner.street, partner.state_id.name, partner.city, partner.country_id.name)
        payload = {
            "CustomerID": int(self.dellyman_customer_id),
            "CompanyID": self.dellyman_company_id,
            "CustomerAuth": self.dellyman_customer_auth,
            "VehicleID": 1,
            "IsCoD": 1,
            "PickUpContactName": partner.name,
            "PickUpContactNumber": partner.phone or partner.mobile,
            "PickUpGooglePlaceAddress": partner_address,
            "PickUpLandmark": " ",
            "PickUpRequestedDate": datetime.date.today().strftime("%d/%m/%Y"),
            "PickUpRequestedTime": "06 AM to 09 PM",
            "DeliveryRequestedTime": "06 AM to 09 PM",
            "Packages": [
                {
                    "PackageDescription": "Laptop",
                    "DeliveryContactName": "Babatope Ajepe",
                    "DeliveryContactNumber": "07068937300",
                    "DeliveryGooglePlaceAddress": partner_address,
                    "DeliveryLandmark": "",
                }
                for picking in pickings
            ],
        }
        print("***************dellyman_send_shipping*************************", sale_id)
        raise exceptions
        return {"exact_price": 5000, "tracking_number": 1111}

    def dellyman_get_tracking_link(self):
        print("******************************************dellyman_get_tracking_link")
        return False

    # def dellyman_cancel_shipment(self):
    #     pass

    # def dellyman_get_default_custom_package_code(self):
    #     pass
