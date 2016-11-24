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
#from openerp.addons.cheape.livebid import launcher
from openerp.addons.mobileservices.queue import produce

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

    livebid_id = fields.Many2one('cheape.livebid', string="The livebid", readonly=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.template', string="Product", readonly=True, index=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True, index=True)
    bids_spent = fields.Integer(help="A count of bids spent by this user", default=0)
    bids_spent_value = fields.Float(compute='_compute_bids_spent_value', store=True, help="The sum of total bids placed by user on a specific livebid")
    buy_it_now_price = fields.Float(compute='_compute_buy_it_now_price', store=True)

    def bet(self, cr, uid, data, context=None):
        """ Non-livebid bet """
        product_obj = self.pool['product.template']
        livebid = self.pool['cheape_livebid'].browse(cr, uid, [data.get('livebid_id')])
        product = livebid.product_id
        partner = data.get('partner_id')
        bid_ids = self.search(cr, uid, [('partner_id', '=', data['partner_id'])])
        userbet = self.browse(cr, uid, bid_ids, context=None)
        values = data.copy()
        if bid_ids:
            # Update
            val = [userbet.bids_spent, DEFAULT_BIDS_SPENT]
            values['bids_spent'] = math.sum(val)
            record = self.write(cr, uid, [partner], values)
        else:
            values['bids_spent'] = DEFAULT_BIDS_SPENT
            record = self.create(cr, uid, values)
        # Update product_template. with new bidprice
        product_obj.write(cr, uid, values['product_id'], {'bid_total': math.fsum([product.bid_total, livebid.raiser])})
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
        totalbids = livebid.totalbids + 1
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

    def _compute_bet(self, cr, uid, partner_id, context=None):
        """ Compute total bids on a livebid per user """
        # A list of all bets by this user on this livebid
        # math.fsum(values)
        pass

    @api.multi
    @api.depends('bids_spent_value', 'livebid_id')
    def _compute_buy_it_now_price(self):
        # Retail price - bids_spent_value
        # self = self.with_context(self.env['res.users'].context_get())
        livebid = self.env['cheape.livebid'].browse([self.livebid_id])
        retail_price = livebid.product_id.price
        return reduce(lambda x, y: x-y, [retail_price, self.bids_spent_value])

    @api.multi
    @api.depends('bids_spent', 'livebid_id')
    def _compute_bids_spent_value(self):
        livebid = self.env['cheape.livebid'].browse([self.livebid_id])
        return self.bids_spent * livebid.bid_cost


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
        # if no livebid_name & islive is True,
        # create a new thread, update livebid with a livebid_name
        if not row.name and row.power_switch == 'on':
            livebid_name = livebid_name_obj._generate_livebid_name()
            livebid_obj.write(cr, uid, ids, {'name': livebid_name})
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
                'countdown': record.countdown
            }

            #launcher.start(values)
            qparams = {
                'exchange': 'livebid',
                'routing_key': 'new',
                'type': 'direct',
            }
            produce(values, **qparams)

        elif row.name and row.power_switch == 'on':
            # notify BidTask of livebid update
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
            _logger.info("VALUES %r" % values)

            #launcher.start(values)
            qparams = {
                'exchange': 'livebid',
                'routing_key': 'new',
                'type': 'direct',
            }
            produce(values, **qparams)

        elif row.name and row.power_switch in ('stop', 'off'):
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

    def off(self, cr, uid, ids):
        """ Set power_switch to off, remove livebid from cheape_livebid_name """
        self.write(cr, uid, ids, {'power_switch': 'off'})
        self.pool['cheape_livebid_name'].unlink_record(cr, SUPERUSER_ID, ids)

    def _livebid_by_product(cr, uid, product_id):
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

    def machina_bid(self, cr, uid, data):
        livebet_obj = self.pool['cheape.bet']
        # partners in group machinas
        machinas = None
        # Random selection of a machina
        machina = None
        lb_id = data.get('livebid_id')
        record = self.browse(cr, uid, [lb_id])
        # @todo Test for required total players
        current_auction_price = record.product_id.bid_total
        if current_auction_price < record.product_id.max_bid_total:
            values = {}
            livebet_obj.livebet(cr, uid, values)


class livebid_name(models.Model):
    _name = 'cheape.livebid.name'

    name = fields.Char()
    livebid_id = fields.Many2one('cheape.livebid', string="The livebid", required=True)

    def _generate_livebid_name(self):
        salt = fields.Datetime.now()
        hashids = Hashids(min_length=5, salt=salt)
        return hashids.encode(int(time.time()), random.randint(1, int(time.time())))

    def unlink_record(self, cr, uid, ids):
        record = self.browse(cr, uid, ids)
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
    num_of_bids = fields.Integer(help="")
    display_name = fields.Char()
