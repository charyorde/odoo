#!/usr/bin/env bash

#cp odoo-deps.sh .profile.d/

apt-get install -y libpq-dev libxml2-dev libxslt1-dev python-ldb-dev libldap2-dev libsasl2-dev
apt-get install -y npm
ln -s /usr/bin/nodejs /usr/bin/node
npm install -g less less-plugin-clean-css

#./odoo.py --without-demo=all --workers=8 --addons-path=addons -r postgres -w postgres --db_host "192.168.3.15" -d gw8
