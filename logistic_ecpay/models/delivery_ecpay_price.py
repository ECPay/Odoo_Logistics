# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class DeliveryECPayPrice(models.Model):
    _name = 'delivery.ecpay.price'
    _description = '用來定義物流不同的費用'

    name = fields.Char(string='物流類型名稱')
    code = fields.Char(string='物流類型編碼')
    price = fields.Float(string='運費')
