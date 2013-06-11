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
from tasks import SimpleTask, SequentialTask, ParallelTask
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
    '''
    complex tree of subtasks are executed:
      hello_world (current local task :5001, sequential)
        |
        |-- sequential (local virtual task :5001, sequential)
               |
               |-- subsubtask1/goodbye_cruel_world (local task :5001, simple)
               |
               |-- subsubtask2(goodbye_cruel_world (remote task :5000, simple)

    when all the subtasks are executed, the sender (:5000  via post_hello)
    is notified that the initial task is finished.
    '''
    username = task.task_model.input_data['username']
    print "hello %s! sleeping..\n" % username

    from time import sleep
    sleep(5)

    parenttask = ParallelTask()
    task.add(parenttask)

    subsubtask1 = SimpleTask(
        receiver_url='http://localhost:5001/api/queues',
        action="testing.goodbye_cruel_world",
        queue="hello_world",
        data={
            'username': username*2
        }
    )
    parenttask.add(subsubtask1)

    subsubtask2 = SimpleTask(
        receiver_url='http://localhost:5000/api/queues',
        action="testing.goodbye_cruel_world",
        queue="hello_world",
        data={
            'username': username*3
        }
    )
    parenttask.add(subsubtask2)


    print "woke up! time to finish =)\n"
    task.task_model.output_data = "hello %s!" % username


@decorators.task(action="testing.goodbye_cruel_world", queue="hello_world")
def goodbye_cruel_world(task):
    username = task.task_model.input_data['username']
    print "goodbye %s! sleeping..\n" % username

    from time import sleep
    sleep(5)

    print "woke up! time to finish =)\n"
    task.task_model.output_data = "goodbye %s!" % username