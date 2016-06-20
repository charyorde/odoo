# -*- coding: utf-8 -*-
{
    'name': "website_greenwood",

    'summary': """
        Alteration of Odoo for Greenwood""",

    'description': """
        Greenwood website Backend
    """,

    'author': "Greenwood",
    'website': "http://www.greenwood.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Hidden',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['web', 'website'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'data/greenwood_account.xml',
        'views/res_partner.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
}
