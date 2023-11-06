# -*- coding: utf-8 -*-

{
    'name': 'ECPay 綠界第三方物流模組',
    'category': 'Stock',
    'summary': '物流 (Logistic): ECPay 綠界第三方物流模組',
    'version': '16.0.1.0',
    'author': 'ECPAY',
    'website': 'http://www.ecpay.com.tw',
    'description': """ECPay 綠界物流模組""",
    'depends': ['delivery', 'website_sale_delivery', 'mail', 'payment_ecpay'],
    'data': [
        'security/logistic_ecpay_access_rule.xml',
        'security/ir.model.access.csv',
        'data/logistic_ecpay_data.xml',
        'data/delivery_b2c_test_data.xml',
        'data/delivery_price_data.xml',
        'views/res_company.xml',
        'views/logistic_ecpay_templates.xml',
        'views/logistic_ecpay_view.xml',
        'views/delivery_b2c_test.xml',
        'views/delivery_ecpay_price.xml',
        'views/stock_picking.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'logistic_ecpay/static/src/js/ecpay_select_check.js',
        ],
        'web.assets_backend': [
            'logistic_ecpay/static/src/widgets/**/*',
        ],
    },

    'installable': True,
    'application': True,
    'auto_install': False,
}
