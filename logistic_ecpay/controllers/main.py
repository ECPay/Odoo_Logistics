# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import pprint
import logging
from werkzeug import urls
from odoo import http, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.logistic_ecpay.controllers.ecpay_logistic_sdk import ECPayLogisticSdk

_logger = logging.getLogger(__name__)


class WebsiteSaleDeliveryEcpay(http.Controller):

    CVSStoreID = ""
    CVSStoreName = ""
    CVSAddress = ""
    CVSTelephone = ""
    ecpay_logistic_sdk = 0

    _ServerReplyURL = '/logistic/ecpay/server_reply_url'

    @http.route('/logistic/ecpay/server_reply_url', type='http', methods=['POST'], auth="public", website=True, csrf=False)
    def server_reply_url(self, **post):
        """
        物流狀態通知
        每當物流狀態有變更時，綠界科技皆會傳送物流狀態至合作特店。
        1.綠界科技：以 ServerPost 方式傳送物流狀態至合作特店設定的(ServerReplyURL) 網址
        2.合作特店：收到綠界科技的物流狀態，並判斷檢查碼是否相符
        3.合作特店：檢查碼相符後，在網頁端回應 1|OK
        """
        _logger.info('綠界回傳[物流狀態通知] %s',
                     pprint.pformat(post))
        #  計算驗證 CheckMacValue 是否相符
        if request.env['shipping.ecpay.model'].sudo().ecpay_check_mac_value(post):
            # 先建立一筆物流資料在資料庫
            request.env['shipping.ecpay.model'].sudo(
            ).shipping_ecpay_model_update(post)
            return '1|OK'
        else:
            return '0|error'

    @http.route(['/logistics/reply'], type='http', auth='public', csrf=False, website=True)
    def logistics_reply(self, **post):
        """
        綠界會將店鋪資訊回傳到此 router
        """
        self.CVSStoreID = post.get('CVSStoreID')
        self.CVSStoreName = post.get('CVSStoreName')
        self.CVSAddress = post.get('CVSAddress')
        self.CVSTelephone = post.get('CVSTelephone')
        response = request.render("logistic_ecpay.map_logistic_ecpay")
        return response

    @http.route(['/shipping/update_carrier'], type='json', auth='public', methods=['POST'], website=True, csrf=False)
    def update_eshop_carrier(self, **post):
        """
        利用 ajax 將店鋪資訊回傳給前端
        """
        data = dict()
        return {
            'CVSStoreID': self.CVSStoreID,
            'CVSStoreName': self.CVSStoreName,
            'CVSAddress': self.CVSAddress,
            'CVSTelephone': self.CVSTelephone,
        }

    @http.route(['/shipping/map', '/shipping/map/<LogisticsSubType>'], type='http', auth="public", website=True, csrf=False)
    def cvs_map(self, LogisticsSubType, **post):
        # 取得 ECPay 的後台設定值
        ecpay_setting = request.env['delivery.carrier'].sudo().search(
            [('delivery_type', '=', 'ecpay')], limit=1)
        self.ecpay_logistic_sdk = ECPayLogisticSdk(
            MerchantID=ecpay_setting.MerchantID,
            HashKey=ecpay_setting.HashKey,
            HashIV=ecpay_setting.HashIV)

        if ecpay_setting.ecpay_type == 'c2c':
            LogisticsSubType = LogisticsSubType + 'C2C'

        # 取得 domain
        base_url = ecpay_setting.ecpay_domain if ecpay_setting.ecpay_domain else request.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')

        # 建立實體
        values = dict()
        parameter = {
            "MerchantTradeNo": "anyno",
            "LogisticsType": "CVS",
            "LogisticsSubType": LogisticsSubType,
            "IsCollection": "N",
            "ServerReplyURL": urls.url_join(base_url, "/logistics/reply"),
            "ExtraData": "",
            "Device": 0,
        }
        values['ecpay_url'] = request.env['shipping.ecpay.model'].sudo(
        ).get_ecpay_urls(ecpay_setting.prod_environment)['CVS_MAP']
        parameter = self.ecpay_logistic_sdk.cvs_map(parameter)
        # pprint.pprint(parameter)
        values['parameters'] = parameter
        return request.render("logistic_ecpay.ecpay_logistic_form", values)


class WebsiteSaleEcpay(WebsiteSale):

    @http.route(['/shop/confirm_order'], type='http', auth="public", website=True, csrf=False)
    def confirm_order(self, **post):
        # 將地址結果 pass 到下一階段(付款頁面)
        request.session['shipping_info'] = post
        #pprint.pprint(request.session)
        # 檢查物流是否開啟超商到店取貨付款
        if ('UNIMART' in post.get('shipping_type') or \
        'FAMI' in post.get('shipping_type') or \
        'HILIFE' in post.get('shipping_type')) and \
        (request.env.ref('logistic_ecpay.logistic_ecpay_data').sudo().ecpay_cod):
            request.env.ref('logistic_ecpay.logistic_ecpay_cod').sudo().write({'website_published': True})
        else:
            request.env.ref('logistic_ecpay.logistic_ecpay_cod').sudo().write({'website_published': False})
        return super(WebsiteSaleEcpay, self).confirm_order(**post)
