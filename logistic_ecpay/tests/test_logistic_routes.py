# -*- coding:utf-8 -*-
from odoo.tests import common
from json import dumps
from datetime import datetime


class TestLogisticRoutes(common.HttpCase):
    def setUp(self):
        super().setUp()
        self.sdk = self.env['delivery.carrier'].sudo().search([
            ('delivery_type', '=', 'ecpay')
        ],limit=1)._ecpay_get_sdk()

        if not self.sdk:
            self.skipTest('無可用的綠界設定')

        self.encrypt_args: dict = {
            'key': self.sdk.HashKey,
            'iv': self.sdk.HashIV,
        }
        self.record = self.env['shipping.ecpay.model'].search([
            ('RtnCode', '=', False)
        ], limit=1)

        if not self.record:
            self.skipTest('無可用的綠界物流訂單，請先產生一張')

    def test_01_server_reply(self):
        test_logistics_id = 'test123456'
        dataset = {
            'MerchantID': self.sdk.MerchantID,
            'RqHeader': {
                'Timestamp': str(int(datetime.now().timestamp()))
            },
            'TransCode': 1,
            'TransMsg': '',
            'Data': self.sdk.cbc_encrypt(
                self,
                plaintext=self.sdk.encode_data_to_url({
                    'RtnCode': 1,
                    'RtnMsg': '成功',
                    'MerchantID': self.sdk.MerchantID,
                    'LogisticsType': self.record.LogisticsType,
                    'LogisticsSubType': self.record.LogisticsSubType,
                    'MerchantTradeNo': self.record.MerchantTradeNo,
                    'LogisticsID': test_logistics_id,
                    'LogisticsStatus': '300',
                    'LogisticsStatusName': '訂單處理中(已收到訂單資料)',
                    'GoodsAmount': 1,
                    'UpdateStatusDate': '2020/05/09 10:36:04',
                    'ReceiverName': 'Test receiver',
                    'ReceiverCellPhone': '85212345678',
                    'ReceiverEmail': 'xxx@xxx.com.tw',
                    'ReceiverAddress': 'xxxx',
                    'CVSPaymentNo': 'xxxx',
                    'CVSValidationNo': 'xxxx',
                    'BookingNote': 'xxxx'
                }),
                **self.encrypt_args,
            )
        }
        response = self.url_open(
            '/logistic/ecpay/server_reply_url',
            data=dumps(dataset),
            headers={
                'Content-Type': 'application/json; charset=utf-8'
            },
        )

        self.assertEqual(response.status_code, 200, '回應不是 200')
        self.assertEqual(self.record.LogisticsID, test_logistics_id, '物流訂單編號更新失敗')
