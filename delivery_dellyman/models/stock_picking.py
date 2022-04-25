import logging
import requests

from odoo import exceptions, fields, models, _

_logger = logging.getLogger(__name__)


class StockPicking(models.AbstractModel):

    _inherit = "stock.picking"

    carrier_type = fields.Selection(
        selection=[
            ("1", "Bike"),
            ("2", "Tricycle"),
            ("3", "Mini Van"),
            ("4", "Vans/Buses"),
            ("5", "Cars"),
        ],
        default="1",
    )
