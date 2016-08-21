import openerp

import logging

_logger = logging.getLogger(__name__)


def _mobile_product_dispatch(db_name, method_name, *method_args):
    try:
        registry = openerp.modules.registry.RegistryManager.get(db_name)
        assert registry, 'Unknown database %s' % db_name
        with registry.cursor() as cr:
            product = registry['product.template']
            return getattr(product, method_name)(cr, *method_args)

    except Exception, e:
        _logger.exception('Failed to execute Mobile service method %s with args %r.',
            method_name, method_args)
        raise

def _mobile_partner_dispatch(db_name, method_name, *method_args):
    try:
        registry = openerp.modules.registry.RegistryManager.get(db_name)
        assert registry, 'Unknown database %s' % db_name
        with registry.cursor() as cr:
            partner = registry['res.partner']
            return getattr(partner, method_name)(cr, *method_args)

    except Exception, e:
        _logger.exception('Failed to execute Mobile service method %s with args %r.',
            method_name, method_args)
        raise

def exp_signup(db_name, uid, passwd, login, name, password, passconfirm, context=None):
    return _mobile_partner_dispatch(db_name, 'signup', login, name, password, passconfirm, context)

def exp_products(db_name, uid, passwd, page=0, search='', category=None, context=None):
    return _mobile_product_dispatch(db_name, 'products_list', uid, page, search, category, context)

def exp_cart(db_name, uid, passwd, userid, context=None):
    return _mobile_product_dispatch(db_name, 'cart_items', userid, context)

def exp_add_to_cart(db_name, uid, passwd, product_id, add_qty=1, set_qty=0, context=None):
    return _mobile_product_dispatch(db_name, 'add_to_cart', uid, product_id, add_qty, set_qty, context)

def exp_profile(db_name, uid, passwd, userid, context=None):
    return _mobile_partner_dispatch(db_name, 'profile_get', userid, context)

def exp_profile_update(db_name, uid, passwd, **kw):
    return _mobile_partner_dispatch(db_name, 'profile_update', uid, **kw)

def exp_logout(db_name, uid, passwd, userid, context=None):
    return _mobile_partner_dispatch(db_name, 'logout', uid, userid, context)

def dispatch(method, params):
    if method in ['signup', 'products', 'profile', 'profile_update', 'cart', 'add_to_cart', 'product_cart_delete', 'logout', ]:
        (db, uid, passwd) = params[0:3]
        openerp.service.security.check(db, uid, passwd)
    else:
        raise KeyError("Method not found: %s." % method)
    fn = globals()['exp_' + method]
    return fn(*params)

openerp.service.wsgi_server.register_rpc_endpoint('mobile', dispatch)
