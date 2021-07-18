#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# Copyright (c) 2013-2021 Agora Voting SL <contact@nvotes.com>.
#
# This file is part of frestq 
# (see https://github.com/agoravoting/frestq).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
from flask import Blueprint, make_response, request
import logging

from frestq.tasks import SimpleTask
from frestq.app import app

logging.basicConfig(level=logging.DEBUG)

# set database uri
import os
ROOT_PATH = os.path.split(os.path.abspath(__file__))[0]
SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/db.sqlite' % ROOT_PATH

ROOT_URL = 'https://127.0.0.1:5000/api/queues'

SSL_CERT_PATH = '%s/certs/selfsigned/cert.pem' % ROOT_PATH

SSL_KEY_PATH = '%s/certs/selfsigned/key-nopass.pem' % ROOT_PATH

ALLOW_ONLY_SSL_CONNECTIONS = True

say_api = Blueprint('say', __name__)

@say_api.route('/hello/<username>', methods=['GET', 'POST'])
def post_hello(username):
    task = SimpleTask(
        receiver_url='https://127.0.0.1:5001/api/queues',
        action="hello_world",
        queue="say_queue",
        data={
            'username': username
        }
    )
    task.create_and_send()
    return make_response("", 200)

app.register_blueprint(say_api, url_prefix='/say')
app.configure_app(config_object=__name__)

if __name__ == "__main__":
    app.run(parse_args=True)
