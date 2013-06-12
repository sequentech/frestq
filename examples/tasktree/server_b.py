#!/usr/bin/env python
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

from frestq import decorators
from frestq.app import app, run_app
from frestq.tasks import SimpleTask, ParallelTask

import common

# configuration:

SQLALCHEMY_DATABASE_URI = 'sqlite:///db2.sqlite'

SERVER_NAME = 'localhost:5001'

SERVER_PORT = 5001

ROOT_URL = 'http://localhost:5001/api/queues'


# action handler:

@decorators.task(action="testing.hello_world", queue="hello_world")
def hello_world(task):
    '''
    complex tree of subtasks are executed:
      hello_world (current local task :5001, sequential)
        |
        |-- subtask (local virtual task :5001, sequential)
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

    subtask = ParallelTask()
    task.add(subtask)

    subsubtask1 = SimpleTask(
        receiver_url='http://localhost:5001/api/queues',
        action="testing.goodbye_cruel_world",
        queue="hello_world",
        data={
            'username': username*2
        }
    )
    subtask.add(subsubtask1)

    subsubtask2 = SimpleTask(
        receiver_url='http://localhost:5000/api/queues',
        action="testing.goodbye_cruel_world",
        queue="hello_world",
        data={
            'username': username*3
        }
    )
    subtask.add(subsubtask2)


    print "woke up! time to finish =)\n"
    task.task_model.output_data = "hello %s!" % username

if __name__ == "__main__":
    run_app(config_object=__name__)
