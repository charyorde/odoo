from kombu import Connection, Exchange
from kombu.pools import producers
from openerp.addons.website_greenwood.main import Config

config = Config()
amqp_url = config.settings().get('amqpurl')
connection = Connection(amqp_url)


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
