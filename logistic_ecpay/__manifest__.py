# -*- coding: utf-8 -*-

{
    'name': 'ECPay 綠界第三方物流模組',
    'category': 'Stock',
    'summary': '物流 (Logistic): ECPay 綠界第三方物流模組',
    'version': '1.6',
    'description': """ECPay 綠界物流模組""",
    'author' : '元植顧問',
    'website' : 'https://www.yuanchih-consult.com/',
    'depends': ['delivery', 'mail'],
    'data': [
        'security/logistic_ecpay_access_rule.xml',
        'security/ir.model.access.csv',
        'data/logistic_ecpay_data.xml',
        'views/logistic_ecpay_templates.xml',
        'views/logistic_ecpay_view.xml',
    ],
    'qweb': [
        'static/src/xml/print_cvs_template.xml',
    ],
    'installable': True,
    'auto_install': False,
}
