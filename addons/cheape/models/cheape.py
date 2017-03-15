# -*- coding: utf-8 -*-
import logging
import simplejson
import math
from datetime import timedelta, datetime
import random
import time

import gevent
from gevent import Greenlet, getcurrent
from gevent.local import local
from gevent.event import AsyncResult

import openerp
from openerp import models, fields, api
from openerp import SUPERUSER_ID
from openerp.addons.mobileservices.queue import produce, dist_queue
import openerp.addons.decimal_precision as dp
from openerp.addons.website_greenwood.main import Config
from openerp.modules.registry import RegistryManager

import kombu
from kombu.mixins import ConsumerMixin
from kombu import Connection, Exchange, Consumer, Queue

config = Config()
settings = config.settings()
db_name = openerp.tools.config['db_name']
registry = RegistryManager.get(db_name)
connection = Connection(settings.get('amqpurl'))

from hashids import Hashids

_logger = logging.getLogger(__name__)

DEFAULT_BIDS_SPENT = 1

def json_dump(v):
    return simplejson.dumps(v, separators=(',', ':'))

def _compute_hour_to_secs(hr):
    return int(timedelta(hours=hr, minutes=00).total_seconds())

def _hours_list():
    l = [
            (_compute_hour_to_secs(1), '01:00'),
            (_compute_hour_to_secs(2), '02:00'),
            (_compute_hour_to_secs(3), '03:00'),
            (_compute_hour_to_secs(4), '04:00'),
            (_compute_hour_to_secs(5), '05:00'),
            (_compute_hour_to_secs(6), '06:00'),
            (_compute_hour_to_secs(7), '07:00'),
            (_compute_hour_to_secs(8), '08:00'),
            (_compute_hour_to_secs(9), '09:00'),
            (_compute_hour_to_secs(10), '10:00'),
            (_compute_hour_to_secs(11), '11:00'),
            (_compute_hour_to_secs(12), '12:00'),
            (_compute_hour_to_secs(13), '13:00'),
            (_compute_hour_to_secs(14), '14:00'),
            (_compute_hour_to_secs(15), '15:00'),
            (_compute_hour_to_secs(16), '16:00'),
            (_compute_hour_to_secs(17), '17:00'),
            (_compute_hour_to_secs(18), '18:00'),
            (_compute_hour_to_secs(19), '19:00'),
            (_compute_hour_to_secs(20), '20:00'),
            (_compute_hour_to_secs(21), '21:00'),
            (_compute_hour_to_secs(22), '22:00'),
            (_compute_hour_to_secs(23), '23:00'),
            (_compute_hour_to_secs(24), '24:00'),
        ]
    return l

def _publish_autobids(data):
    qparams = {
        'exchange': 'livebid',
        'routing_key': 'autobids',
        'type': 'direct',
    }
    produce(data, **qparams)

def _publish_livebet(data):
    qparams = {
        'exchange': 'livebid',
        'routing_key': 'livebet',
        'type': 'direct',
    }
    produce(data, **qparams)


