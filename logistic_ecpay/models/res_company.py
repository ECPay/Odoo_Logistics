# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LogisticEcpaySenderInfo(models.Model):
    _inherit = 'res.company'

    SenderName = fields.Char('寄件人姓名', groups='base.group_user', help='寄件人姓名')
    SenderPhone = fields.Char('寄件人電話', groups='base.group_user', help='寄件人電話')
    SenderCellPhone = fields.Char(
        '寄件人手機', groups='base.group_user', help='寄件人手機')
    SenderZipCode = fields.Char(
        '寄件人郵遞區號', groups='base.group_user', help='寄件人郵遞區號')
    SenderAddress = fields.Char(
        '寄件人地址', groups='base.group_user', help='寄件人地址')

    @api.constrains('SenderName')
    def _onchange_sender_name(self):
        chars = set(' !@#$%^&*()_+\-=[]{};\':\"\\|,.<>\/?')
        if any((c in chars) for c in self.SenderName):
            raise ValidationError("寄件人姓名不可以有符號!")

        length = len(self.SenderName)
        utf8_length = len(self.SenderName.encode('utf-8'))
        length = (utf8_length - length) / 2 + length
        if length < 4 or length > 10:
            raise ValidationError("寄件人姓名應限制 10 字元 (最多 5 個中文、10 個英文)")

        return True

    @api.constrains('SenderPhone')
    def _onchange_sender_phone(self):
        chars = set('1234567890()-#')
        if any((c not in chars) for c in self.SenderPhone):
            raise ValidationError("寄件人電話只允許數字 + 特殊符號；特殊符號僅限()-#")

        return True

    @api.constrains('SenderCellPhone')
    def _onchange_sender_cellphone(self):
        chars = set('1234567890')
        if any((c not in chars) for c in self.SenderCellPhone) or \
                (len(self.SenderCellPhone) != 10) or \
                self.SenderCellPhone[0:2] != '09':
            raise ValidationError("寄件人手機只允許數字、10碼、09開頭")
            return False

        return True
