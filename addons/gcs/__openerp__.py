# -*- coding: utf-8 -*-
{
    'name': "gcs",

    'summary': """
        Back Office integration of GreenCloud""",

    'description': """
        Back Office integration of GreenCloud
    """,

    'author': "Greenwood",
    'website': "http://gcs.greenwood.ng",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['website_sale'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'data/gcs_cron.xml',
        'templates.xml',
        'views/views.xml'
    ],
    'installable': True,
    'application': True,
}
