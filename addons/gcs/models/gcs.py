# -*- coding: utf-8 -*-
import logging
import json

import gevent
import requests
from concurrent import futures

import openerp
from openerp import models, fields, api
from openerp import SUPERUSER_ID
import openerp.addons.decimal_precision as dp
from openerp.tools.float_utils import float_round as round
from openerp.modules.registry import RegistryManager

from kombu.mixins import ConsumerMixin
from kombu import Connection, Exchange, Consumer, Queue

from openerp.addons.mobileservices.queue import produce
from openerp.addons.website_greenwood.main import Config

config = Config()
settings = config.settings()
db_name = openerp.tools.config['db_name']
registry = RegistryManager.get(db_name)
connection = Connection(settings.get('amqpurl'))
_logger = logging.getLogger(__name__)


def run_cloud_metrics(user):
    _logger.info("::gcs run_cloud_metrics for %r" % user)
    url = '%s/v1/metering/%s/bill' % (settings.get('gcs_endpoint'), user)
    requests.get(url)


class FutureWorker(futures.ThreadPoolExecutor):
    def __init__(self, max_workers=None):
        super(FutureWorker, self).__init__(max_workers=max_workers)

    def run(self, fn, arg):
        res = self.submit(fn, arg)
        if res.exception():
            val = None
            raise res.exception()
        else:
            val = res.result()
        return val

class instance_pricing(models.Model):
    """
    Cloud instance pricing
    """
    _name = 'gcs.instance.pricing'

    name = fields.Char(index=True, help="The flavor name")
    display_name = fields.Char()
    pricing_type = fields.Selection([
        ('on-demand', 'On-demand'), ('reserved', 'Fixed')],
        string="Type", default='on-demand',
        help="Cloud instance pricing can be either on-demand or reserved"
    )
    resource_type = fields.Selection([
        ('instance', 'Instance'), ('volume', 'Volume')],
        help="instance, volume, network for example")
    operating_system = fields.Selection(
        [('ubuntu', 'Linux Ubuntu'), ('centos', 'CentOS'),
         ('fedora', 'Fedora')], help="Operating System")
    price = fields.Float(digits=dp.get_precision('Account'), default=float(0.0),
                         help="The fixed price")
    hourly_rate = fields.Float(digits=dp.get_precision('Account'),
                               help="The hourly rate")
    ram = fields.Char(string="ram size")
    cpu = fields.Char(string="CPU size")
    disk = fields.Char(string="disk size")
    bandwidth = fields.Char(string="bandwidth size")
    country_code = fields.Many2one('res.country', string="Country", help="Pricing for this country")

    def create(self, cr, uid, params, context=None):
        res_id = super(instance_pricing, self).create(cr, uid, params, context=context)
        country_obj = self.pool['res.country']
        currency_obj = self.pool['res.currency']
        record = self.browse(cr, uid, [res_id])
        country = country_obj.browse(cr, uid, [record.country_code.id])
        currency = currency_obj.browse(cr, uid, [country.currency_id.id])
        prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        values = {
            'id': record.id,
			'display_name': record.display_name,
            'name': record.name,
            'price': record.price,
            'ram': record.ram,
            'pricing_type': record.pricing_type,
            'currency': currency.name,
            'bandwidth': record.bandwidth,
            'country_code': country.code,
            'currency_symbol': currency.symbol,
            'disk': record.disk,
            'cpu': record.cpu,
            'resource_type': record.resource_type,
            'hourly_rate': round(record.hourly_rate, prec)
        }
        #url = '%s/v1/vm/pricing' % settings.get('gcs_endpoint')
        #_logger.info("::Instance pricing create %r" % values)
        #requests.post(url, data=json.dumps(values))
        return res_id

    def write(self, cr, uid, ids, data, context=None):
        result = super(instance_pricing, self).write(cr, uid, ids, data, context=context)
        currency_obj = self.pool['res.currency']
        country_obj = self.pool['res.country']
        record = self.browse(cr, uid, ids)
        country = country_obj.browse(cr, uid, [record.country_code.id])
        currency = currency_obj.browse(cr, uid, [country.currency_id.id])
        prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        values = {
            'id': ids[0],
            'currency': currency.name,
            'currency_symbol': currency.symbol,
            'country_code': country.code,
            'hourly_rate': round(record.hourly_rate, 2),
            'updated': record.write_date
        }
        values.update(data)
        url = '%s/v1/vm/pricing' % settings.get('gcs_endpoint')
        _logger.info("::Instance pricing update %r" % values)
        requests.post(url, data=json.dumps(values))
        return result

    def name_get(self, cr, user, ids, context=None):
        """
        Returns a list of tupples containing id, name.
        result format: {[(id, name), (id, name), ...]}

        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param ids: list of ids for which name should be read
        @param context: context arguments, like lang, time zone

        @return: Returns a list of tupples containing id, name
        """
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        result = self.browse(cr, user, ids, context=context)
        res = []
        for rs in result:
            currency = rs.country_code.currency_id.name
            name = "%s (%s)" % (rs.name, currency)
            res += [(rs.id, name)]
        return res


