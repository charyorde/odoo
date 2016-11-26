import logging
import copy
import ast
import select
import simplejson
import json

import gevent
from gevent import Greenlet, getcurrent
#from gevent import select
from gevent.local import local
#from threading import current_thread
from gevent.event import AsyncResult

import openerp
from openerp import SUPERUSER_ID
from openerp.addons.website_greenwood.main import Config

import kombu
from kombu.mixins import ConsumerMixin
from kombu import Connection, Exchange, Consumer, Queue

from socketIO_client import SocketIO, BaseNamespace
promise = AsyncResult()

logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
config = Config()
settings = config.settings()

db_name = openerp.tools.config['db_name']

connection = Connection(settings.get('amqpurl'))


_logger = logging.getLogger(__name__)

def socket_session_token():
    registry = openerp.modules.registry.Registry(db_name)
    with registry.cursor() as cr:
        cr.execute("SELECT session_token FROM res_users WHERE login = %s", ('system@greenwood.ng',))
        return cr.fetchall()[0]

session_token = socket_session_token()

class Namespace(BaseNamespace):
    def on_connect(self):
        self.emit('authenticate', {
            'uid': 37,
            'email': 'system@greenwood.ng',
            'session_token': session_token
        })

#sio = SocketIO(
    #settings.get('sio_server_host'),
    #settings.get('sio_server_port'), Namespace,
    #params={'sessionid': session_token},
    #cookies={'JSESSIONID': session_token[0]}
#)

class BidTask(Greenlet):
    def __init__(self, bid):
        Greenlet.__init__(self)
        self.bid = bid

    def __call__(self):
        Greenlet.__init__(self, run=self.task())

    def task(self):
        _logger.info("BidTask.task listen livebet on db postgres")

        global promise

        livebid_id = local()
        livebid_id = self.bid.get('livebid_id')

        t = local()
        t = self.bid.get('countdown')
        countdown_range = ['00:00:10', '00:00:09', '00:00:08', '00:00:07', '00:00:06', '00:00:05', '00:00:04', '00:00:03', '00:00:02', '00:00:01', '00:00:00']
        with openerp.sql_db.db_connect('postgres').cursor() as cr:
            # Retrieve the connection
            conn = cr._cnx
            cr.execute("listen livebet;")
            cr.commit()
            while t:
                # Handle thread updates
                data = promise.value
                print("data %r", [data])
                if data:
                    if data.get('livebid_id') == livebid_id:
                        if data.get('power_switch') == 'stop':
                            print("Stopping livebid %r" % livebid_id)
                            # Clear the value
                            promise.set()
                            #Greenlet.kill(getcurrent(), timeout=5)
                            self.stop(data)

                # @todo Only begin when countdown is 00:00:10
                mins, secs = divmod(t, 60)
                hours, mins = divmod(mins, 60)
                timeformat = '{:02.0f}:{:02.0f}:{:02.0f}'.format(hours, mins, secs)

                _logger.info("Running %r" % [self.bid, id(getcurrent()), timeformat])
                self.countdown({'livebid_id': self.bid.get('id'), 'countdown': timeformat})

                res = select.select([], [], [], 1)
                if res == ([],[],[]):
                    pass
                else:
                    # handle bets in a countdown
                    conn.poll()
                    while conn.notifies and timeformat in countdown_range:
                        data = simplejson.loads(conn.notifies.pop().payload)
                        if data and timeformat != '00:00:00':
                            _logger.info("livebet items %r" % data)
                            # notify of the new bet
                            # new_bid('', data)
                        else:
                            _logger.info("No new bet. livebet timeout. We have a winner")
                            # @todo Before killing put the thread in an idle state for x
                            # timeout waiting.
                            #def shutdown():
                                #gevent.kill(self)
                            #gevent.with_timeout(8, shutdown)
                            Greenlet.kill(getcurrent(), timeout=8)
                            #gevent.sleep(1)
                            #t -= 1

                #if timeformat in countdown_range:
                    # act on notifications received
                    # if countdown == 3, foreach user's in livebid.autobidconf,
                    # publish a bet
                    #_logger.info("livebet items %r" % res)
                    #t = 10
                    #break
                if timeformat not in countdown_range:
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


    def new_bid(self, message):
        launcher.sio.emit('')

    def countdown(self, message):
        launcher.sio.emit('countdown', message)

    def autobid(self):
        launcher.sio.emit('livebet', {})

    def stop(self, data):
        #launcher.sio.emit('stop', data)
        # remove greenlet name from livebid_name
        registry = openerp.modules.registry.RegistryManager.get(db_name)
        with registry.cursor() as cr:
            #registry['cheape_livebid_name'].unlink_record(cr, SUPERUSER_ID, data.get('livebid_id'))
            #registry['cheape.livebid'].off(cr, SUPERUSER_ID, data.get('livebid_id'))
            # @todo should update countdown with the latest value
            #cr.commit()
            Greenlet.kill(getcurrent(), timeout=2)


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
        self.task()

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

        with connection as conn:
            with consumer:
                conn.drain_events()

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
        print("RECEIVED BODY: %r" % (body, ))
        print("RECEIVED MESSAGE: %r" % (message, ))
        #registry = openerp.modules.registry.Registry(db_name)
        registry = openerp.modules.registry.RegistryManager.get(db_name)
        data = body
        if data.get('binding_key') == 'livebid':
            # write bet to db
            d = data.get('d')
            values = {
                'livebid_id': data.get('livebid_id'),
                'product_id': data.get('product_id'),
                'partner_id': data.get('partner_id'),
            }
            registry['cheape.bet'].livebet(registry.cursor(), SUPERUSER_ID, values)
            #try:
                #with registry.cursor() as cr:
                    #registry.get('cheape.bet').create(cr, SUPERUSER_ID, values)
            #except:
            #    pass
        if data.get('binding_key') == 'cleanup':
            with registry.cursor() as cr:
                livebid_id = data.get('livebid_id')
                #registry.get('cheape.livebid').off(registry.cursor(), SUPERUSER_ID, livebid_id)
                cr.execute("DELETE FROM cheape_livebid_name WHERE livebid_id = %s", (livebid_id,))
                cr.commit()
        message.ack()

