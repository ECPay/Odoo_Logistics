# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
from werkzeug import urls
from odoo.http import request
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.logistic_ecpay.controllers.main import WebsiteSaleDeliveryEcpay
from odoo.addons.logistic_ecpay.controllers.ecpay_logistic_sdk import ECPayLogisticSdk, ECPayURL, ECPayTestURL

_logger = logging.getLogger(__name__)


class LogisticEcpay(models.Model):
    ''' A Shipping Provider

    In order to add your own external provider, follow these steps:

    1. Create your model MyProvider that _inherit 'delivery.carrier'
    2. Extend the selection of the field "delivery_type" with a pair
       ('<my_provider>', 'My Provider')
    '''
    _inherit = 'delivery.carrier'
    delivery_type = fields.Selection(selection_add=[('ecpay', 'ECPay')])

    MerchantID = fields.Char(
        '特店編號',
        required_if_provider='ecpay',
        groups='base.group_user',
        help='特店編號')
    HashKey = fields.Char(
        '介接 HashKey', groups='base.group_user', required_if_provider='ecpay')
    HashIV = fields.Char(
        '介接 HashIV', groups='base.group_user', required_if_provider='ecpay')

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
        selection=[('b2c', 'B2C'), ('c2c', 'C2C'),],
        string='會員種類')

    ecpay_cod = fields.Boolean(
        '超商到店取貨付款', default=True, help='超商到店取貨付款', groups='base.group_user')

    '''
    依照 Odoo 物流規則，加入下列的 method
       1. <my_provider>_rate_shipment
       2. <my_provider>_send_shipping
       3. <my_provider>_get_tracking_link
       4. <my_provider>_cancel_shipment
    '''

    def ecpay_rate_shipment(self, order):
        """
        計算物流費用
        """
        # 先將物流資料從 session 中取出
        shipping_info = request.session.get('shipping_info')
        shipping_price = 0
        shipping_address = ''
        reference_no = ''
        shipping_type = ''
        # 取出 ecpay 的後台設定值
        ecpay_setting = self.env['delivery.carrier'].search(
            [('delivery_type', '=', 'ecpay')], limit=1)

        if shipping_info:
            # 從物流資料取出物流類型來計算運費
            shipping_type = shipping_info.get('shipping_type')
            if shipping_type == 'UNIMART':
                shipping_price = int(ecpay_setting.ecpay_unimart_price)
                logistics_type = 'CVS'
            elif shipping_type == 'FAMI':
                shipping_price = int(ecpay_setting.ecpay_fami_price)
                logistics_type = 'CVS'
            elif shipping_type == 'HILIFE':
                shipping_price = int(ecpay_setting.ecpay_hilife_price)
                logistics_type = 'CVS'
            elif shipping_type == 'TCAT':
                shipping_price = int(ecpay_setting.ecpay_tcat_price)
                logistics_type = 'Home'
            elif shipping_type == 'ECAN':
                shipping_price = int(ecpay_setting.ecpay_ecan_price)
                logistics_type = 'Home'
            # 從物流資料取出"郵遞區號"+"縣市"+"區域"+"街道"來組合地址
            shipping_address = shipping_info['zipcode'] + shipping_info['county'] + \
                shipping_info['district'] + shipping_info['ReceiverAddress']

        if order:
            reference_no = order.name
            amount_total = order.amount_total

        if ecpay_setting.ecpay_type == 'c2c':
            if shipping_type == 'UNIMART' or \
            shipping_type == 'FAMI' or \
            shipping_type == 'HILIFE':
                shipping_type = shipping_type + 'C2C'

        params = {
            'ReferenceNo': reference_no,
            'LogisticsType': logistics_type,
            'LogisticsSubType': shipping_type,
            'GoodsAmount': int(amount_total + shipping_price),
            'ReceiverName': shipping_info.get('ReceiverName'),
            'ReceiverCellPhone': shipping_info.get('ReceiverCellPhone'),
            'ReceiverZipCode': shipping_info['zipcode'],
            'ReceiverAddress': shipping_address,
            'CVSStoreID': shipping_info.get('CVSStoreID'),
            'CVSStoreName': shipping_info.get('CVSStoreName'),
        }

        # 先建立一筆物流資料在資料庫
        self.env['shipping.ecpay.model'].sudo().shipping_ecpay_model_record(
            params)

        return {
            'success': True,
            'price': shipping_price,
            'error_message': False,
            'warning_message': False
        }

    @api.model
    def get_ecpay_urls(self, environment):
        if environment is True:
            return ECPayURL
        else:
            return ECPayTestURL

    @api.multi
    def ecpay_get_form_action_url(self):
        return self.get_ecpay_urls(self.prod_environment)['SHIPPING_ORDER']

    @api.model
    def _ecpay_get_sdk(self):
        # 取得 ECPay 的後台設定值
        return ECPayLogisticSdk(
            MerchantID=self.MerchantID,
            HashKey=self.HashKey,
            HashIV=self.HashIV)

    def ecpay_send_shipping(self, pickings):
        res = []
        shipping_data = {
            'exact_price': 0,
            'tracking_number': False,
        }
        res = res + [shipping_data]

        picking_setting = 0
        reference_no = ''
        sale_order = 0
        for picking in pickings:
            sale_order = self.env['sale.order'].search(
                [('name', '=', picking.origin)], limit=1)
            ecpay_shipping = self.env['shipping.ecpay.model'].search(
                [('ReferenceNo', '=', sale_order.id)], limit=1)
            picking_setting = picking
            break
        reference_no = picking_setting.origin

        # 取得 ECPay 的 SDK
        ecpay_logistic_sdk = self._ecpay_get_sdk()

        # 取得 domain
        base_url = self.ecpay_domain if self.ecpay_domain else self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url')

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

        create_shipping_order_params = {
            'MerchantTradeDate': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            'LogisticsType': ecpay_shipping.LogisticsType,
            'LogisticsSubType': ecpay_shipping.LogisticsSubType,
            'GoodsName': '商品一批',
            'GoodsAmount': ecpay_shipping.GoodsAmount,
            'SenderName': company.SenderName,
            'SenderPhone': company.SenderPhone,
            'SenderCellPhone': company.SenderCellPhone,
            'ReceiverName': ecpay_shipping.ReceiverName,
            'ReceiverCellPhone': ecpay_shipping.ReceiverCellPhone,
            'TradeDesc': 'ecpay_module_odoo11',
            'ServerReplyURL': urls.url_join(base_url, WebsiteSaleDeliveryEcpay._ServerReplyURL),
            'LogisticsC2CReplyURL': urls.url_join(base_url, WebsiteSaleDeliveryEcpay._ServerReplyURL),
        }

        # 如果是超商, 組合相關參數
        if ecpay_shipping.LogisticsType.lower() == 'cvs':
            shipping_cvs_params = {
                'ReceiverStoreID': ecpay_shipping.CVSStoreID,
                'ReturnStoreID': ecpay_shipping.CVSStoreID,
            }
            create_shipping_order_params.update(shipping_cvs_params)
            # 取得交易資訊
            payment_transaction = self.env['payment.transaction'].search(
                [('reference', '=', reference_no)], limit=1)
            # 檢查是否為到店取貨付款
            if 'ecpay' in payment_transaction.acquirer_id.name.lower() and \
            payment_transaction.acquirer_id.provider == 'transfer':
                create_shipping_order_params.update({'IsCollection': 'Y'})

        # 如果是宅配, 組合相關參數
        elif ecpay_shipping.LogisticsType.lower() == 'home':
            ScheduledDeliveryTime = ''
            ScheduledDeliveryDate = ''
            if ecpay_shipping.LogisticsSubType.lower() == 'tcat':
                ScheduledDeliveryTime = picking_setting.ScheduledDeliveryTimeTcat
            # 當子物流選擇宅配通時
            elif ecpay_shipping.LogisticsSubType.lower() == 'ecan':
                ScheduledDeliveryTime = picking_setting.ScheduledDeliveryTimeEcan
                # 當子物流選擇宅配通時，此參數才有作用
                if picking_setting.ScheduledDeliveryDateEcan:
                    ScheduledDeliveryDate = datetime.strptime(
                        picking_setting.ScheduledDeliveryDateEcan, DEFAULT_SERVER_DATE_FORMAT
                    ).strftime('%Y/%m/%d')
                    print(ScheduledDeliveryDate)

            shipping_home_params = {
                'SenderZipCode': company.SenderZipCode,
                'SenderAddress': company.SenderAddress,
                'ReceiverZipCode': ecpay_shipping.ReceiverZipCode,
                'ReceiverAddress': ecpay_shipping.ReceiverAddress,
                'Temperature': picking_setting.Temperature,
                'Distance': '00',
                'Specification': picking_setting.Specification,
                'ScheduledPickupTime': '4',
                'ScheduledDeliveryTime': ScheduledDeliveryTime,
                'ScheduledDeliveryDate': ScheduledDeliveryDate,
                'PackageCount': '',
            }
            create_shipping_order_params.update(shipping_home_params)

        #raise ValidationError(pprint.pformat(create_shipping_order_params))
        action_url = self.ecpay_get_form_action_url()
        # 建立物流訂單並接收回應訊息
        reply_result = ecpay_logistic_sdk.create_shipping_order(
            action_url=action_url,
            client_parameters=create_shipping_order_params)

        # 如果抓不到 CheckMacValue, 跳出錯誤訊息
        if not reply_result.get('CheckMacValue'):
            raise ValidationError(reply_result.get('error'))

        # 更新紀錄到綠界訂單
        reply_result.pop('CheckMacValue')
        reply_result.pop('MerchantID')
        reply_result.pop('ReceiverEmail')
        reply_result.pop('ReceiverPhone')
        ecpay_shipping.update(reply_result)
        ecpay_shipping.update({
            'name': reply_result.get('MerchantTradeNo'),
        })
        sale_order.update({'ecpay_Logistics_id': ecpay_shipping.id})

        shipping_data.update({
            'tracking_number': reply_result.get('AllPayLogisticsID'),
        })

        return res

    def ecpay_get_tracking_link(self, pickings):
        return self.get_ecpay_urls(self.prod_environment)['ECPAY_BACKEND']

    def ecpay_cancel_shipment(self, picking):
        raise ValidationError('目前尚未支援取消綠界物流訂單！')

    @api.constrains('ecpay_type')
    def _constrains_ecpay_type(self):
        if not self.ecpay_type:
            raise ValidationError("會員種類不得空白!")
            return False

        return True

    def create_test_data(self):
        # 取得 ECPay 的 SDK
        ecpay_logistic_sdk = self._ecpay_get_sdk()

        # 準備測試的參數
        create_test_data_params = {
            'LogisticsSubType': self.env.context.get('cvs'),
            'PlatformID': '',
        }
        action_url = self.get_ecpay_urls(self.prod_environment)['CREATE_TEST_DATA']
        # 建立物流訂單並接收回應訊息
        reply_result = ecpay_logistic_sdk.create_test_data(
            action_url=action_url,
            client_parameters=create_test_data_params)
        # 如果抓不到 CheckMacValue, 跳出錯誤訊息
        if not reply_result.get('CheckMacValue'):
            raise ValidationError(reply_result.get('error'))

        # 更新紀錄到綠界訂單
        reply_result.pop('CheckMacValue')
        reply_result.pop('MerchantID')
        reply_result.pop('ReceiverEmail')
        reply_result.pop('ReceiverPhone')
        shipping_ecpay_model = self.env['shipping.ecpay.model'].create(reply_result)
        return {
            'name': ('超商 B2C 一段標測試標籤訂單'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'shipping.ecpay.model',
            'res_id': shipping_ecpay_model.id,
            'type': 'ir.actions.act_window',
            'target':'current',
            'flags': {'form': {'action_buttons': False, 'options': {'mode': 'view'},}} 
        }

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

    @api.onchange('ecpay_unimart', 'ecpay_fami', 'ecpay_hilife', 'ecpay_cod')
    def _onchange_store(self):
        if not (self.ecpay_unimart or self.ecpay_fami or self.ecpay_hilife):
            self.ecpay_cod = False
        ecpay_cod_record = self.env.ref('logistic_ecpay.logistic_ecpay_cod')
        # 如果 ecpay_cod 為 False 而且有 ecpay_code 的 record
        if (not self.ecpay_cod) and ecpay_cod_record:
            ecpay_cod_record.write({'website_published': False})
        elif self.ecpay_cod and ecpay_cod_record:
            ecpay_cod_record.write({'website_published': True})

class StockPickingEcpay(models.Model):
    _inherit = 'stock.picking'

    LogisticsSubType = fields.Char(
        '物流子類型', groups='base.group_user', help='物流子類型',
        compute='_logistics_sub_type', readonly=True)

    Temperature = fields.Selection(
        selection=[('0001', '常溫'), ('0002', '冷藏'), ('0003', '冷凍')],
        string='溫層', default='0001', required=True)

    Specification = fields.Selection(
        selection=[('0001', '60cm'), ('0002', '90cm'), ('0003', '120cm'), ('0004', '150cm')],
        string='規格', default='0001', required=True)

    ScheduledDeliveryTimeTcat = fields.Selection(
        selection=[('1', '13前'), ('2', '14~18'), ('3', '14~18'), ('4', '不限時'),],
        string='預定送達時段', default='4', required=True)

    ScheduledDeliveryTimeEcan = fields.Selection(
        selection=[('12', '13前'), ('13', '13前'), ('23', '14~18'), ('4', '不限時'),],
        string='預定送達時段', default='4', required=True)

    ScheduledDeliveryDateEcan = fields.Date(string='指定送達日')

    @api.multi
    def _logistics_sub_type(self):
        for record in self:
            sale_order = self.env['sale.order'].search(
                [('name', '=', record.origin)], limit=1)
            ecpay_shipping = self.env['shipping.ecpay.model'].search(
                    [('ReferenceNo', '=', sale_order.id)], limit=1)
            record.LogisticsSubType = ecpay_shipping.LogisticsSubType
            print('_logistics_sub_type')

    @api.constrains('ScheduledDeliveryDateEcan')
    def _constrains_ScheduledDeliveryDateEcan(self):
        if self.ScheduledDeliveryDateEcan and datetime.strptime(
            self.ScheduledDeliveryDateEcan, DEFAULT_SERVER_DATE_FORMAT
            ).date() < (datetime.now().date() + timedelta(days=3)):
            raise ValidationError("指定送達日限制寄送日 D + 3 天 !!!")
            return False
        print('_constrains_ScheduledDeliveryDateEcan')
        return True

    @api.constrains('Temperature')
    def _constrains_Temperature(self):
        if self.LogisticsSubType and \
        self.LogisticsSubType.lower() == 'ecan' and \
        self.Temperature != '0001':
            raise ValidationError("宅配通溫層只能選擇【常溫】 !!!")
            return False
        print('_constrains_Temperature')
        return True

    @api.constrains('Specification')
    def _constrains_Specification(self):
        if self.Temperature == '0003' and \
        self.Specification == '0004':
            raise ValidationError("溫層選擇【冷凍】時，規格不包含【150cm】選項 !!!")
            return False
        print('_constrains_Specification')
        return True