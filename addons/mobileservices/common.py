from gcm import *

from openerp.addons.website_greenwood.main import Config

config = Config()

def send_email(user_id, message):
    pass

def send_push_notification(user_id, message):
    gcm = GCM(config.settings()['gcm_'])
    pass

def verify_email(params):
    """ Validates a verification code. Checks whether the code
    matches the user and the device.
    Sends push notification to user device id """
    pass