# Autobid
# For each autobid conf in the db, spin up a new thread
# if autobid.livebid.status == open, place a bet
from collections import namedtuple
class LiveBid(object):
    def __init__(self):
        self.sio = SocketIO(
            settings.get('sio_server_host'),
            settings.get('sio_server_port'), Namespace,
            params={'sessionid': session_token},
            cookies={'JSESSIONID': session_token[0]}
        )

    def start(self, data):
        if openerp.evented:
            gevent.spawn(BidTask(data))
        return self

    def resume(self, dbname):
        """ Database resume of livebids if the server is shutdown """
        registry = openerp.registry(dbname)
        with registry.cursor() as cr:
            try:
                LiveBidRecord = namedtuple('LiveBidRecord',
                                           'id, bidpacks_qty, status, end_time, product_id, amount_totalbids, wonby, start_time, countdown, heartbeat, power_switch, totalbids')
                cr.execute('SELECT id, bidpacks_qty, status, end_time, product_id, amount_totalbids, wonby, start_time, countdown, heartbeat, power_switch, totalbids'\
                           ' FROM cheape_livebid WHERE power_switch = %s', ('on',))
                #_logger.info("FETCHED DATA %r" % cr.fetchall())
                g = [gevent.spawn(BidTask(dict(livebid._asdict()))) or [] for livebid in map(LiveBidRecord._make, cr.fetchall())]
                _logger.info("Resumed livebids %r" % g)
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
                            g = [gevent.spawn(BidTask(livebid_record))]
                            #g = gevent.spawn(BidTask(livebid_record))
                            _logger.info("Today's livebid %r" % g)
                            gevent.joinall(g) if g else None
                            #g.start()
                            #g.join()
                        except Exception as e:
                            _logger.info("Failed to load today's auction %r" % e)

    def update(self, data):
        global promise
        promise.set(data)

    def run(self):
        if openerp.evented:
            #gevent.spawn(self.resume(db_name))
            #gevent.spawn(self.listen(db_name))
            #gevent.spawn(self._update_listener())
            #gevent.spawn(consume) # use start() instead so that it runs on the main thread
            gevent.spawn(C(connection).run())
        return self

launcher = LiveBid()
launcher.run()

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
