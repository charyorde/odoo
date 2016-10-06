# -*- coding: utf-8 -*-
import logging
import simplejson
import math
from datetime import timedelta
import random
import time

import openerp
from openerp import models, fields, api
from openerp import SUPERUSER_ID

from hashids import Hashids

_logger = logging.getLogger(__name__)

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


class cheape_account(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    #partner_id = fields.Many2one('res.partner', string='Partner', required=True, readonly=True)
    #bidswon = fields.One2many('cheape.livebid', 'wonby', help="A list of live bids won by the current user")
    bidswon = fields.Many2many('cheape.livebid', compute='_my_bidswon', store=False, readonly=True, help="A list of live bids won by the current user")
    bidscount = fields.Integer(string="My bids", default=0, required=True, help="Total number of a user's purchased bids")
    # A list of the current user's watchlist
    #watchlist_ids = fields.One2many('cheape.watchlist', 'partner_id', help="A list of the current user's watchlist")
    watchlist_ids = fields.Many2many('cheape.watchlist', compute='_my_watchlist', store=False, readonly=True, help="A list of the current user's watchlist")

    def reduce_bidpacks(self, cr, uid, partner_id, qty, context=None):
        """ Reduce user's bidpacks by x amount """
        cheape_account = self.browse(cr, uid, [partner_id], context=context)
        bidscount = reduce(lambda x, y: x-y, [cheape_account.bidscount, qty])
        self.write(cr, uid, [cheape_account.id], {'bidscount': bidscount})
        return bidscount

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


class bet(models.Model):
    """ A cheape bet """
    _name = 'cheape.bet'

    livebid_id = fields.Many2one('cheape.livebid', string="The livebid", readonly=True)
    product_id = fields.Many2one('product.template', string="Product", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)
    #livebid_identity = fields.Integer(string="The Greenlet id", required=True, default=0, index=True)

    def bet(self, cr, uid, values):
        record = self.create(cr, uid, values)
        # Update product_template. with new bidprice
        # reset livebid.countdown and publish message back to client
        return record

    def livebet(self, cr, uid, values, context=None):
        partner_obj = self.pool['res.partner']
        product_obj = self.pool['product.template']
        livebid_obj = self.pool['cheape.livebid']
        cheape_account_obj = self.pool['res.partner']
        partner_id = values['partner_id']
        product = product_obj.browse(cr, uid, values['product_id'])
        livebid = self.pool['cheape.livebid'].browse(cr, uid, values['livebid_id'])
        partner = partner_obj.browse(cr, uid, values['partner_id'])

        record = self.create(cr, uid, values)
        # Increment totalbids spent on this livebid
        totalbids = sum(livebid.totalbids + 1)
        livebid_obj.write(cr, uid, [values['livebid_id']], {'totalbids': totalbids}, context=context)
        # @todo publish totalbids for autobot to act upon
        cr.commit()
        with openerp.sql_db.db_connect('postgres').cursor() as cr2:
            cr2.execute("notify livebet, %s", (json_dump(values),))
        # Update product_template with new bidprice
        product_obj.write(cr, uid, values['product_id'], {'bid_total': math.fsum([product.bid_total, livebid.raiser])})
        # Reduce user's bidpacks by livebid.bidpacks_qty
        bidpacks_left = cheape_account_obj.reduce_bidpacks(cr, uid, partner_id, livebid.bidpacks_qty)
        # reset livebid.countdown and publish message back to client
        # return payload [bidpacks_left, bid_total]
        return record


class livebid(models.Model):
    """ A live auction """
    _name = 'cheape.livebid'

    name = fields.Char(help="A unique livebid name")
    product_id = fields.Many2one('product.template', string="Product", required=True)
    power_switch = fields.Selection(
        [('start', 'Start'),('stop', 'Stop')], string="Power Switch", help="Switch the state of a livebid")
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
    active = fields.Boolean(help="An active livebid is one with a countdown")
    raiser = fields.Float(default=float(0.01), help="The value in which bets on this livebid increments by")
    bidpacks_qty = fields.Integer(string="Bidpacks per bid", default=1, help="The quantity of bidpacks per bid required on this livebid")
    autobids = fields.One2many('cheape.autobid', 'livebid_id', help="A list of autobids on this livebid")
    totalbids = fields.Integer(string="Total bids", help="The total bids placed since live bid begun")

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
        islive = params.get('islive')
        if islive:
            livebid_name = livebid_name_obj._generate_livebid_name()
            params['name'] = livebid_name
        record = super(livebid, self).create(cr, uid, params, context=context)

        # create livebid_name only when islive is True
        if islive:
            livebid_name_obj.create(cr, uid, {'name': livebid_name, 'livebid_id':record}, context=context)

        livebid_name_ids = livebid_name_obj.search(cr, uid, [])
        _logger.info("livebid_name_ids %r" % livebid_name_ids)
        livebid_names = livebid_name_obj.browse(cr, uid, livebid_name_ids, context=context)
        names = [name.name for name in livebid_names]
        _logger.info("livebid_names %r" % names)

        with openerp.sql_db.db_connect('postgres').cursor() as cr2:
            #cr2.execute("notify cheape_livebid, %s", (json_dump(params),))
            if islive:
                cr2.execute("notify cheape_livebid, %s", (simplejson.dumps(params),))
        return record

    def write(self, cr, uid, ids, data, context=None):
        _logger.info("livebid update %r" % data)
        livebid_obj = self.pool['cheape.livebid']
        livebid_name_obj = self.pool['cheape.livebid.name']
        result = super(livebid, self).write(cr, uid, ids, data, context=context) # return Boolean
        row = self.browse(cr, uid, ids)
        # if no livebid_name & islive is True,
        # create a new thread, update livebid with a livebid_name
        if not row.name and row.islive:
            livebid_name = livebid_name_obj._generate_livebid_name()
            livebid_obj.write(cr, uid, ids, {'name': livebid_name})
            record = self.browse(cr, uid, ids)
            autobids = []
            if record.autobids:
                for autobid in autobids:
                    autobids.append(autobid.livebid_id)

            values = {
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
            }

            with openerp.sql_db.db_connect('postgres').cursor() as cr2:
                cr2.execute("notify cheape_livebid, %s", (simplejson.dumps(record),))
        elif row.name and row.islive:
            # notify BidTask of livebid update
            record = self.browse(cr, uid, ids)
            autobids = []
            if record.autobids:
                for autobid in autobids:
                    autobids.append(autobid.livebid_id)

            values = {
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
            }
            _logger.info("VALUES %r" % values)
            with openerp.sql_db.db_connect('postgres').cursor() as cr2:
                cr2.execute("notify livebid_update, %s", (simplejson.dumps(record),))

        return result

    def _get_todays_auction(self, cr, uid, context=None):
        livebid_ids = self.search(cr, uid, [('islive', '=', True)], context=context)
        return self.browse(cr, uid, livebid_ids)

    def off(self, cr, uid, ids):
        self.write(cr, uid, ids, {'islive': False})


class livebid_name(models.Model):
    _name = 'cheape.livebid.name'

    name = fields.Char()
    livebid_id = fields.Many2one('cheape.livebid', string="The livebid", required=True)

    def _generate_livebid_name(self):
        salt = fields.Datetime.now()
        hashids = Hashids(min_length=5, salt=salt)
        return hashids.encode(int(time.time()), random.randint(1, int(time.time())))


class watchlist(models.Model):
    _name = 'cheape.watchlist'

    product_id = fields.Many2one('product.template', string="Product", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)

class rewards(models.Model):
    """ Definition of available rewards that a user can earn """
    _name = 'cheape.rewards'

    name = fields.Char(string="Goal")
    action = fields.Char(string="Challenge")

    def _get_unearned_rewards(self, cr, uid, rewards, context=None):
        allrewards = self.browse(cr, uid, [], context=context)
        # Only rewards unearned by user
        return allrewards.filtered(lambda r: r.name not in rewards)

class reward(models.Model):
    _name = 'cheape.reward'

    name = fields.Char(string="Goal", help="Reward earned by customer")
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)
    action = fields.Char(string="Challenge", help="Action or Challenge performed by user")

    def unlock_reward(self, cr, uid, params, context=None):
        """ Assign reward to partner """
        login = params.get('login')
        values = params.copy()
        # Get user by login
        userid = self.pool['res.users'].search(cr, uid, [('login', '=', login)], context=context)
        user = self.pool['res.users'].browse(cr, uid, userid, context=context)
        values['partner_id'] = user.partner_id.id
        del values['login']
        return self.write(cr, uid, values, context=context)

    def partner_rewards(self, cr, uid, partner_id, context=None):
        """ Get user earned rewards """
        return self.browse(cr, uid, [partner_id], context=context)


class autobid(models.Model):
    """
    conf = {'uid': 3, livebid_id: 4, num_of_bids: 1000, display_name: ''} """
    _name = 'cheape.autobid'

    livebid_id = fields.Many2one('cheape.livebid', string="The livebid", required=True)
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    #conf = fields.Char(string="Autobid config", help="The autobid config")
    num_of_bids = fields.Integer(help="")
    display_name = fields.Char()
