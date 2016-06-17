# -*- coding: utf-8 -*-
{
    'name': "payment_greenpay",

    'summary': """
    Payment Acquirer: Greenpay""",

    'description': """
        Greenpay Payment Acquirer
    """,

    'author': "Greenwood inc.",
    'website': "http://www.greenwood.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Accounting &amp; Finance',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['payment'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'data/greenpay.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
}
