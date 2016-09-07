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
        _logger.exception('Failed to execute Mobile service method %s.', method_name)
        raise

def _mobile_partner_dispatch(db_name, method_name, *method_args):
    try:
        registry = openerp.modules.registry.RegistryManager.get(db_name)
        assert registry, 'Unknown database %s' % db_name
        with registry.cursor() as cr:
            partner = registry['res.partner']
            return getattr(partner, method_name)(cr, *method_args)

    except Exception, e:
        _logger.exception('Failed to execute Mobile service method %s.', method_name)
        raise

def _mobile_users_dispatch(db_name, method_name, *method_args):
    try:
        registry = openerp.modules.registry.RegistryManager.get(db_name)
        assert registry, 'Unknown database %s' % db_name
        with registry.cursor() as cr:
            users = registry['res.users']
            return getattr(users, method_name)(cr, *method_args)

    except Exception, e:
        _logger.exception('Failed to execute Mobile service method %s with args %r.',
            method_name, method_args)
        raise

def exp_signup(db_name, uid, passwd, login, name, password, passconfirm, context=None):
    return _mobile_users_dispatch(db_name, 'mobile_signup', login, name, password, passconfirm, context)

def exp_products(db_name, uid, passwd, page=0, search='', category=None, context=None):
    return _mobile_product_dispatch(db_name, 'products_list', uid, page, search, category, context)

def exp_cart(db_name, uid, passwd, userid, context=None):
    return _mobile_product_dispatch(db_name, 'cart_items', userid, context)

def exp_add_to_cart(db_name, uid, passwd, user_id, product_id, line_id=None, add_qty=1, set_qty=0, context=None, **kwargs):
    return _mobile_product_dispatch(db_name, 'add_to_cart', user_id, product_id, line_id, add_qty, set_qty, context, **kwargs)

def exp_remove_from_cart(db_name, uid, passwd, user_id, product_id, line_id=None, add_qty=1, set_qty=0, context=None, **kwargs):
    return _mobile_product_dispatch(db_name, 'remove_from_cart', user_id, product_id, line_id, add_qty, set_qty, context, **kwargs)

def exp_checkout(db_name, uid, passwd, user_id, context=None):
    return _mobile_product_dispatch(db_name, 'checkout', user_id, context)

def exp_confirm_order(db_name, uid, passwd, user_id, data, context=None):
    return _mobile_product_dispatch(db_name, 'confirm_order', user_id, data, context)

def exp_create_tx(db_name, uid, passwd, user_id, acquirer_id, context=None):
    return _mobile_product_dispatch(db_name, 'create_tx', user_id, acquirer_id, context)

def exp_country_states(db_name, uid, passwd, country_id):
    return _mobile_product_dispatch(db_name, 'country_states', country_id)

def exp_get_credit_score(db_name, uid, passwd, user_id, context=None):
    return _mobile_partner_dispatch(db_name, 'get_credit_score', user_id, context)

def exp_profile(db_name, uid, passwd, userid, context=None):
    return _mobile_partner_dispatch(db_name, 'profile_get', userid, context)

def exp_profile_update(db_name, uid, passwd, partner_id, post, context=None):
    return _mobile_partner_dispatch(db_name, 'profile_update', partner_id, post, context)

def exp_post_file(db_name, uid, passwd, user_id, filename, data):
    return _mobile_partner_dispatch(db_name, 'postFile', user_id, filename, data)

def exp_logout(db_name, uid, passwd, userid, context=None):
    return _mobile_partner_dispatch(db_name, 'logout', uid, userid, context)

def dispatch(method, params):
    if method in ['signup',
                  'products',
                  'profile',
                  'profile_update',
                  'get_credit_score',
                  'post_file',
                  'cart',
                  'add_to_cart',
                  'remove_from_cart',
                  'checkout',
                  'confirm_order',
                  'create_tx',
                  'country_states',
                  'product_cart_delete',
                  'logout',
                  ]:
        (db, uid, passwd) = params[0:3]
        openerp.service.security.check(db, uid, passwd)
    else:
        raise KeyError("Method not found: %s." % method)
    fn = globals()['exp_' + method]
    return fn(*params)

openerp.service.wsgi_server.register_rpc_endpoint('mobile', dispatch)
