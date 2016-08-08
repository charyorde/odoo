# -*- coding: utf-8 -*-
{
    'name': "statics",

    'summary': """
        Serving all Greenwood Static files
    """,

    'description': """
    Serving static files
    """,

    'author': "Greenwood",
    'website': "https://www.greenwood.ng",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Techinical Settings',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['web'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'templates.xml',
    ],
}
