# -*- coding: utf-8 -*-

# This file is part of frestq.
# Copyright (C) 2013  Eduardo Robles Elvira <edulix AT wadobo DOT com>

# election-orchestra is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# election-orchestra  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with election-orchestra.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import json
from datetime import datetime

from flask import Blueprint, request, make_response
from flask import current_app

from action_handlers import ActionHandlers
from tasks import SimpleTask
import decorators

user_api = Blueprint('user_api', __name__)

@user_api.route('/hello/<username>', methods=['POST'])
def post_hello(username):
    task = SimpleTask(
        receiver_url='http://localhost:5001/api/queues',
        action="testing.hello_world",
        queue="hello_world",
        data={
            'username': username
        }
    )
    task.create_and_send()
    return make_response("", 200)

@decorators.task(action="testing.hello_world", queue="hello_world")
def hello_world(task):
    username = task.data.input_data['username']
    print "hello %s! sleeping..\n" % username
    from time import sleep
    sleep(5)
    if len(username) < 10:
        subtask = SimpleTask(
            receiver_url='http://localhost:5001/api/queues',
            action="testing.hello_world",
            queue="hello_world",
            data={
                'username': username*2
            }
        )
        task.add(subtask)
    print "woke up! time to update back =)\n"
    task.data.output_data = "hello %s!" % username
