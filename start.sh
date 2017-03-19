#!/usr/bin/env bash

./odoo.py --without-demo=all --workers=8 --addons-path=addons -r postgres -w postgres --db_host "192.168.3.15" -d gw8
