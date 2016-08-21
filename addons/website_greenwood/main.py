import os
import time

from openerp import fields

import swiftclient
SWIFT_GWTEMP_CONTAINER = 'gwtemp'
SWIFT_GW_CONTAINER = 'gw'
SWIFT_WEB_CONTAINER = 'web'
SWIFT_USER_CONTENT_CONTAINER = 'gwusercontent'
SWIFT_PUBLIC_CONTAINER = 'public'


class Config():
    def __init__(self):
        self.env = dict(name='local',
                        swift_token='AUTH_tkb08608c1fcba43bd9518b98af0e2fa30',
                        swift_storageurl='http://192.168.2.249:8080/v1/AUTH_admin')

    def _env(self):
        env = self.env
        if os.environ.get('PLATFORM'):
            env = dict(name='PROD', swift_token='')
        elif os.environ.get('CLOUD'):
            env = dict(name='CLOUD', swift_token='')
        elif os.environ.get('DEV'):
            env = dict(name='dev', swift_token='')
        else:
            env
        return env

    def swift(self):
        env = self._env()
        if env['name'] != 'local':
            pass
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
