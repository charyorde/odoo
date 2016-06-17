import os
import time

from openerp import fields

import swiftclient


class Config():
    def env(self):
        env = 'local'
        if os.environ.get('PLATFORM'):
            env = 'PROD'
        elif os.environ.get('CLOUD'):
            env = 'CLOUD'
        elif os.environ.get('DEV'):
            env = 'dev'
        else:
            env
        return env

    def swift(self):
        env = self.env()
        if env != 'local':
            pass
        else:
            return self._swift_local()

    def _swift_local(self):
        username = 'admin'
        password = 'admin'
        authurl = 'http://192.168.2.249:8080/auth/v1.0/'
        preauthurl = 'http://192.168.2.249:8080/v1/AUTH_admin'
        preauthtoken = 'AUTH_tk9cc002cccbc541e49dc26fafd99cf5c1'
        swift = swiftclient.client.Connection(user=username,
                                              key=password,
                                              authurl=authurl,
                                              preauthurl=preauthurl,
                                              preauthtoken=preauthtoken,
                                              retries=3)
        return swift


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
