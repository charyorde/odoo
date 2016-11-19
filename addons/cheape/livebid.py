import logging
import copy
import ast
import select
import simplejson

import gevent
from gevent import Greenlet
from gevent import getcurrent
#from gevent import select
from gevent.local import local
#from threading import current_thread

import openerp
from openerp import SUPERUSER_ID
from openerp.addons.website_greenwood.main import Config

import kombu
from kombu.mixins import ConsumerMixin
from kombu import Connection, Exchange, Consumer, Queue

from socketIO_client import SocketIO, LoggingNamespace
logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
config = Config()
settings = config.settings()

connection = Connection(settings.get('amqpurl'))


_logger = logging.getLogger(__name__)


class BidTask(Greenlet):
    def __init__(self, bid):
        #Greenlet.__init__(self)
        self.bid = bid

    def __call__(self):
        Greenlet.__init__(self, run=self.task(id(getcurrent())))

    def _update_listener(self):
        with openerp.sql_db.db_connect('postgres').cursor() as cr:
            conn = cr._cnx
            cr.execute("LISTEN livebid_update;")
            cr.commit();
            while True:
                if select.select([conn], [], [], 1) == ([],[],[]):
                    pass
                else:
                    conn.poll()
                    while conn.notifies:
                        #_logger.info("LIVEBID UPDATE RECEIVED: %r" % simplejson.loads(conn.notifies.pop().payload))
                        data = simplejson.loads(conn.notifies.pop().payload)
                        if data.get('auction_name') == self.bid.get('auction_name'):
                            _logger.info("LIVEBID UPDATE RECEIVED: %r" % data)
                            if data.get('power_switch') and data.get('power_switch') == 'stop':
                                gevent.kill(self)
                            self.bid = data
                break

    def task(self, current_livebid):
        _logger.info("BidTask.task listen livebet on db postgres")
        t = local()
        t = self.bid.get('countdown')
        countdown_range = ['00:00:10', '00:00:09', '00:00:08', '00:00:07', '00:00:06', '00:00:05', '00:00:04', '00:00:03', '00:00:02', '00:00:01', '00:00:00']
        with openerp.sql_db.db_connect('postgres').cursor() as cr:
            self._update_listener()
            # Retrieve the connection
            conn = cr._cnx
            cr.execute("listen livebet")
            cr.commit()
            while t:
                # @todo Only begin when countdown is 00:00:10
                mins, secs = divmod(t, 60)
                hours, mins = divmod(mins, 60)
                timeformat = '{:02.0f}:{:02.0f}:{:02.0f}'.format(hours, mins, secs)

                _logger.info("Running %r" % [self.bid, id(getcurrent()), timeformat])
                self.publish({'livebid_id': 5, 'countdown': timeformat})

                res = select.select([], [], [], 1)
                if timeformat in countdown_range and res != ([], [], []):
                    # act on notifications received
                    # if countdown == 3, foreach user's in livebid.autobidconf,
                    # publish a bet
                    # if not res and id(getcurrent()) == current_livebid
                    #publish({'message': {'livebid_id': 5, 'countdown': n}})
                    _logger.info("livebet items %r" % res)
                    t = 10
                    break
                else:
                    _logger.info("No new bet. livebet timeout. We have a winner")
                    # @todo Before killing put the thread in an idle state for x
                    # timeout waiting. conn.poll() and return to countdown
                    # if there's a bet
                    gevent.sleep(1)
                    #gevent.kill(self)
                    t -= 1
                    # Turnoff this livebid. livebid.off
                    # registry['cheape.livebid'].off(registry.cursor(),
                    # SUPERUSER_ID, bid.id)

    def publish(self, message):
        with SocketIO(settings.get('sio_server_host'), settings.get('sio_server_port'), LoggingNamespace) as socketIO:
            socketIO.emit('countdown', message)

    def autobid(self):
        with SocketIO(settings.get('sio_server_host'), settings.get('sio_server_port'), LoggingNamespace) as socketIO:
            # select user using random selection
            socketIO.emit('livebet', {})

    @staticmethod
    def keepalive(self):
        """ Our keepalive poller """
        # For all the current livebids (islive), publish a bet, every
        # 15 mins
        _logger.info("Keeping alive livebids...")
        dbname = openerp.tools.config['db_name']
        registry = openerp.registry(dbname)
        with registry.cursor() as cr:
            cr.execute('SELECT * FROM cheape_livebid WHERE islive is True')
            with SocketIO(settings.get('sio_server_host'), settings.get('sio_server_port'), LoggingNamespace) as socketIO:
                while True:
                    for livebid in dict(cr.fetchall()):
                        if livebid:
                            # select a random partner_id with group
                            # cheape_bot_user
                            socketIO.emit('livebet', {
                                'd': dbname,
                                'livebid_id': livebid.id,
                                'partner_id': livebid.partner_id,
                                'product_id': livebid.product_id
                            })
                            gevent.sleep(3)
                    gevent.sleep(900)

    def _run(self):
        self.task(id(getcurrent()))

