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

def exp_bet(db_name, uid, passwd, data, context=None):
   return _cheape_dispatch(db_name, 'cheape.bet', 'bet', uid, data, context)

def exp_cheape_products(db_name, uid, passwd, page=0, search='', category=None, kw=None, context=None):
    return _cheape_product_dispatch(db_name, 'cheape_products', uid, page, search, category, kw, context)

def exp_play_live(db_name, uid, passwd, params, context=None):
    return _cheape_dispatch(db_name, 'cheape.livebid', 'create', params, context)

def exp_cheape_signup(db_name, uid, passwd, post, context=None):
    return _cheape_dispatch(db_name, 'res.users', 'cheape_signup', uid, post, context)

def exp_add_to_watchlist(db_name, uid, passwd, params, context=None):
    return _cheape_dispatch(db_name, 'cheape.watchlist', 'create', uid, params, context)

def exp_my_watchlist(db_name, uid, passwd, partner_id, context=None):
    return _cheape_dispatch(db_name, 'res.partner', 'cheape.watchlist', uid, partner_id, context)

def exp_bid_history(db_name, uid, passwd, partner_id, context=None):
    return _cheape_dispatch(db_name, 'res.partner', 'bid_history', uid, partner_id, context)

def exp_account_update(db_name, uid, passwd, user_id, post, context=None):
    return _cheape_dispatch(db_name, 'res.users', 'account_update', uid, user_id, post, context)

def exp_get_free_bids(db_name, uid, passwd, partner_id, context=None):
    return _cheape_dispatch(db_name, 'res.partner', 'award_free_bids', uid, partner_id, context)

def dispatch(method, params):
    if method in ['bet',
                  'cheape_products',
                  'play_live',
                  'cheape_signup',
                  'add_to_watchlist',
                  'my_watchlist',
                  'bid_history',
                  'account_update',
                  'get_free_bids',
                  ]:
        (db, uid, passwd) = params[0:3]
        openerp.service.security.check(db, uid, passwd)
    else:
        raise KeyError("Method not found: %s." % method)
    fn = globals()['exp_' + method]
    return fn(*params)

openerp.service.wsgi_server.register_rpc_endpoint('cheape', dispatch)
