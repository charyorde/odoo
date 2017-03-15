# -*- coding: utf-8 -*-
{
    'name': "theme_houzz",

    'summary': """
        Greenwood theme
    """,

    'description': """
        Greenwood bootstrap website theme
    """,

    'author': "Greenwood",
    'website': "http://www.greenwood.com.ng",
    'category': 'Theme/Creative',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['website', 'website_less'],

    # always loaded
    'data': [
        'views/templates.xml',
        'views/snippets.xml',
    ],
    'auto_install':False,
    'installable': True,
}
