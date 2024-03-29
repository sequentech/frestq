#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-FileCopyrightText: 2013-2021 Sequent Tech Inc <legal@sequentech.io>
#
# SPDX-License-Identifier: AGPL-3.0-only
#
from frestq import decorators
from frestq.app import app

# configuration:

# set database uri
import os
ROOT_PATH = os.path.split(os.path.abspath(__file__))[0]
SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/db2.sqlite' % ROOT_PATH

SERVER_NAME = '127.0.0.1:5001'

SERVER_PORT = 5001

ROOT_URL = 'https://127.0.0.1:5001/api/queues'

SSL_CERT_PATH = '%s/certs/selfsigned2/cert.pem' % ROOT_PATH

SSL_KEY_PATH = '%s/certs/selfsigned2/key-nopass.pem' % ROOT_PATH

ALLOW_ONLY_SSL_CONNECTIONS = True

# action handler:

@decorators.task(action="hello_world", queue="say_queue")
def hello_world(task):
    print("I'm sleepy!..\n")

    # simulate we're working hard taking our time
    from time import sleep
    sleep(5)

    username = task.get_data()['input_data']['username']
    return dict(
        output_data = "hello %s!" % username
    )

app.configure_app(config_object=__name__)

if __name__ == "__main__":
    app.run(parse_args=True)
