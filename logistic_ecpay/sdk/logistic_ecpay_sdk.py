# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import base64
import json
import logging
import math
import time
import urllib.parse

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

_logger = logging.getLogger(__name__)

""""
物流追蹤狀態對照表
"""
ECPayTestURL = {
    'ECPAY_BACKEND': 'https://vendor-stage.ecpay.com.tw',
}
ECPayURL = {
    'ECPAY_BACKEND': 'https://vendor.ecpay.com.tw',
}
"""
物流類型名稱對照表
"""
LogisticsNameMap = {
    'CVS': '超商取貨',
    'HOME': '宅配',
    'FAMI': '全家物流(B2C)',
    'UNIMART': '7-ELEVEN超商物流(B2C)',
    'UNIMARTFREEZE': '7-ELEVEN冷凍店取(B2C)',
    'FAMIC2C': '全家物流(C2C)',
    'UNIMARTC2C': '7-ELEVEN超商物流(C2C)',
    'HILIFE': '萊爾富物流(B2C)',
    'HILIFEC2C': '萊爾富物流(C2C)',
    'OKMARTC2C': 'OK超商(C2C)',
    'TCAT': '黑貓物流',
    'POST': '中華郵政',
}


class ECPayLogistics(object):
    def __init__(self, MerchantID, HashKey, HashIV):
        self.MerchantID = MerchantID
        self.HashKey = HashKey
        self.HashIV = HashIV

    @staticmethod
    def cbc_encrypt(self, plaintext, key, iv):
        """
        AES-CBC 加密
        key 必須是 16(AES-128)、24(AES-192) 或 32(AES-256) 位元組的 AES 金鑰；
        初始化向量 iv 為隨機的 16 位字串 (必須是16位)，
        解密需要用到這個相同的 iv，因此將它包含在密文的開頭。
        """
        url_encoded_padded = pad(plaintext.encode(), AES.block_size)
        cipher = AES.new(bytes(key, 'utf-8'), AES.MODE_CBC, bytes(iv, 'utf-8'))
        _logger.info(f'random IV : {base64.b64encode(cipher.iv).decode("utf-8")}')
        data_check = cipher.encrypt(url_encoded_padded)
        data_base64_encoded = base64.b64encode(data_check).decode()
        return data_base64_encoded

    @staticmethod
    def cbc_decrypt(self, ciphertext, key, iv):
        # 對data進行AES解密
        decrypt_cipher = AES.new(bytes(key, 'utf-8'), AES.MODE_CBC, bytes(iv, 'utf-8'))
        base64_decoded = base64.b64decode(ciphertext)
        decrypted = decrypt_cipher.decrypt(base64_decoded)
        # 對解密後的數據進行解填充
        decrypted_unpadded = unpad(decrypted, AES.block_size)
        # 對解填充後的數據進行urldecode
        url_decoded = urllib.parse.unquote(decrypted_unpadded.decode())
        # 輸出解密後的數據
        _logger.info(url_decoded)
        return url_decoded

    # 用來 B2C 測標的方法
    def create_test_data(self, LogisticsSubType):
        data = {
            'MerchantID': self.MerchantID,
            'LogisticsSubType': LogisticsSubType
        }
        data_json = json.dumps(data)
        data_encoded = urllib.parse.quote(data_json)  # URL Encode before encryption
        return data_encoded

    def track_trade_info(self, LogisticsID=None, MerchantTradeNo=None):
        if not (LogisticsID and MerchantTradeNo):
            raise Exception('無定義 "綠界訂單編號" 或 "廠商交易編號"')

        data = {
            'MerchantID': self.MerchantID,
            **({'LogisticsID': LogisticsID} if LogisticsID else {}),
            **({'MerchantTradeNo': MerchantTradeNo} if not LogisticsID and MerchantTradeNo else {}),
        }

        data_json = json.dumps(data)
        data_encoded = urllib.parse.quote(data_json)  # URL Encode before encryption
        return data_encoded

    # 用來更新暫存訂單(後台)
    def update_logistic_temp_order(self, temp, company=None, server_reply_url=None):
        data = {
            'TempLogisticsID': temp.TempLogisticsID,
            'GoodsAmount': int(temp.ReferenceNo.amount_total),
            'GoodsName': '商品一批',
            'SenderName': company.SenderName,
            'SenderZipCode': company.SenderZipCode,
            'SenderAddress': company.SenderAddress,
            'Remark': temp.ReferenceNo.name,  # 備註 (訂單編號)
            'ServerReplyURL': server_reply_url,
            # 'Specification':
            'ReceiverAddress': temp.ReceiverAddress or temp.ReferenceNo.partner_id.street,
            'ReceiverZipCode': temp.ReceiverZipCode or '',
            'ReceiverCellPhone': temp.ReceiverCellPhone or '',
            'ReceiverPhone': temp.ReferenceNo.partner_id.phone or temp.ReceiverCellPhone,
            'ReceiverName': temp.ReceiverName,
        }
        data_json = json.dumps(data)
        data_encoded = urllib.parse.quote(data_json)  # URL Encode before encryption
        return data_encoded

    def query_shipping_info(self, temp):
        data = {
            'MerchantID': self.MerchantID,
            **({'LogisticsID': temp.LogisticsID} if temp.LogisticsID else {}),
            **({'MerchantTradeNo': temp.MerchantTradeNo} if not temp.LogisticsID and temp.MerchantTradeNo else {}),
        }
        data_json = json.dumps(data)
        data_encoded = urllib.parse.quote(data_json)  # URL Encode before encryption
        return data_encoded

    def convert_logistic_temp_trade(self, temp):
        data = {
            'TempLogisticsID': temp.TempLogisticsID,
            'MerchantTradeNo': temp.MerchantTradeNo,  # 後台交易訂單號
        }
        data_json = json.dumps(data)
        data_encoded = urllib.parse.quote(data_json)  # URL Encode before encryption
        return data_encoded

    @staticmethod
    def print_shipping_info(order, temp):
        data = {
            'MerchantID': order.get('MerchantID'),
            'LogisticsID': temp,
            'LogisticsSubType': order.get('LogisticsSubType'),
        }
        data_json = json.dumps(data)
        data_encoded = urllib.parse.quote(data_json)  # URL Encode before encryption
        return data_encoded

    @staticmethod
    def create_logistic_temp_data(order, company=None, server_reply_url=None, client_reply_url=None) -> dict:
        IsCollection = 'N'
        if order.carrier_id.IsCollection == True:
            IsCollection = 'Y'
        return {
            'TempLogisticsID': '0',
            'GoodsAmount': int(order.amount_total),
            'IsCollection': IsCollection,
            'GoodsName': '商品一批',
            'SenderName': company.SenderName,
            'SenderZipCode': company.SenderZipCode,
            'SenderAddress': company.SenderAddress,
            'Remark': order.name,  # 備註 (訂單編號)
            'ServerReplyURL': server_reply_url,
            'ClientReplyURL': client_reply_url,
            'ReceiverAddress': order.partner_id.street,
            'ReceiverCellPhone': order.partner_id.mobile or '',
            'ReceiverPhone': order.partner_id.phone or order.partner_id.mobile,
            'ReceiverName': ECPayLogistics.get_limit_name(order.partner_id.name),
            'EnableSelectDeliveryTime': 'Y'
        }

    @staticmethod
    def get_char_use_space(char: str) -> int:
        """ 判斷文字使用位數 """
        if len(char) > 1:
            char = char[0]

        if '\u4e00' <= char <= '\u9fff':  # 中文字碼範圍
            return 2
        elif 0x61 <= (ord(char) | 0x20) <= 0x7a:  # 英文大小寫範圍
            return 1
        else:
            return 0

    @staticmethod
    def get_limit_name(current_name: str, min_length: int = 4, max_length: int = 10) -> str:
        """ 取得純中英文字串 """
        used_space: int = 0
        new_name: str = ''
        for char in current_name:
            char_use: int = ECPayLogistics.get_char_use_space(char)

            if not char_use:
                continue

            if (used_space + char_use) > max_length:
                break

            used_space += char_use
            new_name += char

        if used_space < min_length:
            padding: int = min_length - used_space
            new_name += new_name[0] * math.ceil(padding / ECPayLogistics.get_char_use_space(new_name))

        return new_name

    @staticmethod
    def encode_data_to_url(data: dict) -> str:
        data_json = json.dumps(data)
        return urllib.parse.quote(data_json)  # URL Encode before encryption

    @staticmethod
    def get_logistic_url(env: bool = None, method: str = None) -> str:
        """ 取 API 網址 """
        allow_methods = (
            'CreateTestData',
            'RedirectToLogisticsSelection',
            'UpdateTempTrade',
            'CreateByTempTrade',
            'QueryLogisticsTradeInfo',
            'PrintTradeDocument',
        )

        if method not in allow_methods:
            raise KeyError(f'未定義的 method: {method}')

        domain = 'logistics.ecpay.com.tw' if env else 'logistics-stage.ecpay.com.tw'
        return f'https://{domain}/Express/v2/{method}'

    def _packing(self, data: str) -> str:
        encrypted_data = self.cbc_encrypt(self, data, self.HashKey, self.HashIV)
        return json.dumps({
            'MerchantID': self.MerchantID,
            'RqHeader': {
                'Timestamp': str(int(time.time())),
            },
            'Data': encrypted_data,
        })

    def send_process_data(self, data, url):
        headers = {'Content-Type': 'application/json'}
        transaction_data_array = self._packing(data)
        try:
            response = requests.post(url, transaction_data_array, headers=headers, timeout=120)
            if response.status_code != 200:
                raise Exception('HTTP status code exception: ' + str(response.status_code))
            result_data = json.loads(response.text)
            if result_data.get('TransCode') != 1 or result_data.get('TransMsg') != 'Success':
                raise Exception('串接物流失敗!!錯誤訊息： ' + str(result_data.get('TransMsg')))
            decrypted_data = self.cbc_decrypt(self, result_data.get("Data"), self.HashKey, self.HashIV)
            return json.loads(decrypted_data)
        except Exception as e:
            raise Exception('Exception: ' + str(e))

    def request_html(self, data: str, url: str) -> str:
        headers = {'Content-Type': 'application/json'}
        transaction_data_array = self._packing(data)

        try:
            response = requests.post(url, transaction_data_array, headers=headers, timeout=120)
            if response.status_code != 200:
                raise Exception('HTTP status code exception: ' + str(response.status_code))

            try:
                response_data = json.loads(response.content.decode('utf-8'))
                decrypt_data: dict = json.loads(
                    self.cbc_decrypt(self, response_data['Data'], self.HashKey, self.HashIV)
                )
                _logger.debug(f'不為 HTML 內容，請檢查錯誤訊息: {decrypt_data}')
                return decrypt_data.get('RtnMsg', '未知的問題，請聯絡系統管理員')
            except:
                return response.content.decode('utf-8')
        except Exception as e:
            raise Exception(f'Exception: {e.args[0]}')

    def send_temp_process_data(self, data, url):
        headers = {'Content-Type': 'application/json'}
        transaction_data_array = self._packing(data)

        try:
            response = requests.post(url, transaction_data_array, headers=headers, timeout=120)
            if response.status_code != 200:
                raise Exception('HTTP status code exception: ' + str(response.status_code))

            try:
                response_data = json.loads(response.text)
                decrypt_data: dict = json.loads(
                    self.cbc_decrypt(self, response_data['Data'], self.HashKey, self.HashIV)
                )
                _logger.debug(f'建立暫存訂單失敗: {decrypt_data}')
                return decrypt_data.get('RtnMsg', '未知的問題，請聯絡系統管理員')
            except:
                return json.dumps(response.text)
        except Exception as e:
            raise Exception(f'Exception: {e.args[0]}')
