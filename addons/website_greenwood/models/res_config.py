import logging
from openerp import models, fields, api

AMQP_URL = "amqp://fwnihdxj:wY5zNSfYpvpI6PeT__g59JpAjPlIZGSZ@elephant.rmq.cloudamqp.com/fwnihdxj"
SWIFT_TOKEN = "AUTH_tk0f21e7a5bef445e99b7eb275b836ea7a"
SWIFT_STORAGE_URL = "http://192.168.2.249:8080/v1/AUTH_admin"
SOCKET_SERVER_HOST = "sios.cfapps.io"
_logger = logging.getLogger(__name__)


class greenwood_config_settings(models.Model):
    _name = 'greenwood.config.settings'
    _inherit = 'res.config.settings'

    amqpurl = fields.Char(string="AMQP URL", default=AMQP_URL)
    swift_token = fields.Char(string="Swift token", default="")
    swift_storageurl = fields.Char(string="Swift Storage URL", default=SWIFT_STORAGE_URL, help="Swift Storage URL")
    gcm_sender_id = fields.Char(string="GCM sender key", default="", help="Google Cloud Messaging sender id")
    gcm_apikey = fields.Char(string="GCM api key", default="", help="Google Cloud Messaging api key")
    sio_server_host = fields.Char(string="Socket server host", default=SOCKET_SERVER_HOST)
    sio_server_port = fields.Char(string="Socket server port", default=80)

    @api.returns('self')
    def get_config(self):
        _logger.info("Greenwood Config: AMQPURL %r" % {'amqpurl': self.amqpurl})
        return self