class cheape_account(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    #partner_id = fields.Many2one('res.partner', string='Partner', required=True, readonly=True)
    bidswon = fields.One2many('cheape.livebid', 'wonby', help="A list of live bids won by the current user")
    #bidswon = fields.Many2many('cheape.livebid', compute='_my_bidswon', store=False, readonly=True, help="A list of live bids won by the current user")
    bidscount = fields.Integer(string="My bids", default=0, required=True, help="Total number of a user's purchased bids")
    # A list of the current user's watchlist
    watchlist_ids = fields.One2many('cheape.watchlist', 'partner_id', help="A list of the current user's watchlist")
    #watchlist_ids = fields.Many2many('cheape.watchlist', compute='_my_watchlist', store=False, readonly=True, help="A list of the current user's watchlist")
    last_free_bids_date = fields.Char(string="Last free bids date")

    def bid_history(self, cr, uid, partner_id, context=None):
        pool, values = self.pool, []
        partner = self.browse(cr, uid, [partner_id], context=context)
        #wonbids = pool['cheape.livebid'].search(cr, uid, [('wonby', '=', int(partner_id))], context=context)
        #_logger.info("%s bid history %s" % (partner_id, wonbids))
        _logger.info("%s bid history %s" % (partner_id, partner.bidswon))
        livebids = partner.bidswon
        if livebids:
            # wonbids.bidswon
            for l in livebids:
                values.append({
                    'product_id': l.product_id.id,
                    'name': l.product_id.name,
                    'bid_total': l.product_id.bid_total,
                    'claimed': l.claimed
                })
        return values

    def topup_bidpacks(self, cr, uid, data, context=None):
        login = data.get('login')
        userid = self.pool['res.users'].search(cr, uid, [('login', '=', login)], context=context)
        user = self.pool['res.users'].browse(cr, uid, userid, context=context)
        partner_id = user.partner_id.id
        partner = self.browse(cr, uid, [partner_id], context=context)
        values = {
            'bidscount': sum([partner.bidscount, data.get('qty')])
        }
        return self.write(cr, uid, [partner_id], values)

    def reduce_bidpacks(self, cr, uid, partner_id, qty, context=None):
        """ Reduce user's bidpacks by x amount """
        cheape_account = self.browse(cr, uid, [partner_id], context=context)
        bids = reduce(lambda x, y: x-y, [cheape_account.bidscount, qty])
        # prevent negative value
        bids = 0 if bids < 0 else bids
        self.write(cr, uid, [cheape_account.id], {'bidscount': bids})
        return bids

    #@api.depends('partner_id')
    def _my_watchlist(self, cr, uid, ids, context=None):
        watchlist_obj = self.pool['cheape.watchlist']
        #watchlists = watchlist_obj.browse(cr, uid, [self.partner_id], context=context)
        watchlists = watchlist_obj.browse(cr, uid, [self.id], context=context)
        l = []
        if watchlists:
            for record in watchlists:
                l.append({'id': record.id,
                        'name': record.product_id.name})
        return l or [(0, _, _)]

    #@api.depends('partner_id')
    def _my_bidswon(self, cr, uid, ids, context=None):
        livebid_obj = self.pool['cheape.livebid']
        # livebids participated in by partner_id
        #bids_won = livebid_obj.browse(cr, uid, [self.partner_id], context=context)
        #bids_won_ids = livebid_obj.search(cr, uid, [('wonby', '=', self.partner_id)], context=context)
        bids_won_ids = livebid_obj.search(cr, uid, [('wonby', '=', self.id)], context=context)
        bids_won = livebid_obj.browse(cr, uid, bids_won_ids, context=context)
        l = []
        if bids_won:
            for livebid in bids_won:
                l.append({'id': livebid.id,
                        'name': livebid.product_id.name})

        return l or [(0, _, _)]

    def award_free_bids(self, cr, uid, partner_id, context=None):
        partner = self.browse(cr, uid, [partner_id], context=context)
        today = datetime.now().strftime('%Y-%m-%d')
        if not partner:
            return False, "Couldn't validate user"
        if partner.last_free_bids_date != today:
            bids = sum([partner.bidscount, 50])
            self.write(cr, uid, [partner_id], {'bidscount': bids, 'last_free_bids_date': today})
            return True, "Congratulations! You've been awarded 50 free bid packs"
        else:
            return False, "You've already used up your free bids for today."


class bet(models.Model):
    """ A cheape bet """
    _name = 'cheape.bet'

    livebid_id = fields.Many2one('cheape.livebid', string="The livebid", readonly=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.template', string="Product", readonly=True, index=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True, index=True)
    bids_spent = fields.Integer(help="A count of bids spent by this user", default=0)
    bids_spent_value = fields.Float(compute='_compute_bids_spent_value', digits_compute=dp.get_precision('Product Price'), store=True, help="The sum of total bids placed by user on a specific livebid")
    buy_it_now_price = fields.Float(compute='_compute_buy_it_now_price', digits_compute=dp.get_precision('Product Price'), store=True)

    def bet(self, cr, uid, data, context=None):
        """ Non-livebid bet """
        _logger.info("New bet %r" % data)
        pool = self.pool
        product_obj = pool['product.template']
        partner_obj = pool['res.partner']
        livebid = pool['cheape.livebid'].browse(cr, uid, [data.get('livebid_id')])
        product = livebid.product_id
        partnerid = data.get('partner_id')
        partner = partner_obj.browse(cr, uid, [partnerid])
        user_id = pool['res.users'].search(cr, uid, [('partner_id', '=', partnerid)], context=context)
        user = pool['res.users'].browse(cr, uid, user_id, context=context)
        bid_ids = self.search(cr, uid, [('partner_id', '=', data['partner_id']), ('livebid_id', '=', data['livebid_id'])])
        userbet = self.browse(cr, uid, bid_ids, context=None)
        values = data.copy()
        if values['binding_key']:
            del values['binding_key']

        # Validate whether user has bids
        if partner.bidscount < 1:
            return False

        if bid_ids:
            # Update
            val = [userbet.bids_spent, DEFAULT_BIDS_SPENT]
            values['bids_spent'] = sum(val)
            record = self.write(cr, uid, bid_ids, values)
        else:
            values['bids_spent'] = DEFAULT_BIDS_SPENT
            values['bids_spent_value'] = float(1.0)
            #record = self.create(cr, uid, values)
            record = super(bet, self).create(cr, uid, values, context=context)
        # Update product_template. with new bidprice
        product_obj.write(cr, uid, values['product_id'], {'bid_total': math.fsum([product.bid_total, livebid.raiser])})
        # Reduce user's bidpacks by livebid.bidpacks_qty
        partner_obj.reduce_bidpacks(cr, uid, values['partner_id'], livebid.bidpacks_qty)
        d = {
            'livebid_id': values['livebid_id'],
            'partner_id': values['partner_id'],
            'username': user.userhash,
            'auction_price': product.bid_total,
            'binding_key': 'livebet'
        }
        _publish_livebet(d)
        return d or False

    def livebet(self, cr, uid, values, context=None):
        pool = self.pool
        partner_obj = pool['res.partner']
        product_obj = pool['product.template']
        livebid_obj = pool['cheape.livebid']
        cheape_account_obj = pool['res.partner']

        if values['binding_key']:
            del values['binding_key']

        product = product_obj.browse(cr, uid, values['product_id'])
        livebid = pool['cheape.livebid'].browse(cr, uid, values['livebid_id'])
        partner = partner_obj.browse(cr, uid, values['partner_id'])
        bid_ids = self.search(cr, uid, [('partner_id', '=', values['partner_id']), ('livebid_id', '=', data['livebid_id'])])
        userbet = self.browse(cr, uid, bid_ids, context=None)

        # Validate whether user has bids
        if partner.bidscount < 1:
            return False

        if bid_ids:
            # Update
            val = [userbet.bids_spent, DEFAULT_BIDS_SPENT]
            values['bids_spent'] = sum(val)
            record = self.write(cr, uid, bid_ids, values)
        else:
            values['bids_spent'] = DEFAULT_BIDS_SPENT
            values['bids_spent_value'] = float(1.0)
            #record = self.create(cr, uid, values)
            record = super(bet, self).create(cr, uid, values, context=context)

        # Increment totalbids spent on this livebid
        totalbids = livebid.totalbids + 1
        livebid_obj.write(cr, uid, [values['livebid_id']], {'totalbids': totalbids}, context=context)
        # Update product_template with new bidprice
        product_obj.write(cr, uid, values['product_id'], {'bid_total': math.fsum([product.bid_total, livebid.raiser])})
        # Reduce user's bidpacks by livebid.bidpacks_qty
        cheape_account_obj.reduce_bidpacks(cr, uid, values['partner_id'], livebid.bidpacks_qty)
        d = {
            'livebid_id': values['livebid_id'],
            'partner_id': values['partner_id'],
            'username': partner.user_id.userhash,
            'auction_price': product.bid_total,
            'binding_key': 'livebet'
        }
        _publish_livebet(d)
        # reset livebid.countdown and publish message back to client
        # return payload [bidpacks_left, bid_total]
        return record

    def _compute_bet(self, cr, uid, partner_id, context=None):
        """ Compute total bids on a livebid per user """
        # A list of all bets by this user on this livebid
        # math.fsum(values)
        pass

    @api.multi
    @api.depends('bids_spent_value', 'livebid_id', 'partner_id')
    def _compute_buy_it_now_price(self):
        """ Retail price - bids_spent_value """
        #livebid = self.env['cheape.livebid'].browse()
        #if livebid:
            #retail_price = livebid.product_id.price
            #res = reduce(lambda x, y: x-y, [retail_price, self.bids_spent_value])
            #self.buy_it_now_price = res
        rec = self.search([('livebid_id', '=', self.livebid_id.id), ('partner_id', '=', self.partner_id.id)])
        if rec:
            livebid = rec.livebid_id
            retail_price = livebid.product_id.list_price
            _logger.info("compute buy_it_now_price: retail_price %r" % retail_price)
            res = reduce(lambda x, y: x-y, [retail_price, self.bids_spent_value])
        else:
            res = float(0)
        self.buy_it_now_price = res

    @api.multi
    @api.depends('bids_spent', 'livebid_id', 'partner_id')
    def _compute_bids_spent_value(self):
        # we browse on the recordset not the id becos of v8 API. see
        # https://github.com/odoo/odoo/issues/9675
        rec = self.search([('livebid_id', '=', self.livebid_id.id), ('partner_id', '=', self.partner_id.id)])
        if rec:
            livebid = rec.livebid_id
            res =  float(self.bids_spent * livebid.bid_cost)
        else:
            res = float(1 * self.bids_spent)
        _logger.info("new bids_spent_value %r" % res)
        self.bids_spent_value = res

    @api.v7
    def _machina_bid(self, cr, uid, context=None):
        users_obj = self.pool['res.users']
        livebet_obj = self.pool['cheape.bet']
        machina_group_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'cheape', 'group_cheape_machina')[1]
        user_ids = users_obj.search(cr, uid, [])
        users = users_obj.browse(cr, uid, user_ids)
        machinas = []
        # users in group machinas
        for user in users:
            for g  in user.groups_id:
                if g.id == machina_group_id:
                    machinas.append(user)
        #gids = [g.id for g in user.groups_id if g.id == machina_group_id for user in users]
        #_logger.info("user group ids %r" % gids)
        # Random selection of a machina
        machina = random.choice(machinas)
        # @todo Test for required total players
        ids = self.pool['cheape.livebid'].search(cr, uid, [('power_switch', '=', 'on')])
        livebids = self.pool['cheape.livebid'].browse(cr, uid, ids)
        #livebids = [live_auctions] if len(live_auctions) == int(1) else live_auctions
        if livebids is not None:
            for record in livebids:
                if record:
                    current_auction_price = record.product_id.bid_total
                    #product = self.env['product.template'].browse([record.product_id.id])
                    #_logger.info("maximum_bids_total %r" % record.product_id.maximum_bids_total())
                    if current_auction_price < record.product_id.maximum_bids_total():
                        values = {
                            'livebid_id': record.id,
                            'product_id': record.product_id.id,
                            'partner_id': machina.partner_id.id,
                            'binding_key': 'livebet'
                        }
                        livebet_obj.bet(cr, uid, values)
                        _logger.info("Machina placed a bet %r" % machina.login)

    @api.v8
    @api.multi
    def _machina_bid(self):
        users_obj = self.env['res.users']
        livebet_obj = self.env['cheape.bet']
        machina_group_id = self.env['ir.model.data'].get_object_reference('cheape', 'group_cheape_machina')[1]
        users = users_obj.search([])
        machinas = []
        # users in group machinas
        for user in users:
            for g  in user.groups_id:
                if g.id == machina_group_id:
                    machinas.append(user)
        _logger.info("machina %r" % machinas)
        #gids = [g.id for g in user.groups_id if g.id == machina_group_id for user in users]
        # Random selection of a machina
        machina = random.choice(machinas)
        # @todo Test for required total players
        livebids = self.env['cheape.livebid'].search([('power_switch', '=', 'on')])
        #livebids = [live_auctions] if len(live_auctions) == int(1) else live_auctions
        if livebids is not None:
            for record in livebids:
                if record:
                    current_auction_price = record.product_id.bid_total
                    product = self.env['product.template'].browse([record.product_id.id])
                    _logger.info("maximum_bids_total %r" % record.product_id.maximum_bids_total())
                    if current_auction_price < record.product_id.maximum_bids_total():
                        values = {
                            'livebid_id': record.id,
                            'product_id': record.product_id.id,
                            'partner_id': machina.partner_id.id,
                            'binding_key': 'livebet'
                        }
                        livebet_obj.bet(values)
                        _logger.info("Machina placed a bet %r" % machina.login)


class livebid(models.Model):
    """ A live auction """
    _name = 'cheape.livebid'

    name = fields.Char(help="A unique livebid name")
    product_id = fields.Many2one('product.template', domain=[('company_id.name', '=', 'Cheape')], string="Product", required=True)
    power_switch = fields.Selection(
        [('on', 'On'),('off', 'Off'), ('stop', 'Stop')], string="Power Switch", help="Switch the state of a livebid")
    islive = fields.Boolean(string="IsLive", index=True, default=False, help="Power on/off this livebid")
    # Is the livebid open or closed
    status = fields.Selection([('open', 'Open'),('closed', 'Closed'),], string="Status", default="closed",
                              required=True, help="An Auction can be paused but still be open")
    start_time = fields.Selection(_hours_list(), string="Auction Start time", required=True, default=_compute_hour_to_secs(8))
    end_time = fields.Selection(_hours_list(), string="Auction End time", required=True, default=_compute_hour_to_secs(14))
    countdown = fields.Integer(compute='_compute_countdown', store=True, help="A livebid countdown in seconds. This is the aggregate of the start and end time. For example, 10")
    heartbeat = fields.Integer(required=True, help="The countdown period where most bids takes place")
    # Query bet table by this livebid_id. Return the sum
    amount_totalbids = fields.Float(string='Amount total bids', compute='_compute_amount_totalbids', store=True, help='Sum of all total bids placed on this livebid')
    #amount_totalbids = fields.Float(string="Total bids value", default=float(0.0), help="Total bids on a livebid")
    wonby = fields.Many2one('res.partner', string="Livebid winner")
    raiser = fields.Float(default=float(0.01), help="The value in which bets on this livebid increments by")
    bidpacks_qty = fields.Integer(string="Bidpacks per bid", default=1, help="The quantity of bidpacks per bid required on this livebid")
    autobids = fields.One2many('cheape.autobid', 'livebid_id', help="A list of autobids on this livebid")
    totalbids = fields.Integer(string="Total bids", help="The total bids placed since live bid begun")
    claimed = fields.Boolean(help="A livebid winner either claims it or not", default=False)
    bid_cost = fields.Float(default=float(0.50), help="Cost per bid")

    _sql_constraints = [
        ('product_id_uniq', 'UNIQUE(product_id)', 'A livebid product_id must be unique!'),
    ]

    @api.depends('product_id')
    def _compute_amount_totalbids(self):
        """ Sum all bets on this livebid """
        bet_obj = self.pool['cheape.bet']
        #total_bet = bet_obj.product_id.bid_total
        total_bet = self.product_id.bid_total
        for record in self:
            #record.amount_totalbids = math.fsum(total_bet)
            record.amount_totalbids = total_bet

    @api.onchange('start_time', 'end_time')
    def _onchange_auction_time(self):
        start_secs = int(self.start_time)
        end_secs = int(self.end_time)
        #self.countdown = int(sum([start_secs, end_secs]))
        self.countdown = int(reduce(lambda x, y: x-y, [end_secs, start_secs]))

    @api.depends('start_time', 'end_time')
    def _compute_countdown(self):
        start_secs = int(self.start_time)
        end_secs = int(self.end_time)
        #self.countdown = int(sum([start_secs, end_secs]))
        self.countdown = int(reduce(lambda x, y: x-y, [end_secs, start_secs]))

    def onchange_hour(self, cr, uid, ids, value):
        hour = value.split(' ')[0]
        hr = timedelta(hours=hour, minutes=00)
        return hr.total_seconds()

    def create(self, cr, uid, params, context=None):
        _logger.info("livebid create %r" % params)
        pool = self.pool
        livebid_name_obj = pool['cheape.livebid.name']
        params['name'] = ''
        #islive = params.get('islive')
        power = params.get('power_switch')
        if power == 'on':
            livebid_name = livebid_name_obj._generate_livebid_name()
            params['name'] = livebid_name
        record = super(livebid, self).create(cr, uid, params, context=context)
        if record:
            new_record = self.browse(cr, uid, [record])
            params['countdown'] = new_record.countdown

        # create livebid_name only when islive is True
        if power == 'on':
            livebid_name_obj.create(cr, uid, {'name': livebid_name, 'livebid_id':record}, context=context)

        livebid_name_ids = livebid_name_obj.search(cr, uid, [])
        _logger.info("livebid_name_ids %r" % livebid_name_ids)
        livebid_names = livebid_name_obj.browse(cr, uid, livebid_name_ids, context=context)
        names = [name.name for name in livebid_names]
        _logger.info("livebid_names %r" % names)

        with openerp.sql_db.db_connect('postgres').cursor() as cr2:
            #cr2.execute("notify cheape_livebid, %s", (json_dump(params),))
            if power == 'on':
                cr2.execute("notify cheape_livebid, %s", (simplejson.dumps(params),))
        return record

    def write(self, cr, uid, ids, data, context=None):
        _logger.info("livebid update %r" % data)
        livebid_obj = self.pool['cheape.livebid']
        livebid_name_obj = self.pool['cheape.livebid.name']
        result = super(livebid, self).write(cr, uid, ids, data, context=context) # return Boolean
        row = self.browse(cr, uid, ids)
        name_row_ids = livebid_name_obj.search(cr, uid, [('livebid_id', 'in', ids)])
        name_row = livebid_name_obj.browse(cr, uid, name_row_ids)
        # if no livebid_name & islive is True,
        # create a new thread, update livebid with a livebid_name
        if not name_row:
            if 'power_switch' in data:
                if data['power_switch'] == 'on':
                    _logger.info("Creating new livebid %r" % (ids))
                    livebid_name_obj.create(cr, uid, {'name': row.name, 'livebid_id': ids[0]})
                    record = self.browse(cr, uid, ids)
                    autobids = []
                    if record.autobids:
                        for autobid in autobids:
                            autobids.append(autobid.livebid_id)

                    values = {
                        'livebid_id': record.id,
                        'name': record.name,
                        'status': record.status,
                        'bidpacks_qty': record.bidpacks_qty,
                        'product_id': record.product_id.id,
                        'start_time': record.start_time,
                        'raiser': record.raiser,
                        'end_time': record.end_time,
                        'autobids': autobids,
                        'islive': record.islive,
                        'heartbeat': record.heartbeat,
                        'wonby': record.wonby.id,
                        'power_switch': record.power_switch,
                        'countdown': record.countdown,
                        'binding_key': 'new'
                    }

                    #launcher.start(values)
                    qparams = {
                        'exchange': 'livebid',
                        'routing_key': 'new',
                        'type': 'direct',
                    }
                    produce(values, **qparams)

        #elif name_row.name and row.power_switch == 'on':
            #record = self.browse(cr, uid, ids)
            #autobids = []
            #if record.autobids:
                #for autobid in autobids:
                    #autobids.append(autobid.livebid_id)

            #values = {
                #'livebid_id': record.id,
                #'name': record.name,
                #'status': record.status,
                #'bidpacks_qty': record.bidpacks_qty,
                #'product_id': record.product_id.id,
                #'start_time': record.start_time,
                #'raiser': record.raiser,
                #'end_time': record.end_time,
                #'autobids': autobids,
                #'islive': record.islive,
                #'heartbeat': record.heartbeat,
                #'wonby': record.wonby.id,
                #'power_switch': record.power_switch,
                #'countdown': record.countdown,
                #'binding_key': 'new'
            #}
            #_logger.info("VALUES %r" % values)

            #qparams = {
                #'exchange': 'livebid',
                #'routing_key': 'new',
                #'type': 'direct',
            #}
            #produce(values, **qparams)

        elif name_row and name_row.name:
            if 'power_switch' in data:
                if data['power_switch'] in ('stop', 'off'):
                    _logger.info("Stopping livebid %r" % (ids))
                    # notify BidTask of livebid update
                    record = self.browse(cr, uid, ids)

                    values = {
                        'livebid_id': record.id,
                        'name': record.name,
                        'status': record.status,
                        'bidpacks_qty': record.bidpacks_qty,
                        'product_id': record.product_id.id,
                        'start_time': record.start_time,
                        'raiser': record.raiser,
                        'end_time': record.end_time,
                        'islive': record.islive,
                        'heartbeat': record.heartbeat,
                        'wonby': record.wonby.id,
                        'power_switch': record.power_switch,
                        'countdown': record.countdown,
                        'binding_key': 'update'
                    }
                    _logger.info("VALUES %r" % values)

                    #launcher.update(values)
                    qparams = {
                        'exchange': 'livebid',
                        'routing_key': 'update',
                        'type': 'direct',
                    }
                    produce(values, **qparams)
        return result

    def user_can_buy(self, cr, uid):
        """ buy it now price = retail price - auction price """
        # Validate eligibility
        bids_spent_value = 0
        if bids_spent_value < buy_it_now_price:
            return False
        else:
            # proceed
            pass

    def _get_todays_auction(self, cr, uid, context=None):
        livebid_ids = self.search(cr, uid, [('islive', '=', True)], context=context)
        return self.browse(cr, uid, livebid_ids)

    @api.multi
    @api.returns('self')
    def off(self, ids):
        """ Set power_switch to off, remove livebid from cheape_livebid_name """
        #self.write(cr, uid, [ids], {'power_switch': 'stop'})
        #self.pool['cheape_livebid_name'].unlink_record(cr, uid, ids)
        self.write({'power_switch': 'stop'})
        #self.pool['cheape_livebid_name'].unlink_record(cr, SUPERUSER_ID, ids)
        name_obj = self.env['cheape_livebid_name'].search([('livebid_id', '=', ids)])
        name_obj.unlink() if name_obj else None

    def _livebid_by_product(self, cr, uid, product_id):
        record = self.browse(cr, uid, [product_id])
        values = {
            'name': record.name,
            'status': record.status,
            'start_time': record.start_time,
            'end_time': record.end_time,
            'autobids': autobids,
            'islive': record.islive,
            'heartbeat': record.heartbeat,
            'wonby': record.wonby.id,
            'power_switch': record.power_switch,
        }
        return values



class livebid_name(models.Model):
    _name = 'cheape.livebid.name'

    name = fields.Char()
    livebid_id = fields.Many2one('cheape.livebid', string="The livebid", required=True)

    def _generate_livebid_name(self):
        salt = fields.Datetime.now()
        hashids = Hashids(min_length=5, salt=salt)
        return hashids.encode(int(time.time()), random.randint(1, int(time.time())))

    @api.multi
    def unlink_record(self, ids):
        #record = self.browse(cr, uid, ids)
        record = self.browse([ids])
        if ids:
            record.unlink()

class watchlist(models.Model):
    _name = 'cheape.watchlist'

    product_id = fields.Many2one('product.template', string="Product", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)

    def create(self, cr, uid, values, context=None):
        return super(watchlist, self).create(cr, uid, values, context=context)

    def my_watchlist(self, cr, uid, partner_id, context=None):
        return self.browse(cr, uid, [partner_id]).watchlist_ids


class rewards(models.Model):
    """ Definition of available rewards that a user can earn """
    _name = 'cheape.rewards'

    label = fields.Char(string="Label", help="Reward identifier")
    name = fields.Char(string="Goal")
    action = fields.Char(string="Challenge")

    def _get_unearned_rewards(self, cr, uid, rewards, context=None):
        allrewards = self.browse(cr, uid, [], context=context)
        # Only rewards unearned by user
        return allrewards.filtered(lambda r: r.name not in rewards)

    def _get_reward(self, cr, uid, action, context=None):
        ids = self.search(cr, uid, [('action', '=', action)], context=context)
        rewards = self.browse(cr, uid, ids, context=context)
        #return rewards.filtered(lambda r: r.action == action)
        return rewards


class reward(models.Model):
    _name = 'cheape.reward'

    name = fields.Char(string="Goal", help="Reward earned by customer")
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)
    action = fields.Char(string="Challenge", help="Action or Challenge performed by user")

    def create(self, cr, uid, params, context=None):
        """ Assign reward to partner """
        login = params.get('login')
        values = params.copy()
        # Get user by login
        userid = self.pool['res.users'].search(cr, uid, [('login', '=', login)], context=context)
        user = self.pool['res.users'].browse(cr, uid, userid, context=context)
        partner_id = user.partner_id.id
        values['partner_id'] = partner_id
        del values['login']
        #return self.write(cr, uid, [partner_id], values, context=context)
        return super(reward, self).create(cr, uid, values, context=context)

    def partner_rewards(self, cr, uid, partner_id, context=None):
        """ Get user earned rewards """
        return self.browse(cr, uid, [partner_id], context=context)


