#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-FileCopyrightText: 2013-2021 Sequent Tech Inc <legal@sequentech.io>
#
# SPDX-License-Identifier: AGPL-3.0-only
#
from flask import Blueprint, make_response

from frestq.app import app
from frestq import decorators
from frestq.tasks import SimpleTask, SubTasksFailed, TaskError
from frestq.action_handlers import TaskHandler

# set database uri
import os
ROOT_PATH = os.path.split(os.path.abspath(__file__))[0]
SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/db.sqlite' % ROOT_PATH

say_api = Blueprint('say', __name__)

@say_api.route('/hello/<username>', methods=['POST'])
def post_hello(username):
    task = SimpleTask(
        receiver_url='http://127.0.0.1:5000/api/queues',
        action="hello_world",
        queue="fail_queue",
        data={
            'username': username
        }
    )
    task.create_and_send()
    return make_response("", 200)
app.register_blueprint(say_api, url_prefix='/say')

# action handler:
@decorators.task(action="hello_world", queue="fail_queue")
class HelloWorld(TaskHandler):
    def execute(self):
        # this task will trigger a failure
        self.task.add(SimpleTask(
            receiver_url='http://127.0.0.1:5000/api/queues',
            action="hello_recoverable_fail",
            queue="fail_queue",
            data={
                'hello': 'world'
            }
        ))

        # this task will be executed after the failure is handled
        self.task.add(SimpleTask(
            receiver_url='http://127.0.0.1:5000/api/queues',
            action="hello_propagated_failure",
            queue="fail_queue",
            data={
                'hello': 'world'
            }
        ))

        # this task will never be executed because previous task will fail and
        # won't be recovered
        self.task.add(SimpleTask(
            receiver_url='http://127.0.0.1:5000/api/queues',
            action="never_land",
            queue="fail_queue",
            data={
                'hello': 'world'
            }
        ))

    def handle_error(self, error):
        print("received an error, but we didn't handle it")
        print(error)

@decorators.task(action="hello_recoverable_fail", queue="fail_queue")
class HelloWorld(TaskHandler):
    def execute(self):
        raise TaskError(dict(some_data="here goes some error"))

    def handle_error(self, error):
        print("handling error: " + error + "with data = " + error.data)
        self.task.propagate = False


@decorators.task(action="hello_propagated_failure", queue="fail_queue")
def hello_propagated_failure(task):
    print("this task will fail and doesn't handle failures")
    raise TaskError(dict(some_data="here goes some error"))


@decorators.task(action="never_land", queue="fail_queue")
def never_land(task):
    print("this task should never be reached")

app.configure_app(config_object=__name__)
if __name__ == "__main__":
    app.run(parse_args=True)
