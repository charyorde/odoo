# -*- coding: utf-8 -*-
{
    'name': "mobileservices",

    'summary': """
        REST APIs that exposes core Greenwood functionalities for mobile
    integration
    """,

    'description': """
        Web service integration for mobile
    """,

    'author': "Greenwood",
    'website': "https://www.greenwood.ng",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Technical Settings',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'website_sale'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'templates.xml',
    ],
}
