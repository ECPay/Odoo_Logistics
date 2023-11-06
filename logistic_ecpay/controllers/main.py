# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
import logging
from datetime import datetime

from odoo import http, _
from odoo.addons.website_sale_delivery.controllers.main import WebsiteSaleDelivery
from odoo.exceptions import MissingError
from odoo.http import request, Controller
from datetime import timedelta, datetime
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

WITHOUT_JSONRPC_ROUTES = [
    '/logistic/ecpay/server_reply_url',
]


class WebsiteSaleDeliveryECPay(WebsiteSaleDelivery):
    CVSStoreID = ""
    CVSStoreName = ""
    CVSAddress = ""
    CVSTelephone = ""
    ecpay_logistic_sdk = 0

    _ServerReplyURL = '/logistic/ecpay/server_reply_url'
    # 開啟物流選擇頁面 ECPay 回傳的網址會用 ClientReplyURL參數
    _ClientReplyURL = '/logistics/reply'

    @http.route('/logistic/ecpay/server_reply_url', type='json', methods=['POST'], auth="public", website=True)
    def server_reply_url(self, **kwargs):
        """
        物流狀態通知
        每當物流狀態有變更時，綠界科技皆會傳送物流狀態至合作特店。
        1.綠界科技：以 ServerPost 方式傳送物流狀態至合作特店設定的(ServerReplyURL) 網址
        2.合作特店：收到綠界科技的物流狀態，並判斷檢查碼是否相符
        3.合作特店：檢查碼相符後，在網頁端回應 1|OK
        """
        request_data: dict = json.loads(request.httprequest.data)
        data: str = request_data.get('Data')
        # if request_data.get('RtnCode') == 1 and request_data.get('RtnMsg') == '成功':
        #     return '1|OK'
        # else:
        #     return '0|error'

        logistics = request.env['delivery.carrier'].sudo().search([
            ('delivery_type', '=', 'ecpay')
        ], limit=1)._ecpay_get_sdk()
        shipping_model = request.env['shipping.ecpay.model']

        default_return_data: dict = {
            'RtnCode': 0,
            'RtnMsg': '失敗',
        }
        try:
            return_data = {**default_return_data}
            if request_data.get('TransCode') == 1:
                decrypted_data = logistics.cbc_decrypt(self, data, logistics.HashKey, logistics.HashIV)
                result = json.loads(decrypted_data)
                trade_no, logistic_id = result.get('MerchantTradeNo'), result.get('LogisticsID')
                shipping_data = shipping_model.sudo().search([
                    ('MerchantTradeNo', '=', trade_no),
                ], limit=1)

                if shipping_data:
                    shipping_data.write({
                        'LogisticsID': logistic_id,
                        'LogisticsStatus': result.get('LogisticsStatus'),
                        'LogisticsStatusName': result.get('LogisticsStatusName'),
                        'RtnCode': result.get('RtnCode'),
                        'RtnMsg': result.get('RtnMsg'),
                        'is_convert': True,
                        'GoodsAmount': result.get('GoodsAmount') or False,
                        'UpdateStatusDate': result.get('UpdateStatusDate') or False,
                        'BookingNote': result.get('BookingNote') or False,
                        'CVSPaymentNo': result.get('CVSPaymentNo') or False,
                        'CVSValidationNo': result.get('CVSValidationNo') or False,
                    })
                    _logger.info(f'物流建立成功返回資訊: {result}')
                    body = _('物流訂單轉換完成')
                    shipping_data.message_post(body=body)
                    shipping_data.TempLogisticsID = ''

                    return_data = {
                        'RtnCode': 1,
                        'RtnMsg': '成功',
                    }
                else:
                    _logger.info(f'server_reply_url: 找不到綠界物流訂單 [data: {result}]')
        except:
            _logger.info(f'server_reply_url: 更新失敗！', exc_info=True)
            return_data = default_return_data

        return {
            'MerchantID': logistics.MerchantID,
            'RqHeader': {
                'Timestamp': str(int(datetime.now().timestamp()))
            },
            'TransCode': 1,
            'TransMsg': '',
            'Data': logistics.cbc_encrypt(
                logistics,
                plaintext=logistics.encode_data_to_url(return_data),
                key=logistics.HashKey,
                iv=logistics.HashIV,
            ),
        }

    @http.route('/logistics/reply', type='http', auth='public', csrf=False, website=True, sitemap=False,
                save_session=False)
    def logistics_reply(self, **post):
        """
        綠界會將店鋪資訊回傳到此
        """
        website = request.website.sudo()
        so = website.sale_get_order()
        if not so:
            try:
                so = so.browse(int(post.get('so')))
                _logger.info(f'Reply get so: {so.name}')  # 故意取得欄位，確保 so 是存在的
            except Exception as e:
                _logger.info(f'SO 解析失敗 [{e}]')
                return request.redirect("/shop/payment")

        ecpay_setting = request.env['delivery.carrier'].sudo().search([
            ('delivery_type', '=', 'ecpay')
        ], limit=1)

        return_temp_order = json.loads(post.get('ResultData'))
        logistics = ecpay_setting.sudo()._ecpay_get_sdk()
        if return_temp_order.get('TransCode') != 1:
            raise Exception('綠界返回暫存訂單物流失敗!!錯誤訊息： ' + str(return_temp_order.get('TransMsg')))
        decrypted_data = logistics.cbc_decrypt(self, return_temp_order.get("Data"), logistics.HashKey, logistics.HashIV)
        result = json.loads(decrypted_data)

        if result.get('RtnCode') == 1 and result.get('RtnMsg') == '成功' and so:
            ecpay_record = request.env['shipping.ecpay.model'].sudo().search([
                ('ReferenceNo', '=', so.id)
            ], limit=1)

            temp_data = {
                "MerchantID": ecpay_setting.MerchantID or result.get('MerchantID'),
                "TempLogisticsID": result.get('TempLogisticsID'),
                "LogisticsType": result.get('LogisticsType'),
                "LogisticsSubType": result.get('LogisticsSubType'),
                "ReceiverName": result.get('ReceiverName'),
                "ReceiverPhone": result.get('ReceiverPhone'),
                "ReceiverCellPhone": result.get('ReceiverCellPhone'),
                "ReceiverZipCode": result.get('ReceiverZipCode'),
                "ReceiverAddress": result.get('ReceiverAddress'),
                "CVSStoreID": result.get('ReceiverStoreID'),
                "CVSStoreName": result.get('ReceiverStoreName'),
                "ReferenceNo": so.id,
                "MerchantTradeNo": f'odooN{(datetime.now() + timedelta(hours=8)).strftime("%m%d%H%M%S")}',
            }
            # 加入 運送的方式 ID，以利後續更新或送正式訂單後台單據能夠使用，及寫入銷售訂單的綠界物流訂單
            if ecpay_record:
                temp_data['delivery_id'] = ecpay_record.delivery_id.id or so.carrier_id.id
                if so.carrier_id.IsCollection == True or ecpay_record.delivery_id.IsCollection == True:
                    temp_data['IsCollection'] = 'Y'
                _logger.info('===> 更新')
                ecpay_record.write(temp_data)
                so.ecpay_Logistics_id = ecpay_record.id
                # shipping_price = request.env['delivery.ecpay.price'].sudo().search(
                #     [('code', '=', result.get('LogisticsSubType'))])
                # so.amount_delivery = shipping_price.price or 0.0
            else:
                _logger.info('===> 新增')
                temp_data['delivery_id'] = so.carrier_id.id
                if so.carrier_id.IsCollection == True:
                    temp_data['IsCollection'] = 'Y'
                ecpay_temp_id = ecpay_record.create(temp_data)
                so.ecpay_Logistics_id = ecpay_temp_id.id
                # shipping_price = request.env['delivery.ecpay.price'].sudo().search(
                #     [('code', '=', result.get('LogisticsSubType'))])
                # so.amount_delivery = shipping_price.price or 0.0
        else:
            error = []
            if result.get('RtnCode') != 1:
                error.append(f'綠界回傳值不為成功: {result.get("RtnMsg")}')
            if not so:
                error.append('找不到銷售訂單')
            _logger.info(f'發生了一些問題: [{", ".join(error)}]')

        return request.redirect("/shop/payment")

    @http.route('/shipping/get_delivery_method_name', type='json', methods=['POST'], auth="public")
    def get_delivery_method_name(self, **post):
        try:
            post_id = int(post['id'])
        except TypeError:
            post_id = 0

        return request.env['delivery.carrier'].sudo().get_delivery_method_name(post_id)

    @http.route('/shipping/create_temp_order', type='json', auth='public', methods=['POST'], csrf=False)
    def create_temp_order(self, **post):
        [success, content] = [True, '']
        sale_order = request.env['sale.order'].sudo()
        delivery_carrier = request.env['delivery.carrier'].sudo()

        try:
            sale_order_id = int(post.get('sale_order_id'))
            sale_order = sale_order.browse(sale_order_id)
            sale_order.name_get()

            delivery_carrier_id = int(post.get('delivery_carrier_id'))
            delivery_carrier = delivery_carrier.browse(delivery_carrier_id)
            delivery_carrier.name_get()
        except MissingError:
            success = False
            content = '找不到相關單據，請重新整理畫面後再嘗試'
        except TypeError as e:
            success = False
            content = f'參數傳入錯誤 [{e}]'
        except ValueError as e:
            success = False
            content = f'無法被轉換的錯誤 [{e}]'

        if success:
            content = delivery_carrier.ecpay_create_temp_order(sale_order)
        #  Return ECPAY Selection Form to Frontend

        return {
            'success': success,
            'content': content,
        }

    @http.route()
    def shop_payment(self, **post):
        response = super().shop_payment(**post)

        qcontext = response.qcontext
        so = qcontext.get('website_sale_order')
        if so:
            logistic = request.env['shipping.ecpay.model'].sudo().search([('ReferenceNo', '=', so.id)], limit=1)
            if logistic:
                qcontext.update({
                    'store_name': logistic.website_name_get(),
                })
            keep_carrier = post.get('keep_carrier', False)
            carrier_id = post.get('carrier_id') or so.carrier_id.id or False
            so._check_carrier_quotation(force_carrier_id=carrier_id, keep_carrier=keep_carrier)

        return response


