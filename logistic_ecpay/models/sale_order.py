# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ecpay_Logistics_id = fields.Many2one(
        'shipping.ecpay.model',
        string='綠界物流訂單編號',
        help='綠界物流訂單編號')

    def _check_carrier_quotation(self, force_carrier_id=None, keep_carrier=False) -> bool:
        if not force_carrier_id and not keep_carrier and self.carrier_id:
            return True

        return super()._check_carrier_quotation(force_carrier_id, keep_carrier)
