import logging

import openerp

_logger = logging.getLogger(__name__)

def _cheape_product_dispatch(db_name, method_name, *method_args):
    try:
        registry = openerp.modules.registry.RegistryManager.get(db_name)
        assert registry, 'Unknown database %s' % db_name
        with registry.cursor() as cr:
            product = registry['product.template']
            return getattr(product, method_name)(cr, *method_args)

    except Exception, e:
        _logger.exception('Failed to execute Cheape service method %s.', method_name)
        raise

def _cheape_dispatch(db_name, entity_name, method_name, *method_args):
    try:
        registry = openerp.modules.registry.RegistryManager.get(db_name)
        assert registry, 'Unknown database %s' % db_name
        with registry.cursor() as cr:
            entity = registry[entity_name]
            return getattr(entity, method_name)(cr, *method_args)

    except Exception, e:
        _logger.exception('Failed to execute Cheape service method %s.', method_name)
        raise

def ext_bet(db_name, uid, passwd, data, context):
    return _cheape_dispatch(db_name, 'cheape.bet', 'bet', data, context)

def ext_cheape_products(db_name, uid, passwd, data, context):
    return _cheape_product_dispatch(db_name, 'bet', uid, data, context)

def ext_play_live(db_name, uid, passwd, params, context):
    return _cheape_dispatch(db_name, 'cheape.livebid', 'create', params, context)

def ext_cheape_signup(db_name, uid, passwd, login, name, password, passconfirm, context):
    return _cheape_dispatch(dbname, 'res.users', 'cheape_signup', login, name, password, passconfirm, context)

def dispatch(method, params):
    if method in ['bet',
                  'cheape_products',
                  'play_live',
                  'cheape_signup',
                  ]:
        (db, uid, passwd) = params[0:3]
        openerp.service.security.check(db, uid, passwd)
    else:
        raise KeyError("Method not found: %s." % method)
    fn = globals()['exp_' + method]
    return fn(*params)

openerp.service.wsgi_server.register_rpc_endpoint('cheape', dispatch)