def consume():
    while True:
        exchange = Exchange('socketio_forwarder', type='direct', durable=True)
        queue = Queue('', exchange, routing_key='forwarder')
        registry = openerp.registry(openerp.tools.config['db_name'])

        def process_bet(body, message):
            _logger.info("RECEIVED MESSAGE: %r" % (body, ))
            #data = ast.literal_eval(body)
            data = body
            # write bet to db
            d = data.get('d')
            values = {
                'livebid_id': data.get('livebid_id'),
                'product_id': data.get('product_id'),
                'partner_id': data.get('partner_id'),
                #'livebid_identity': body['livebid_identity']
            }
            #registry['cheape.bet'].livebet(registry.cursor(), SUPERUSER_ID, values)
            #with registry.cursor() as cr:
                #registry['cheape.bet'].create(cr, SUPERUSER_ID, values)
            message.ack()

        consumer = Consumer(channel=connection.channel(), queues=queue, accept=['json', 'pickle'], callbacks=[process_bet])
        #consumer = Consumer(connection, queues=queue, callbacks=[process_bet])

        with connection as conn:
            with consumer:
                conn.drain_events()

class C(ConsumerMixin):

    def __init__(self, connection):
        self.connection = connection

    def get_consumers(self, Consumer, channel):
        exchange = Exchange('socketio_forwarder', type='direct', durable=True)
        queue = Queue('', exchange, routing_key='forwarder')
        return [
            Consumer(queue, callbacks=[self.on_message]),
        ]

    def on_message(self, body, message):
        print("RECEIVED MESSAGE: %r" % (body, ))
        #data = ast.literal_eval(body)
        data = body
        # write bet to db
        d = data.get('d')
        values = {
            'livebid_id': data.get('livebid_id'),
            'product_id': data.get('product_id'),
            'partner_id': data.get('partner_id'),
        }
        registry = openerp.registry(d)
        #registry['cheape.bet'].livebet(registry.cursor(), SUPERUSER_ID, values)
        #try:
            #with registry.cursor() as cr:
                #registry['cheape.bet'].create(cr, SUPERUSER_ID, values)
        #except:
        #    pass
        message.ack()

# Autobid
# For each autobid conf in the db, spin up a new thread
# if autobid.livebid.status == open, place a bet
from collections import namedtuple
class LiveBid(object):
    def start(self, dbname):
        registry = openerp.registry(dbname)
        with registry.cursor() as cr:
            try:
                LiveBidRecord = namedtuple('LiveBidRecord', 'id, bidpacks_qty, status, end_time, product_id, amount_totalbids, wonby, start_time, countdown, heartbeat, islive, totalbids')
                cr.execute('SELECT id, bidpacks_qty, status, end_time, product_id, amount_totalbids, wonby, start_time, countdown, heartbeat, islive, totalbids'\
                           ' FROM cheape_livebid WHERE islive is True')
                #cr.execute('SELECT * FROM cheape_livebid WHERE islive is True')
                #_logger.info("FETCHED DATA %r" % cr.fetchall())
                g = [gevent.spawn(BidTask(livebid)) or [] for livebid in map(LiveBidRecord._make, cr.fetchall())]
                #g = [gevent.spawn(BidTask(livebid)) or [] for livebid in cr.fetchall()]
                _logger.info("Today's livebid %r" % g)
                if g:
                    gevent.joinall(g)
            except Exception as e:
                _logger.info("Failed to load today's auction %r" % e)
        return self

    def listen(self, dbname):
        _logger.info("LiveBid.listen listen cheape_livebid on db postgres")
        with openerp.sql_db.db_connect('postgres').cursor() as cr:
            conn = cr._cnx
            cr.execute("LISTEN cheape_livebid;")
            cr.commit();
            while True:
                if select.select([conn], [], [], 1) == ([],[],[]):
                    pass
                else:
                    conn.poll()
                    while conn.notifies:
                        #_logger.info("DB NOTIFICATION RECEIVED: %r" % simplejson.loads(conn.notifies.pop().payload))
                        try:
                            livebid_record = simplejson.loads(conn.notifies.pop().payload)
                            #g = [gevent.spawn(BidTask(livebid_record))]
                            g = gevent.spawn(BidTask(livebid_record))
                            _logger.info("Today's livebid %r" % g)
                            #gevent.joinall(g) if g else None
                            g.start().join()
                        except Exception as e:
                            _logger.info("Failed to load today's auction %r" % e)


db_name = openerp.tools.config['db_name']
if openerp.evented:
    gevent.spawn(LiveBid().listen(db_name))
    gevent.spawn(consume) # use start() instead so that it runs on the main thread
    #gevent.spawn(consume_socket)
    #gevent.spawn(C(connection).run())
    #gevent.spawn(BidTask.keepalive())

class LiveBidManager(object):
    def __init__(self, **kwargs):
        self.livebid = []
        self.machina = kwargs.get('machina')
        if self.machina:
            self.imitate(self.machina)

    def imitate(self, data):
        registry = openerp.registry(db_name)
        livebid = registry.get('cheape.livebid')
        livebid.machina_bid(registry.cr, SUPERUSER_ID, data)

    def add(self, bidtask):
        self.livebid.append(bidtask)

    def joinall(self):
        # for n livebid joinall
        gevent.joinall(self.livebid)

bid_manager = LiveBidManager()


class Controller(openerp.http.Controller):
    @openerp.http.route('/cheape/livebid/create', type="json", auth="public")
    def create(self, **kw):
        pass

    @openerp.http.route('/cheape/bet', type="json", auth="public")
    def bet(self, channel, message):
        """ A bet in a non-livebid """
        pass

    @openerp.http.route('/cheape/livebet', type="json", auth="public")
    def livebet(self, channel, message):
        """ A bet in a livebid """
        pass

    @openerp.http.route('/cheape/poll', type="json", auth="public")
    def poll(self, data):
        # LiveBidManager(machina=machina)
        bid_manager.imitate(data)