class Main(Controller):
    @http.route(
        route='/web/logistic/print_csv_shipping/<int:record_id>',
        type='http', methods=['GET'], auth="user", website=True
    )
    def print_csv_shipping(self, record_id=None):
        allow_groups = ('base.group_user', 'logistic_ecpay.group_user')
        denied = not all(request.env.user.has_group(g) for g in allow_groups)
        if denied or not record_id:
            return '不存在的紀錄'

        try:
            record = request.env['shipping.ecpay.model'].browse(record_id)
            record.name  # 取得任一欄位來確認是否為不存在的資料
        except MissingError:
            return '不存在的紀錄'

        return record.print_logistic_order()

    # @http.route(['/shop/carrier_rate_shipment'], type='json', auth='public', methods=['POST'], website=True)
    # def cart_carrier_rate_shipment(self, carrier_id, **kw):
    #     order = request.website.sale_get_order(force_create=True)
    #
    #     if not int(carrier_id) in order._get_delivery_methods().ids:
    #         raise UserError(
    #             _('It seems that a delivery method is not compatible with your address. Please refresh the page and try again.'))
    #
    #     Monetary = request.env['ir.qweb.field.monetary']
    #
    #     res = {'carrier_id': carrier_id}
    #     carrier = request.env['delivery.carrier'].sudo().browse(int(carrier_id))
    #     rate = WebsiteSaleDelivery._get_rate(carrier, order)
    #     if rate.get('success'):
    #         res['status'] = True
    #         res['new_amount_delivery'] = Monetary.value_to_html(rate['price'], {'display_currency': order.currency_id})
    #         res['is_free_delivery'] = not bool(rate['price'])
    #         res['error_message'] = rate['warning_message']
    #         order.amount_delivery = rate['price']
    #     else:
    #         res['status'] = False
    #         res['new_amount_delivery'] = Monetary.value_to_html(0.0, {'display_currency': order.currency_id})
    #         res['error_message'] = rate['error_message']
    #     return res
