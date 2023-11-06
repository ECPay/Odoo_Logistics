# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class DeliveryB2CTest(models.Model):
    _name = 'delivery.b2c.test'
    _description = '建立物流訂單 / 一段標測試資料產生(B2C)-測標平台預設'
    _rec_name = 'logistics_name'

    logistics_name = fields.Char(string='物流類型名稱')
    logistics_code = fields.Char(string='物流類型編碼')
