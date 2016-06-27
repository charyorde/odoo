from openerp.addons.base.ir.ir_qweb import QWeb
from openerp.addons.website_sale.controllers.main import QueryURL
from openerp.osv import osv, orm, fields
import werkzeug


class QueryURL2(object):
    def __init__(self, path='', **args):
        self.path = path
        self.args = args

    def __call__(self, path=None, **kw):
        if not path:
            path = self.path
        for k,v in self.args.items():
            kw.setdefault(k,v)
        l = []
        for k,v in kw.items():
            if v:
                if isinstance(v, list) or isinstance(v, set):
                    l.append(werkzeug.url_encode([(k,i) for i in v]))
                else:
                    l.append(werkzeug.url_encode([(k,v)]))
        if l:
            path += '?' + '&'.join(l)
        return path


class QWeb(orm.AbstractModel):
    _name = 'ir.qweb'
    _inherit = 'ir.qweb'

    def query_url(self, path='', **args):
        keep = QueryURL(path, args=args)
        return keep
