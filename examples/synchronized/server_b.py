#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of frestq.
# Copyright (C) 2013  Eduardo Robles Elvira <edulix AT wadobo DOT com>

# frestq is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# frestq  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with frestq.  If not, see <http://www.gnu.org/licenses/>.

import copy

from frestq import decorators
from frestq.app import app, run_app
from frestq.tasks import SimpleTask, ParallelTask, SynchronizedTask
from frestq.action_handlers import SynchronizedTaskHandler

from common import GoodbyeCruelWorldHandler

# configuration:

# set database uri
import os
ROOT_PATH = os.path.split(os.path.abspath(__file__))[0]
SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/db2.sqlite' % ROOT_PATH

SERVER_NAME = '127.0.0.1:5001'

SERVER_PORT = 5001

ROOT_URL = 'http://127.0.0.1:5001/api/queues'

QUEUES_OPTIONS = {
    'goodbye_world': {
        'max_threads': 3,
    }
}

BYEBYE_PORT_RANGE=[6000,6003]

# action handler:

def goodbye_sync_handler(task):

    port = subtask.get_data()['sync_output_data']['port']
    parent = subtask.get_parent()
    return dict

@decorators.internal_task(name="synchronized_goodbye")
class SynchronizedGoodbyeHandler(SynchronizedTaskHandler):

    def new_reservation(self, subtask):
        '''
        save reservation data
        '''
        subtask_id = subtask.get_data()["id"]
        reservation_data = subtask.get_data()["reservation_data"]
        if not isinstance(self.task.task_model.input_data, dict):
            self.task.task_model.input_data = dict()

        self.task.task_model.input_data[subtask_id] = reservation_data
        db.session.add(self.task.task_model)
        db.session.commit()

    def pre_execute(self):
        reservation_data = self.task.get_data()["reservation_data"]
        for subtask in self.task.get_children():
            subtask.task_model.input_data["reservation_data"] = reservation_data
            db.session.add(subtask.task_model)
        db.session.commit()

@decorators.task(action="testing.hello_world", queue="hello_world")
def hello_world(task):
    '''
    complex tree of subtasks are executed:
      task/hello_world (current local task :5001, sequential)
        |
        |-- task1 (local virtual task :5001, parallel)
        |      |
        |      |-- task11 (local task :5001, synchronized)
        |      |      |
        |      |      |-- task111/GoodbyeCruelWorldHandler (local task : 5001, simple)
        |      |      |
        |      |      |-- task112/GoodbyeCruelWorldHandler (local task : 5001, simple)
        |      |      |
        |      |      |-- task113/GoodbyeCruelWorldHandler (remote task : 5000, simple)
        |      |
        |      |-- task12 (local task :5001, synchronized)
        |      |      |
        |      |      |-- task121/GoodbyeCruelWorldHandler (local task : 5001, simple)
        |      |      |
        |      |      |-- task122/GoodbyeCruelWorldHandler (local task : 5001, simple)
        |      |      |
        |      |      |-- task123/GoodbyeCruelWorldHandler (remote task : 5000, simple)
        |
        |-- task2/all_goodbyes_together (local virtual task :5000, simple)


    when all the subtasks are executed, the sender (:5000  via post_hello)
    is notified that the initial task is finished.
    '''
    username = task.get_data()['input_data']['username']

    task1 = ParallelTask()
    task.add(task1)

    task11 = SynchronizedTask(handler=SynchronizedGoodbyeHandler)
    task1.add(task11)

    goodbye_kwargs = dict(
        receiver_url='http://127.0.0.1:5001/api/queues',
        action="testing.goodbye_cruel_world",
        queue="goodbye_world",
        data={
            'username': username*2
        }
    )
    goodbye_remote_kwargs = copy.deepcopy(goodbye_kwargs)
    goodbye_remote_kwargs.update({
        'receiver_url':'http://127.0.0.1:5000/api/queues'
    })

    task111 = SimpleTask(**goodbye_kwargs)
    task11.add(task111)

    task112 = SimpleTask(**goodbye_kwargs)
    task11.add(task112)

    task113 = SimpleTask(**goodbye_remote_kwargs)
    task11.add(task113)

    task12 = SynchronizedTask(handler=SynchronizedGoodbyeHandler)
    task1.add(task12)

    task121 = SimpleTask(**goodbye_kwargs)
    task12.add(task121)

    task122 = SimpleTask(**goodbye_kwargs)
    task12.add(task122)

    task123 = SimpleTask(**goodbye_remote_kwargs)
    task12.add(task123)


    task2 = SimpleTask(**goodbye_remote_kwargs)
    task.add(task2)

    return dict(
        output_data = "hello %s!" % username
    )

@decorators.task(action="testing.all_goodbyes_together", queue="hello_world")
def all_goodbyes_together(task):
    return dict(
        output_data = [
            child.get_data()['output_data']
                for child in task.get_prev().get_children()
        ]
    )

if __name__ == "__main__":
    run_app(config_object=__name__)
