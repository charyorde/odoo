from kombu import Connection, Exchange, Queue
from kombu.pools import producers
from openerp.addons.website_greenwood.main import Config

config = Config()
amqp_url = config.settings().get('amqpurl')
connection = Connection(amqp_url)

# Cheape Livebid default Queue definition
livebid_exchange = Exchange("livebid", type="direct", durable=True)
autobid_queue = Queue("autobids", livebid_exchange, routing_key='autobids')

def produce(message, **kwargs):
    print("queue message %r" % message)
    exchange = kwargs.get('exchange')
    with producers[connection].acquire(block=True) as producer:
        producer.publish(
            message,
            exchange=Exchange(exchange, type=kwargs['type'], durable=True),
            routing_key=kwargs.get('routing_key'),
            priority=1
        )

def dist_queue(message, **kwargs):
    pass