class autobid(models.Model):
    """
    conf = {'uid': 3, livebid_id: 4, num_of_bids: 1000, display_name: ''} """
    _name = 'cheape.autobid'

    livebid_id = fields.Many2one('cheape.livebid', string="The livebid", required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    #conf = fields.Char(string="Autobid config", help="The autobid config")
    num_of_bids = fields.Integer(help="", default=0)
    display_name = fields.Char()

    def roll(self, cr, uid, data, context=None):
        lid, pid = data.get('livebid_id'), data.get('partner_id')
        del data['binding_key']
        vals = data.copy()
        ids = self.search(cr, uid, [('livebid_id', '=', lid), ('partner_id', '=', pid)])
        if ids:
            autobids = self.browse(cr, uid, ids)
            nob = sum([autobids.num_of_bids, data['num_of_bids']])
            vals['num_of_bids'] = nob
            record = self.write(cr, uid, ids,  vals)
            vals['binding_key'] = 'autobid_reply'
            _publish_autobids(vals)
        else:
            record = super(autobid, self).create(cr, uid, data, context=context)
            vals['binding_key'] = 'autobid_reply'
            _publish_autobids(vals)
        return record

    def complete_autobid(self, cr, uid, data):
        """ Update num_of_bids after a successful completion of a round of autobids """
        lid, pid = data.get('livebid_id'), data.get('partner_id')
        ids = self.search(cr, uid, [('livebid_id', '=', lid), ('partner_id', '=', pid)])
        if ids:
            self.write(cr, uid, ids, {'num_of_bids': 0})

    #def write(self, cr, uid, ids, data, context=None):
        #result = super(autobid, self).write(cr, uid, ids, data, context=context) # return Boolean
        #publish()

class C(ConsumerMixin):

    def __init__(self, connection):
        self.connection = connection

    def get_consumers(self, Consumer, channel):
        exchange = Exchange('socketio_forwarder', type='direct', durable=True)
        livebid_ex = Exchange('livebid', type='direct', durable=True)
        queue = Queue('', exchange, routing_key='forwarder')
        cleanup_q = Queue('', livebid_ex, routing_key='cleanup')
        return [
            Consumer(queue, callbacks=[self.on_message]),
            Consumer(cleanup_q, callbacks=[self.on_message]),
        ]

    def on_message(self, body, message):
        global registry
        print("RECEIVED BODY: %r" % (body, ))
        data = body
        if data.get('binding_key') == 'livebid':
            # write bet to db
            values = {
                'livebid_id': data.get('livebid_id'),
                'product_id': data.get('product_id'),
                'partner_id': data.get('partner_id'),
            }
            with registry.cursor() as cr:
                registry.get('cheape.bet').livebet(cr, SUPERUSER_ID, values)

        if data.get('binding_key') == 'cleanup':
            with registry.cursor() as cr:
                livebid_id = data.get('livebid_id')
                cr.execute("UPDATE cheape_livebid SET power_switch = 'stop' WHERE id = %s", (livebid_id,))
                cr.execute("DELETE FROM cheape_livebid_name WHERE livebid_id = %s", (livebid_id,))
                cr.commit()

        if data.get('binding_key') == 'autobid':
            with registry.cursor() as cr:
                #registry.get('cheape.autobid').roll(cr, SUPERUSER_ID, data)
                lid, pid = data.get('livebid_id'), data.get('partner_id')
                del data['binding_key']
                vals = data.copy()
                cr.execute("SELECT livebid_id, partner_id, num_of_bids FROM cheape_autobid \
                                 WHERE livebid_id = %s AND partner_id = %s", (lid, pid))
                autobids = cr.dictfetchall()[0]
                if autobids:
                    nob = sum([autobids.get('num_of_bids'), data['num_of_bids']])
                    vals['num_of_bids'] = nob
                    cr.execute("UPDATE cheape_autobid SET num_of_bids = %s \
                               WHERE livebid_id = %s AND partner_id = %s", (vals['num_of_bids'], lid, pid))
                    cr.commit()
                    vals['binding_key'] = 'autobid_reply'
                    _publish_autobids(vals)
                else:
                    cr.execute("INSERT INTO cheape_autobid (livebid_id, partner_id, num_of_bids) \
                               VALUES (%s, %s, %s)", (lid, pid, data.get('num_of_bids')))
                    cr.commit()
                    vals['binding_key'] = 'autobid_reply'
                    _publish_autobids(vals)
        message.ack()


class LiveBid(object):
    def run(self):
        if openerp.evented:
            gevent.spawn(C(connection).run())
        return self

launcher = LiveBid()
launcher.run()
