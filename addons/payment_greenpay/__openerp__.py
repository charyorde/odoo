# -*- coding: utf-8 -*-
{
    'name': "payment_greenpay",

    'summary': """
    Payment Acquirer: Greenpay""",

    'description': """
        Greenpay Supported Payment Acquirers
    """,

    'author': "Greenwood inc.",
    'website': "http://www.greenwood.com",

    'category': 'Accounting &amp; Finance',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['payment'],

    # always loaded
    'data': [
        'views/views.xml',
        'views/templates.xml',
        'views/interswitch.xml',
        'views/nibsscmms.xml',
        'views/paystack.xml',
        'data/interswitch.xml',
        'data/nibsscmms.xml',
        'data/interswitchauto.xml',
        'data/paystack.xml'
    ],
    'installable': True,
}
