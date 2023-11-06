# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging

from werkzeug import urls

from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError
from ..controllers.main import WebsiteSaleDeliveryECPay
from ..sdk.logistic_ecpay_sdk import ECPayLogistics, ECPayTestURL, ECPayURL

_logger = logging.getLogger(__name__)


class LogisticEcpay(models.Model):
    """ A Shipping Provider

    In order to add your own external provider, follow these steps:

    1. Create your model MyProvider that _inherit 'delivery.carrier'
    2. Extend the selection of the field "delivery_type" with a pair
       ('<my_provider>', 'My Provider')
    """
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('ecpay', 'ECPay')], ondelete={'ecpay': 'set default'})

    MerchantID = fields.Char(
        '特店編號',
        required_if_provider='ecpay',
        groups='base.group_user',
        help='特店編號')
    HashKey = fields.Char(
        '介接 HashKey', groups='base.group_user', required_if_provider='ecpay')
    HashIV = fields.Char(
        '介接 HashIV', groups='base.group_user', required_if_provider='ecpay')
    IsCollection = fields.Boolean(string='是否代收貨款', default=False, groups='base.group_user')
    ecpay_unimart = fields.Boolean(
        '統一超商', default=True, help='統一超商', groups='base.group_user')
    ecpay_unimart_price = fields.Integer(
        '統一超商運費', help='統一超商運費', groups='base.group_user')

    ecpay_fami = fields.Boolean(
        '全家', default=True, help='全家', groups='base.group_user')
    ecpay_fami_price = fields.Integer(
        '全家運費', help='全家運費', groups='base.group_user')

    ecpay_hilife = fields.Boolean(
        '萊爾富', default=True, help='萊爾富', groups='base.group_user')
    ecpay_hilife_price = fields.Integer(
        '萊爾富運費', help='萊爾富運費', groups='base.group_user')

    ecpay_tcat = fields.Boolean(
        '黑貓', default=True, help='黑貓', groups='base.group_user')
    ecpay_tcat_price = fields.Integer(
        '黑貓運費', help='黑貓運費', groups='base.group_user')

    ecpay_ecan = fields.Boolean(
        '宅配通', default=True, help='宅配通', groups='base.group_user')
    ecpay_ecan_price = fields.Integer(
        '宅配通運費', help='宅配通運費', groups='base.group_user')
    ecpay_domain = fields.Char(
        '網域名稱',
        default='https://your_domain_name/',
        groups='base.group_user',
        required_if_provider='ecpay')

    ecpay_type = fields.Selection(
        selection=[('b2c', 'B2C'), ('c2c', 'C2C'), ],
        string='會員種類')

    ecpay_cod = fields.Boolean(
        '超商到店取貨付款', default=True, help='超商到店取貨付款', groups='base.group_user')

    ezship_mart = fields.Boolean(
        '便利配', default=True, help='便利配', groups='base.group_user')
    ezship_mart_price = fields.Integer(
        '便利配運費', help='便利配運費', groups='base.group_user')

    home_ship = fields.Boolean(
        '郵寄宅配', default=True, help='郵寄宅配', groups='base.group_user')
    home_ship_price = fields.Integer(
        '郵寄宅配運費', help='郵寄宅配運費', groups='base.group_user')
    delivery_b2c_test = fields.Many2many('delivery.b2c.test', string='B2C-測標用', help='請選擇簽約時的B2C物流商')
    payment_provider_id = fields.Many2one('payment.provider', string='金流固定', help='貨到付款請選擇金流固定')

    @api.model
    def _ecpay_get_sdk(self):
        # 取得 ECPay 的後台設定值
        return ECPayLogistics(
            MerchantID=self.MerchantID,
            HashKey=self.HashKey,
            HashIV=self.HashIV)

    #   建立一段標測試資料產生(B2C)
    def ecpay_b2c_test(self):
        if not self.delivery_b2c_test:
            raise UserError('請選擇簽約時的B2C物流商')
        if self.ecpay_type != 'b2c':
            raise UserError('請選擇B2C物流類型，才可進行此方法測標')
        # 建立物流物件
        if self.MerchantID and self.HashKey and self.HashIV:
            logistics = self._ecpay_get_sdk()
            # 捉取B2C 測標參數物流商的CODE 送進 SDK 中的create_test_data方法
            for rec in self.delivery_b2c_test:
                data = logistics.create_test_data(rec.logistics_code)
                url = logistics.get_logistic_url(self.prod_environment, 'CreateTestData')
                response = logistics.send_process_data(data, url)
                if response['RtnCode'] == 1 and response['RtnMsg'] == '成功':
                    self.env['shipping.ecpay.model'].create(response)
                # 在這裡處理回應數據

    def ecpay_create_temp_order(self, order):
        """
        2023 0531 全方位物流 流程
        1、網頁前端選擇物流方式 ECPAY全方位物流會進到此方法
        2、先判斷是否有暫存訂單編號，若有則更新，若無則新增
        3、送出 或更新 暫存訂單 至 ECPAY
        4、回傳 ECPAY Selection Form HTML to 前端
        """
        if not self.MerchantID or not self.HashKey or not self.HashIV:
            raise UserError('請先設定 ECPay 的後台設定值')
        # 取得 domain
        base_url = self.ecpay_domain if self.ecpay_domain else self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url')
        ServerReplyURL = urls.url_join(base_url, WebsiteSaleDeliveryECPay._ServerReplyURL)
        ClientReplyURL = urls.url_join(base_url, WebsiteSaleDeliveryECPay._ClientReplyURL) + f'?so={order.id}'
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
        #  建立物流物件
        logistics = self._ecpay_get_sdk()
        ecpay_shipping_id = self.env['shipping.ecpay.model'].search([
            ('ReferenceNo', '=', order.name)
        ], limit=1)

        temp_data = logistics.create_logistic_temp_data(order, company, ServerReplyURL, ClientReplyURL)  # 送出暫存訂單
        if ecpay_shipping_id and ecpay_shipping_id.TempLogisticsID:
            temp_data.update({
                'TempLogisticsID': ecpay_shipping_id.TempLogisticsID,
            })
            ecpay_shipping_id.delivery_id = self.id,  # 把 ecpay_shipping_id.delivery_id 設定為當前的delivery_id

        url = logistics.get_logistic_url(self.prod_environment, 'RedirectToLogisticsSelection')
        response = logistics.send_temp_process_data(
            logistics.encode_data_to_url(temp_data),
            url
        )
        return response

    '''
    依照 Odoo 物流規則，加入下列的 method
       1. <my_provider>_rate_shipment
       2. <my_provider>_send_shipping
       3. <my_provider>_get_tracking_link
       4. <my_provider>_cancel_shipment
    '''

    def ecpay_rate_shipment(self, order):
        """
        2023 0531 全方位物流 流程
        1、網頁前端選擇物流方式 ECPAY全方位物流會進到此方法
        2、先判斷是否有暫存訂單編號，若有則更新，若無則新增
        3、送出 或更新 暫存訂單 至 ECPAY
        4、返回 ECPAY 暫存訂單編號、物流方式、物流子類型，寫入shiping.ecpay.model
        5、參考後台ECPAY 全方位物流的 物流商費用 返回前端頁面
        """
        if not self.MerchantID or not self.HashKey or not self.HashIV:
            raise UserError('請先設定 ECPay 的後台設定值')

        # 取得公司設定記錄
        if self.env.context.get('company_id'):
            company = self.env['res.company'].browse(
                self.env.context['company_id'])
        else:
            company = self.env.user.company_id

        # 如果沒有填入寄件人資料
        if not (company.SenderName and
                company.SenderName and
                company.SenderZipCode and
                company.SenderAddress):
            raise ValidationError('請在"設定"的"公司"中填寫完整的寄件人資料')
        # 設定運費為0初始化，在搜尋order的 ecapy_Logistics_id.LogisticsSubType 類型 的運費
        shipping_price = 0
        ecpay_logistic_price = self.env['delivery.ecpay.price'].search(
            [('code', '=', order.ecpay_Logistics_id.LogisticsSubType)])
        for carrier in self:
            shipping_price = ecpay_logistic_price.price or carrier.product_id.standard_price

        return {
            'success': True,
            'price': shipping_price,
            'error_message': False,
            'warning_message': False
        }

    def ecpay_send_shipping(self, pickings):
        res = []
        logistics = self._ecpay_get_sdk()
        ecpay_shipping = self.env['shipping.ecpay.model']
        for picking in pickings:
            if not picking.logistic_ecpay_id:
                raise ValidationError(f'請先轉物流暫存訂單轉為正式訂單，才可進行驗證出貨')
            # sale_order = self.env['sale.order'].search(
            #     [('name', '=', picking.origin)], limit=1)
            ecpay_shipping = ecpay_shipping.search(
                [('id', '=', picking.logistic_ecpay_id.id)], limit=1)
            tracking_data = logistics.track_trade_info(ecpay_shipping.LogisticsID, ecpay_shipping.MerchantTradeNo)
            url = logistics.get_logistic_url(self.prod_environment, 'QueryLogisticsTradeInfo')
            response = logistics.send_process_data(
                tracking_data,
                url
            )
            if response['RtnCode'] == 1 and response['RtnMsg'] == '成功':
                ecpay_shipping.HandlingCharge = response['HandlingCharge']
                ecpay_shipping.ShipmentNo = response['ShipmentNo']
                ecpay_shipping.TradeDate = response['TradeDate']

            shipping_data = {
                'exact_price': 0,
                'tracking_number': response['ShipmentNo'],
            }
            res = res + [shipping_data]
        return res

    def ecpay_get_tracking_link(self, pickings):
        return self.get_ecpay_urls(self.prod_environment)['ECPAY_BACKEND']

    @api.model
    def get_ecpay_urls(self, environment):
        if environment is True:
            return ECPayURL
        else:
            return ECPayTestURL

    def ecpay_cancel_shipment(self, picking):
        raise ValidationError('目前尚未支援取消綠界物流訂單！')

    @api.constrains('ecpay_type')
    def _constrains_ecpay_type(self):
        if not self.ecpay_type:
            raise ValidationError("會員種類不得空白!")

        return True

    @api.onchange('ecpay_type')
    def _onchange_ecpay_type(self):
        if not self.prod_environment:
            if self.ecpay_type == 'b2c':
                self.MerchantID = '2000132'
                self.HashKey = '5294y06JbISpM5x9'
                self.HashIV = 'v77hoKGq4kWxNNIS'
            elif self.ecpay_type == 'c2c':
                self.MerchantID = '2000933'
                self.HashKey = 'XBERn1YOvpM9nfZc'
                self.HashIV = 'h1ONHk4P4yqbl5LK'

    #   對應 contorllers/main.py 中的路由 /shipping/get_delivery_method_name
    def get_delivery_method_name(self, post_id=0):
        # 取得
        method_name, service = '', ''
        if post_id:
            record = self.search([('id', '=', post_id)])
            if any(record):
                for field_name in ['ecpay_unimart', 'ecpay_fami', 'ecpay_hilife', 'ecpay_tcat', 'ecpay_ecan']:
                    if record[field_name]:
                        method_name = field_name
                        break
                service = record.delivery_type
        # 取得選項文字
        # method_name = '' if not method_name else self.fields_get([method_name], ['string'])[method_name]['string']
        return {
            'service': service,
            'method': method_name
        }


class StockPickingEcpay(models.Model):
    _inherit = 'stock.picking'

    LogisticsSubType = fields.Char(
        '物流子類型', groups='base.group_user', help='物流子類型',
        compute='_logistics_sub_type', readonly=True)
