#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-FileCopyrightText: 2013-2021 Agora Voting SL <contact@nvotes.com>
#
# SPDX-License-Identifier: AGPL-3.0-only
#
import copy

from frestq import decorators
from frestq.app import db
from frestq.app import app
from frestq.tasks import SimpleTask, ParallelTask, SynchronizedTask
from frestq.action_handlers import SynchronizedTaskHandler

from common import GoodbyeCruelWorldHandler

# configuration:

# set database uri
import os
ROOT_PATH = os.path.split(os.path.abspath(__file__))[0]
SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/db2.sqlite' % ROOT_PATH

SERVER_PORT = 5001

SERVER_NAME = '127.0.0.1:%d' % SERVER_PORT

ROOT_URL = 'http://%s/api/queues' % SERVER_NAME

QUEUES_OPTIONS = {
    'goodbye_world': {
        'max_threads': 3,
    }
}

BYEBYE_PORT_RANGE=[6000,6003]


@decorators.internal_task(name="synchronized_goodbye")
class SynchronizedGoodbyeHandler(SynchronizedTaskHandler):

    def new_reservation(self, subtask):
        '''
        save reservation data
        '''
        subtask_id = subtask.get_data()["id"]
        reservation_data = subtask.get_data()["reservation_data"]
        ## TODO: create a set_reservation_data(subtask_id, data) to use it here
        if not isinstance(self.task.task_model.reservation_data, dict):
            self.task.task_model.reservation_data = dict()

        self.task.task_model.reservation_data[subtask_id] = reservation_data
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

    all_goodbyes_together_kwargs = dict(
        receiver_url='http://127.0.0.1:5001/api/queues',
        action="testing.all_goodbyes_together",
        queue="end_of_the_world"
    )

    task2 = SimpleTask(**all_goodbyes_together_kwargs)
    task.add(task2)

    # this will get overridden by last task, all_goodbyes_together
    return dict(
        output_data = "hello %s!" % username
    )

@decorators.task(action="testing.all_goodbyes_together", queue="end_of_the_world")
def all_goodbyes_together(task):
    output_data = [
        child.get_data()['output_data']
            for child in task.get_prev().get_children()[0].get_children()
    ]
    parent_model = task.get_parent().task_model
    task.get_parent().task_model.output_data = output_data
    db.session.add(parent_model)
    db.session.commit()

    return dict(
        output_data = output_data
    )

app.configure_app(config_object=__name__)

if __name__ == "__main__":
    app.run(parse_args=True)
