#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-FileCopyrightText: 2013-2021 Sequent Tech Inc <legal@sequentech.io>
#
# SPDX-License-Identifier: AGPL-3.0-only
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
