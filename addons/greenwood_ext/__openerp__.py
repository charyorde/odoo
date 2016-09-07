# -*- coding: utf-8 -*-
{
    'name': "greenwood_ext",

    'summary': """
        Greenwood Extension""",

    'description': """
        Greenwood backend extension
    """,

    'author': "Greenwood",
    'website': "https://www.greenwood.ng",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Hidden',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['website_sale'],

    # always loaded
    'data': [
        #'views/res_partner.xml',
        #'views/views.xml',
        'views/templates.xml',
        'views/product_view.xml',
        'views/res_partner.xml',
    ],
    # only loaded in demonstration mode
    'qweb':[
        'static/src/xml/*.xml'
    ],
    'installable': True,
    'application': True,
}