class volume_pricing(models.Model):
    _name = 'gcs.volume.pricing'


class product_template(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    cloud_pricing = fields.Many2one('gcs.instance.pricing')

    def cloud_products(self, cr, uid, context=None):
        pool = self.pool
        company_ids = pool['res.company'].search(cr, uid, [('name', '=', 'GreenCloud')], context=context)
        company_id = company_ids[0]
        domain = [('company_id', '=', company_id)]
        ids = self.search(cr, uid, domain)
        products = self.browse(cr, uid, ids, context=context)
        return products

    def get_cloud_offerings(self, cr, uid, flavors, currency):
        offerings = []

        for f in flavors:
            terms = {'name': f['name'], 'currency': currency}
            vals = self.get_cloud_product(cr, uid, terms)
            if vals:
                vals['id'] = f['id']
                vals['name'] = f['name']
                offerings.append(vals)
        return offerings

    def get_cloud_product(self, cr, uid, terms):
        products = self.cloud_products(cr, uid)
        res = {}
        for product in products:
            value = self.find_product(cr, uid, product, terms)
            if value:
                res.update(value)
        return res

    def find_product(self, cr, uid, product, terms):
        pool = self.pool
        attr_obj = pool['product.attribute']
        result = {}
        currency_id = pool['res.currency'].search(cr, uid, [('name', '=', terms.get('currency'))])
        attr_values, flavor = [], {}
        cloud_pricing = product.cloud_pricing
        for v in product.product_variant_ids:
            for vid in v.attribute_value_ids:
                attr_values.append(vid.name)
                attr_name = attr_obj.browse(cr, uid, [vid.attribute_id.id]).name
                flavor[attr_name] = vid.name

        _logger.info("attr_values %r" % attr_values)
        _logger.info("flavor %r" % flavor)
        currency = product.pricelist_item_ids.currency_name
        flavor['currency_symbol'] = currency.symbol
        flavor['hourly_rate'] = round(cloud_pricing.hourly_rate, 2)
        flavor['resource_type'] = cloud_pricing.resource_type
        if terms['name'] in list(set(attr_values)) \
                and currency_id[0] == currency.id:
            result.update({'product_id': product.id,
                           'meta': flavor})
        return result


class res_user(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    cloud_userid = fields.Char(index=True, help="Cloud userid")

    def cloud_signup(self, cr, uid, post, context=None):
        _logger.info("New Cloud user signup %r" % post)
        pool = self.pool
        icp = pool['ir.config_parameter']
        cloud_userid = post.get('cloud_userid')
        login = post.get('login')
        company_ids = pool['res.company'].search(cr, uid, [('name', '=', 'GreenCloud')], context=context)
        company_id = company_ids[0]
        config = {
            'signup_enabled': icp.get_param(cr, SUPERUSER_ID, 'auth_signup.allow_uninvited') == 'True',
            'reset_password_enabled': icp.get_param(cr, SUPERUSER_ID, 'auth_signup.reset_password') == 'True',
        }
        ids = self.search(cr, uid, [('login', '=', login)], context=context)
        if ids:
            # add user to multi-currency(in_group_7) and
            # multi-company(in_group_6) groups
            group_multi_company = self.pool['ir.model.data'].get_object_reference(cr, uid, 'base', 'group_multi_company')[1]
            group_multi_currency = self.pool['ir.model.data'].get_object_reference(cr, uid, 'base', 'group_multi_currency')[1]
            # add greencloud as part of user's company
            vals = {
                'groups_id': [(6, 0, [group_multi_currency, group_multi_company])],
                'company_ids': [(6, 0, [company_id])],
                #'company_ids': [(4, company_id)],
                'cloud_userid': cloud_userid
            }
            return self.write(cr, SUPERUSER_ID, ids, vals, context=context)
        username, login = post.get('username'), post.get('login')
        values = {
            'login': login,
            'name': post.get('name'),
            'password': post.get('password'),
            'confirm_password': post.get('confirmpass'),
            'token': None,
            'company_id': company_id,
            'userhash': username,
            'cloud_userid': post.get('cloud_user_id')
        }
        values.update(config)
        db, login, password = pool['res.users'].signup(cr, SUPERUSER_ID, values, None)
        user_id = self.search(cr, uid, [('login', '=', login)], context=context)
        if user_id and not username:
            userhash = self._generate_userhash()
            pool['res.users'].write(cr, SUPERUSER_ID, user_id, {'userhash': userhash}, context=context)

        # Apply general user configs
        self.config_user(cr, uid, user_id, {'company_id': company_id})
        cr.commit()
        return [db, login, password] if all([k for k in [db, login, password]]) else None

    def config_user(self, cr, uid, user_id, **kwargs):
        company_id = kwargs.get('company_id')
        group_multi_company = self.pool['ir.model.data'].get_object_reference(cr, uid, 'base', 'group_multi_company')[1]
        group_multi_currency = self.pool['ir.model.data'].get_object_reference(cr, uid, 'base', 'group_multi_currency')[1]
        # @TODO: Add user to cloud_user group
        vals = {
            'groups_id': [(6, 0, [group_multi_currency, group_multi_company])],
            #'customer': True
        }
        if company_id:
            #vals['company_ids'] = [(4, company_id)]
            vals['company_ids'] = [(6, 0, [company_id])]
        return self.write(cr, SUPERUSER_ID, user_id, vals, context=context)


class sale_order(models.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'

    def cloud_bill(self, cr, uid, params, context=None):
        """
        create sale order with values as line items

        :param values: The possible line items
        :type values: dict
        """
        _logger.info("::gcs:cloud_bill preparing... %r" % params)
        pool = self.pool
        res = False
        cloud_userid = params.get('cloud_userid')
        login = params.get('email')
        orm_user = pool['res.users']
        company_ids = pool['res.company'].search(cr, uid, [('name', '=', 'GreenCloud')], context=context)
        company_id = company_ids[0]
        ids = orm_user.search(cr, uid, [('cloud_userid', '=', cloud_userid)], context=context)
        _logger.info("::gcs:cloud_bill ids %r" % ids)
        user_id = ids[0]
        sol = pool['sale.order.line']
        invoice_obj = pool['account.invoice']
        partner = orm_user.browse(cr, uid, ids, context).partner_id
        currency = dict(pool['res.currency'].name_search(cr, uid, name=params['currency']))
        pricelist_id = pool['product.pricelist'].search(cr, uid,
                                                        [('currency_id', 'in', currency.keys()),
                                                         ('company_id', '=', company_id)])
        acquirer = dict(pool['payment.acquirer'].name_search(cr, uid, name='Paystack'))

        values = {
            'user_id': user_id,
            'partner_id': partner.id,
            'pricelist_id': pricelist_id[0],
            'section_id': pool['ir.model.data'].get_object_reference(cr, uid, 'website', 'salesteam_website_sales')[1],
            'company_id': company_id,
            'payment_acquirer_id': acquirer.keys()[0]
        }
        sale_order_id = self.create(cr, SUPERUSER_ID, values, context=context)
        cr.commit()
        values = self.onchange_partner_id(cr, SUPERUSER_ID, [], partner.id, context=context)['value']
        self.write(cr, SUPERUSER_ID, [sale_order_id], values, context=context)

        products = params.get('lines')

        # create order_line from params
        vals = self._prepare_products(cr, uid, sale_order_id, products)
        _logger.info("::cloud_bill sale_order_line %r" % vals)
        for val in vals:
            sol.create(cr, uid, val, context=context)
            cr.commit()

        # confirm the order
        self.action_button_confirm(cr, uid, [sale_order_id])

        # create invoice
        inv_id = self.action_invoice_create(cr, uid, [sale_order_id], date_invoice=fields.datetime.now())
        cr.commit()

        if inv_id:
            # set invoice state = 'open'
            invoice_obj.invoice_validate(cr, uid, inv_id)
        return self._send_invoice(cr, uid, inv_id, [sale_order_id])

    def _prepare_products(self, cr, uid, order_id, lines, context=None):
        _logger.info("Processing GCS Order lines %r" % lines)
        pool = self.pool
        product_obj = pool['product.product']

        values = []
        for line in lines:
            product_tmpl_id = line.get('product_id')
            product_id = product_obj.search(cr, uid, [('product_tmpl_id', '=', product_tmpl_id)])
            product = product_obj.browse(cr, uid, product_id)
            cpu = line.get('cpu')
            disk = line.get('disk')
            traffic = line.get('traffic')

            parts = []
            if cpu:
                parts.append({'value': cpu, 'label': 'CPU',
                              'price_unit': self.get_price_extra(cr, uid, product, 'cpu')})
            if disk:
                parts.append({'value': disk, 'label': 'Disk',
                              'price_unit': self.get_price_extra(cr, uid, product, 'disk')})
            if traffic:
                parts.append({'value': traffic, 'label': 'Traffic',
                              'price_unit': self.get_price_extra(cr, uid, product, 'bandwidth')})
            for part in parts:
                values.append({
                    'name': '  '.join([product.name, part.get('label')]),
                    'product_id': product.id, 'order_id': order_id,
                    'product_uom_qty': part.get('value'),
                    'price_unit': part.get('price_unit'),
                    'product_uom': product.uom_id.id
                })

        return values

    def get_price_extra(self, cr, uid, product, name):
        pool = self.pool
        value_id = pool['product.attribute'].name_search(cr, uid, name=name)
        res = float(0.0)
        for val in product.attribute_value_ids:
            for price_id in val.price_ids:
                if price_id.value_id.id == value_id[0][0]:
                    res = price_id.price_extra
        return res

    def _send_invoice(self, cr, uid, invoice_id, ids, context=None):
        ir_model_data = self.pool.get('ir.model.data')
        try:
            template_id = ir_model_data.get_object_reference(cr, uid, 'account', 'email_template_edi_invoice')[1]
        except ValueError:
            template_id = False

        composer_obj = self.pool['mail.compose.message']
        composer_values = {}
        email_ctx = dict()
        email_ctx.update({
            'default_model': 'account.invoice',
            'default_res_id': invoice_id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })

        template_values = [
            email_ctx.get('default_template_id'),
            email_ctx.get('default_composition_mode'),
            email_ctx.get('default_model'),
            email_ctx.get('default_res_id'),
        ]

        composer_values.update(composer_obj.onchange_template_id(cr, uid, None, *template_values, context=context).get('value', {}))
        #if not composer_values.get('email_from'):
            #composer_values['email_from'] = self.browse(cr, uid, ids, context=context).company_id.email
        for key in ['attachment_ids', 'partner_ids']:
            if composer_values.get(key):
                composer_values[key] = [(6, 0, composer_values[key])]
        composer_id = composer_obj.create(cr, uid, composer_values, context=email_ctx)
        composer_obj.send_mail(cr, uid, [composer_id], context=email_ctx)
        return True

    @api.v7
    def _gather_metrics(self, cr, uid, context=None):
        _logger.info("metering cron v7")
        users_obj = self.pool['res.users']
        greencloud_id = self.pool['res.company'].search(cr, uid, [('name', '=', 'GreenCloud')])[0]
        user_ids = users_obj.search(cr, uid, [])
        users = users_obj.browse(cr, uid, user_ids)
        clouders = []
        for user in users:
            for coy in user.company_ids:
                if coy.id == greencloud_id:
                    clouders.append(user)

        for c in clouders:
            if c.cloud_userid:
                FutureWorker(max_workers=1).run(run_cloud_metrics, c.cloud_userid)

    #@api.v8
    #@api.multi
    #def _gather_metrics(self):
        #_logger.info("metering cron v8")
        #users_obj = self.env['res.users']
        #greencloud = self.env['res.company'].search([('name', '=', 'GreenCloud')])
        #_logger.info("gcs company %r" % greencloud)
        #users = users_obj.search([])
        #clouders = []
        #for user in users:
            #for coy in user.company_ids:
                #_logger.info("company ids %r" % coy)
                # if user's company_ids contain GreenCloud company_id
                #if coy.id == greencloud.id:
                    #clouders.append(user)

        #for c in clouders:
            #FutureWorker(max_workers=1).run(run_cloud_metrics, c)


class C(ConsumerMixin):

    def __init__(self, connection):
        _logger.info("Running GCS consumers")
        self.connection = connection

    def get_consumers(self, Consumer, channel):
        exchange = Exchange('gcs', type='direct', durable=True)
        queue = Queue('cloud', exchange, routing_key='gcs.user.measures')
        cloud_user_q = Queue('cloud', exchange, routing_key='gcs.user.new')
        return [
            Consumer(queue, callbacks=[self.on_message]),
            Consumer(cloud_user_q, callbacks=[self.cloud_signup_handler]),
        ]

    def on_message(self, body, message):
        global registry
        with registry.cursor() as cr:
            registry.get('sale.order').cloud_bill(cr, SUPERUSER_ID, body)
        message.ack()

    def cloud_signup_handler(self, body, message):
        _logger.info("New cloud signup %r" % body)
        global registry
        with registry.cursor() as cr:
            registry.get('res.user').cloud_signup(cr, SUPERUSER_ID, body)
        message.ack()
