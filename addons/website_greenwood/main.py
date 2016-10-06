import os
import time

from openerp import fields
from cfenv import AppEnv

import swiftclient
SWIFT_GWTEMP_CONTAINER = 'gwtemp'
SWIFT_GW_CONTAINER = 'gw'
SWIFT_WEB_CONTAINER = 'web'
SWIFT_USER_CONTENT_CONTAINER = 'gwusercontent'
SWIFT_PUBLIC_CONTAINER = 'public'


class Config():
    def __init__(self):
        #self.env = dict(name='local',
                        #swift_token='AUTH_tk0f21e7a5bef445e99b7eb275b836ea7a',
                        #swift_storageurl='http://192.168.2.249:8080/v1/AUTH_admin')
        self.env = dict()
        self.appenv = AppEnv()

    def _env(self):
        env = self.env
        if os.environ.get('PLATFORM'):
            env = dict(name='PROD', swift_token='')
        elif os.environ.get('CLOUD'):
            env = dict(name='CLOUD',
                       swift_token='AUTH_tk0f21e7a5bef445e99b7eb275b836ea7a',
                       swift_storageurl='http://192.168.2.249:8080/v1/AUTH_admin',
                       gcm_sender_id='',
                       gcm_apikey='',
                       amqpurl='amqp://test:Wordpass15@192.168.10.29:5672/',
                       sio_server_host='sios.apps.greenwood.ng',
                       sio_server_port=80,
                       )
        elif os.environ.get('DEV'):
            env = dict(name='dev', swift_token='')
        elif os.environ.get('DEV_STAGING'):
            env = dict(name='staging',
                       swift_token='AUTH_tk0f21e7a5bef445e99b7eb275b836ea7a',
                       swift_storageurl='http://192.168.2.249:8080/v1/AUTH_admin',
                       gcm_sender_id='',
                       gcm_apikey='',
                       amqpurl='amqp://test:Wordpass15@192.168.10.29:5672/',
                       sio_server_host='sios.apps.yookore.net',
                       sio_server_port=80,
                       )
        else:
            env = dict(name='local',
                       swift_token='AUTH_tk0f21e7a5bef445e99b7eb275b836ea7a',
                       swift_storageurl='http://192.168.2.249:8080/v1/AUTH_admin',
                       gcm_sender_id='',
                       gcm_apikey='',
                       amqpurl='amqp://guest:guest@localhost:5672/',
                       sio_server_host='0.0.0.0',
                       sio_server_port=5000,
                       )
        return env

    def settings(self):
        env = self._env()
        # swift = self.swift()
        if env['name'] != 'local':
            env.update({
                'backend_host': 'https://www.greenwood.ng',
                'mobile_virtual_host': 'https://www.greenwood.ng',
            })
            return env
        else:
            env.update({
                'backend_host': 'https://odoo',
                'mobile_virtual_host': 'https://192.168.56.1',
            })
            return env

    def swift(self):
        env = self._env()
        #swift = self.appenv.get_service('swift')
        #scred = swift.credentials
        if env['name'] != 'local':
            #params = {
                #'username': scred['username'],
                #'password': scred['password'],
                #'authurl': scred['authurl'],
                #'preauthurl': scred['preauthurl'],
                #'preauthtoken': scred['preauthtoken'],
            #}
            #return self._swift_instance(params)
            # Using swift local for now
            return self._swift_local()
        else:
            return self._swift_local()

    def _swift_local(self):
        username = 'admin'
        password = 'admin'
        authurl = 'http://192.168.2.249:8080/auth/v1.0/'
        preauthurl = 'http://192.168.2.249:8080/v1/AUTH_admin'
        preauthtoken = self.env['swift_token']

        swift = swiftclient.client.Connection(user=username,
                                              key=password,
                                              authurl=authurl,
                                              preauthurl=preauthurl,
                                              preauthtoken=preauthtoken,
                                              retries=3)
        return swift

    def _swift_instance(self, params):
        swift = swiftclient.client.Connection(user=params['username'],
                                              key=params['password'],
                                              authurl=params['authurl'],
                                              preauthurl=params['preauthurl'],
                                              preauthtoken=params['preauthtoken'],
                                              retries=3)
        return swift

    def _swift_auth_token(self):
        env = self._env()
        if env['name'] != 'local':
            pass
        else:
            return env['swift_token']


    def _get_swift_storageurl(self):
        env = self._env()
        if env['name'] != 'local':
            pass
        else:
            return env['swift_storageurl']

    def get_swift_param(self, *arg):
        param = dict()
        if 'storageurl' in arg:
            param['storageurl'] = self._get_swift_storageurl()
        if 'tempcontainer' in arg:
            param['gwtempcontainer'] = SWIFT_GWTEMP_CONTAINER
        if 'gwcontainer' in arg:
            param['gwcontainer'] = SWIFT_GW_CONTAINER
        if 'token' in arg:
            param['token'] = self._swift_auth_token()
        return param


class Swift():
    def __init__(self):
        self.config = Config()
        pass

    def object_url(self):
        # get the env and return the respective url
        pass


import datetime


class GWCalender():
    def year_range(self, range):
        rangeSplit = range.split(':')
        current_year = self.today().year
        pass

    def today(self):
        return datetime.date.today()

    def current_year(self):
        return self.today().year

    def get_months(self, kind):
        pass

    def daysMonth(self):
        pass


def _datetime_from_string(idate):
    itime = time.strftime('%H:%M:%S')
    return fields.Datetime.from_string(' '.join([idate, itime]))


def _months_list(kind):
    if kind == 'short':
        names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        index = range(1, 13)
        return zip(index, names)
    else:
        raise NotImplementedError("Only short month names are supported for now. E,g Jan")


def _days_number_list():
    return range(1, 32)
