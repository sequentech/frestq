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
from flask import Blueprint, make_response

from frestq.tasks import SimpleTask
from frestq.app import app

from common import GoodbyeCruelWorldHandler

# set database uri
import os
ROOT_PATH = os.path.split(os.path.abspath(__file__))[0]
SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/db.sqlite' % ROOT_PATH

SERVER_PORT = 5000

SERVER_NAME = '127.0.0.1:%d' % SERVER_PORT

ROOT_URL = 'http://%s/api/queues' % SERVER_NAME

QUEUES_OPTIONS = {
    "goodbye_world": {
        "max_threads": 11,
    }
}

BYEBYE_PORT_RANGE=[6010,6020]

say_api = Blueprint('say', __name__)

@say_api.route('/hello/<username>', methods=['POST'])
def post_hello(username):
    task = SimpleTask(
        receiver_url='http://127.0.0.1:5001/api/queues',
        action="testing.hello_world",
        queue="hello_world",
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
