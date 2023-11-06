# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    logistic_ecpay_id = fields.Many2one('shipping.ecpay.model', string='綠界物流訂單編號', help='綠界物流訂單編號')

    def action_confirm(self):
        res = super().action_confirm()
        logistic_ECPay_Order = self.env['shipping.ecpay.model']
        if self.origin or self.group_id:
            order_name = self.origin or self.group_id.name or False
            sale_id = self.env['sale.order'].search([('name', '=', order_name)], limit=1)
            logistic_order = logistic_ECPay_Order.search([('ReferenceNo', '=', sale_id.id)], limit=1)
            if logistic_order:
                self.logistic_ecpay_id = logistic_order.id
        return res
