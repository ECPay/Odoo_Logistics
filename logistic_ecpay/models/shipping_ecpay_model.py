# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging

from werkzeug import urls

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from ..controllers.main import WebsiteSaleDeliveryECPay
from ..sdk.logistic_ecpay_sdk import ECPayLogistics, LogisticsNameMap

_logger = logging.getLogger(__name__)


class ShippingEcpayModel(models.Model):
    _name = 'shipping.ecpay.model'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='綠界物流訂單名稱')
    ReferenceNo = fields.Many2one('sale.order', string='訂單編號', groups='base.group_user', help='訂單編號')
    MerchantID = fields.Char(string='特店編號', groups='base.group_user', help='特店編號')
    MerchantTradeNo = fields.Char(
        string='廠商交易編號', groups='base.group_user', help='廠商交易編號')
    RtnCode = fields.Char(string='目前物流狀態', groups='base.group_user', help='目前物流狀態')
    RtnMsg = fields.Char(string='物流狀態說明', groups='base.group_user', help='物流狀態說明')
    TempLogisticsID = fields.Char(string='綠界暫存訂單編號', groups='base.group_user', help='綠界暫存訂單編號')
    LogisticsID = fields.Char(
        string='綠界訂單編號', groups='base.group_user', help='綠界訂單編號')
    LogisticsType = fields.Char(string='物流類型', groups='base.group_user', help='物流類型')
    LogisticsSubType = fields.Char(
        '物流子類型', groups='base.group_user', help='物流子類型')
    LogisticsStatus = fields.Char(string='貨態代碼', groups='base.group_user', help='貨態代碼')
    LogisticsStatusName = fields.Char(string='貨態代碼訊息', groups='base.group_user', help='貨態代碼訊息')
    GoodsAmount = fields.Char('商品金額', groups='base.group_user', help='商品金額')
    GoodsWeight = fields.Float(string='商品重量', groups='base.group_user', help='商品重量')
    UpdateStatusDate = fields.Char(
        string='物流狀態更新時間', groups='base.group_user', help='物流狀態更新時間')
    ReceiverName = fields.Char(string='收件人姓名', groups='base.group_user', help='收件人姓名')
    ReceiverPhone = fields.Char(string='收件人電話', groups='base.group_user', help='收件人電話')
    ReceiverCellPhone = fields.Char(
        string='收件人手機', groups='base.group_user', help='收件人手機')
    ReceiverZipCode = fields.Char(
        string='收件人郵遞區號', groups='base.group_user', help='收件人郵遞區號')
    ReceiverEmail = fields.Char(string='收件人Email', groups='base.group_user', help='收件人Email')
    ReceiverAddress = fields.Char(
        string='收件人地址', groups='base.group_user', help='收件人地址')
    CVSPaymentNo = fields.Char(string='交貨便代碼 / 店到店編號', groups='base.group_user', help='交貨便代碼 / 店到店編號')
    CVSValidationNo = fields.Char(string='驗證碼', groups='base.group_user', help='驗證碼')
    BookingNote = fields.Char(string='配送編號 / 托運單號', groups='base.group_user', help='配送編號 / 托運單號')
    CVSStoreID = fields.Char(string='店舖編號', groups='base.group_user', help='店舖編號')
    CVSStoreName = fields.Char(string='店舖名稱', groups='base.group_user', help='店舖名稱')
    IsCollection = fields.Char(string='是否代收貨款', groups='base.group_user', help='是否代收貨款', default='N')
    CollectionAmount = fields.Char(string='代收金額', groups='base.group_user', help='代收金額')
    delivery_id = fields.Many2one('delivery.carrier', string='運送方式', groups='base.group_user', help='運送方式')
    is_convert = fields.Boolean('是否轉為正式物流訂單', deafult=False)
    HandlingCharge = fields.Char(string='物流費用', groups='base.group_user')
    ShipmentNo = fields.Char(string='物流單據號碼', groups='base.group_user')
    TradeDate = fields.Char(string='訂單成立時間', groups='base.group_user')

    def name_get(self):
        return [(r.id, f"{r.ReferenceNo.name}-{r.LogisticsID}") for r in self]

    def website_name_get(self):
        self.ensure_one()

        sun_type_name = LogisticsNameMap.get(self.LogisticsSubType, "")
        info = ''
        if self.LogisticsType == 'CVS':
            info = self.CVSStoreName or ''
        elif self.LogisticsType == 'HOME':
            info = f'{self.ReceiverZipCode or ""} {self.ReceiverAddress or ""}'

        return f'{sun_type_name} - {info}' if sun_type_name and info else ''

    def ecpay_get_form_action_url(self, cvs_type):
        # 取得 ECPay 的後台設定值
        if any(self):
            ecpay_setting = self.ReferenceNo.carrier_id
        else:
            ecpay_setting = self.env['delivery.carrier'].search([
                ('delivery_type', '=', 'ecpay')
            ], limit=1)

        return self.get_ecpay_urls(ecpay_setting.prod_environment)[cvs_type]

    @api.model
    def _ecpay_get_sdk(self):
        return ECPayLogistics(
            MerchantID=self.delivery_id.MerchantID,
            HashKey=self.delivery_id.HashKey,
            HashIV=self.delivery_id.HashIV
        )

    """TODO 查詢物流訂單狀態 Jason"""

    def get_trade_info(self, picking=None):
        # 取得 ECPay SDK
        logistics = self._ecpay_get_sdk()
        for rec in self:
            temp_data = logistics.query_shipping_info(rec)
            url = logistics.get_logistic_url(self.delivery_id.prod_environment, 'QueryLogisticsTradeInfo')
            response = logistics.send_process_data(temp_data, url)
            if response['RtnCode'] == 1 and response['RtnMsg'] == '成功':
                data = {
                    'HandlingCharge': response['HandlingCharge'],
                    'CollectionAmount': response['CollectionAmount'],
                    'LogisticsStatus': response['LogisticsStatus'],
                    'ShipmentNo': response['ShipmentNo'],
                    'RtnCode': response['RtnCode'],
                    'RtnMsg': response['RtnMsg'],
                    'GoodsAmount': response['GoodsAmount'],
                    'TradeDate': response['TradeDate'],
                    'BookingNote': response['BookingNote'] or False,
                    'CVSPaymentNo': response['CVSPaymentNo'] or False,
                    'CVSValidationNo': response['CVSValidationNo'] or False,
                }
                _logger.info(f'查詢物流訂單狀態：{response}')
                rec.write(data)
                body = _(f'物流狀態更新成功')
                rec.message_post(body=body)
            else:
                body = _(f'物流暫存訂單更新失敗，原因：{response["RtnMsg"]}')
                rec.message_post(body=body)

    """TODO 轉換物流暫存訂單至正式訂單 Jason"""

    # 暫存訂單轉正式物流訂單
    def create_temp_trade_send(self):
        # 取得公司設定記錄
        if self.env.context.get('company_id'):
            company = self.env['res.company'].browse(self.env.context['company_id'])
        else:
            company = self.env.user.company_id

        # 如果沒有填入寄件人資料
        if not (company.SenderName and
                company.SenderName and
                company.SenderZipCode and
                company.SenderAddress):
            raise ValidationError('請在"設定"的"公司"中填寫完整的寄件人資料')

        logistics = self._ecpay_get_sdk()
        for rec in self:
            temp_data = logistics.convert_logistic_temp_trade(rec)
            url = logistics.get_logistic_url(self.delivery_id.prod_environment, 'CreateByTempTrade')
            check = logistics.send_process_data(temp_data, url)
            if check['RtnCode'] != 1:
                body = _(f'物流暫存訂單轉換失敗，原因：{check["RtnMsg"]}')
                rec.message_post(body=body)
            # if response['RtnCode'] == 1 and response['RtnMsg'] == '成功':
            #     rec.LogisticsID = response['LogisticsID']
            #     rec.is_convert = True
            #     body = _('物流訂單轉換完成')
            #     rec.message_post(body=body)
            #     # break
            # else:
            #     body = _(f'物流正式訂單轉換失敗，原因：{response["RtnMsg"]}')
            #     rec.message_post(body=body)

    """TODO 更新物流暫存訂單 Jason"""

    def update_shipping_model_order(self):
        # 取得公司設定記錄
        if self.env.context.get('company_id'):
            company = self.env['res.company'].browse(self.env.context['company_id'])
        else:
            company = self.env.user.company_id

        # 如果沒有填入寄件人資料
        if not (company.SenderName and
                company.SenderName and
                company.SenderZipCode and
                company.SenderAddress):
            raise ValidationError('請在"設定"的"公司"中填寫完整的寄件人資料')
        base_url, ServerReplyURL = '', ''
        if self.delivery_id:
            base_url = self.delivery_id.ecpay_domain if self.delivery_id.ecpay_domain else self.env[
                'ir.config_parameter'].sudo().get_param(
                'web.base.url')
            ServerReplyURL = urls.url_join(base_url, WebsiteSaleDeliveryECPay._ServerReplyURL)
        logistics = self._ecpay_get_sdk()
        for rec in self:
            temp_data = logistics.update_logistic_temp_order(rec, company, ServerReplyURL)
            url = logistics.get_logistic_url(self.delivery_id.prod_environment, 'UpdateTempTrade')
            response = logistics.send_process_data(temp_data, url)
            if response['RtnCode'] == 1 and response['RtnMsg'] == '成功':
                body = _('物流暫存訂單更新完成')
                rec.message_post(body=body)
            else:
                body = _(f'物流暫存訂單更新失敗，原因：{response["RtnMsg"]}')
                rec.message_post(body=body)

    """TODO 托運單列印 Jason 初步處理"""

    # @api.model
    # def print_c2c_logistic(self, model_id=0):
    #     # 取得指定的物流訂單，並重新定義 self
    #     self = self.browse(model_id)
    #     if not any(self):
    #         return '<h1>Not given any order id</h1>'
    #     elif self.AllPayLogisticsID == 'Wait delivery confirm':
    #         raise UserError('請先進行交貨確認')
    #
    #     # 取得其交易方式
    #     delivery_carrier = self.ReferenceNo.carrier_id
    #     if not any(delivery_carrier):
    #         raise UserError('此筆訂單無設定交貨方式')
    #
    #     # 取得 ECPay 的後台設定值
    #     ecpay_type = delivery_carrier.ecpay_type if delivery_carrier else ''
    #     logistics_type = (self.LogisticsType or '').lower()
    #
    #     # 取得 ECPay 的 SDK
    #     ecpay_logistic_sdk = self._ecpay_get_sdk()
    #     print_c2c_bill_params = {
    #         'AllPayLogisticsID': self.AllPayLogisticsID,
    #         'PlatformID': '',
    #     }
    #
    #     if logistics_type == 'cvs' and ecpay_type == 'c2c':
    #         subtype = self.LogisticsSubType
    #         # 統一超商
    #         if subtype == 'UNIMARTC2C':
    #             action_url = self.ecpay_get_form_action_url('PRINT_UNIMART_C2C_BILL')
    #             if len(self.CVSPaymentNo) < 12:
    #                 print_c2c_bill_params.update({
    #                     'CVSPaymentNo': self.CVSPaymentNo,
    #                     'CVSValidationNo': self.CVSValidationNo
    #                 })
    #             else:
    #                 print_c2c_bill_params.update({
    #                     'CVSPaymentNo': self.CVSPaymentNo[:len(self.CVSPaymentNo) - 4],
    #                     'CVSValidationNo': self.CVSPaymentNo[len(self.CVSPaymentNo) - 4:]
    #                 })
    #
    #             final_params = ecpay_logistic_sdk.print_unimart_c2c_bill(
    #                 action_url=action_url,
    #                 client_parameters=print_c2c_bill_params)
    #         # 全家
    #         elif subtype == 'FAMIC2C':
    #             action_url = self.ecpay_get_form_action_url('PRINT_FAMILY_C2C_BILL')
    #             print_c2c_bill_params.update({
    #                 'CVSPaymentNo': self.CVSPaymentNo,
    #             })
    #
    #             final_params = ecpay_logistic_sdk.print_family_c2c_bill(
    #                 action_url=action_url,
    #                 client_parameters=print_c2c_bill_params)
    #         # 萊爾富
    #         elif subtype == 'HILIFEC2C':
    #             action_url = self.ecpay_get_form_action_url('PRINT_HILIFE_C2C_BILL')
    #             print_c2c_bill_params.update({
    #                 'CVSPaymentNo': self.CVSPaymentNo,
    #             })
    #
    #             final_params = ecpay_logistic_sdk.print_hilife_c2c_bill(
    #                 action_url=action_url,
    #                 client_parameters=print_c2c_bill_params)
    #         else:
    #             return f"<h1>LogisticsSubType is wrong! (subtype:{subtype})</h1>"
    #
    #     elif logistics_type == 'home' or (logistics_type == 'cvs' and ecpay_type == 'b2c'):
    #         action_url = self.ecpay_get_form_action_url('PRINT_TRADE_DOC')
    #         final_params = ecpay_logistic_sdk.print_trade_doc(
    #             action_url=action_url,
    #             client_parameters=print_c2c_bill_params)
    #     else:
    #         return f"<h1>無法對應的交貨方式(id:{model_id}, carrier:{ecpay_type}, type:{logistics_type})</h1>"
    #
    #     hidden_field = [f'<input type="hidden" name="{key}" value="{value}">' for key, value in
    #                     final_params.items()]
    #     return f"""
    #         <form id="ecpay_print" action="{action_url}" method="POST">
    #             {''.join(hidden_field)}
    #         </form
    #     """
    def print_logistic_order(self):
        # 全選的物流訂單必須為相同的LogisticsSubType
        subtypes = {order['LogisticsSubType'] for order in self}
        if len(subtypes) > 1:
            raise UserError("所選的訂單包含不同的物流訂單類型，請重新選擇。")
        else:
            logistics = self._ecpay_get_sdk()
            logistics_data: list = list({order.LogisticsID for order in self})

            logistics_order = {
                "MerchantID": logistics.MerchantID,
                "LogisticsSubType": self[0].LogisticsSubType,
            }
            print_data = logistics.print_shipping_info(logistics_order, logistics_data)
            url = logistics.get_logistic_url(self.delivery_id.prod_environment, 'PrintTradeDocument')
            return logistics.request_html(print_data, url)
            # if response['RtnCode'] == 1 and response['RtnMsg'] == '成功':
            #     for order in self:
            #         body = _(f'物流訂單列印完成，物流訂單編號：{order.LogisticsID}')
            #         order.message_post(body=body)
            # else:
            #     raise UserError(response['RtnMsg'])
