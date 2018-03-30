# -*- coding: utf-8 -*-
{
    'name': "cheape",

    'summary': """
        Online bargain buying engine""",

    'description': """
        Online bargain buying engine. A product of Huntrecht inc.
    """,

    'author': "Greenwood",
    'website': "http://www.greenwood.ng",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Technical Settings',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['website_sale'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/res_users_data.xml',
        'data/cheape_cron.xml',
        'templates.xml',
        'views/views.xml'
    ],
    'installable': True,
    'application': True,
}
