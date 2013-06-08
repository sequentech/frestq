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


from flask import Blueprint, request, make_response
import json

from action_handlers import ActionHandlers
import decorators

@decorators.message_action(action="frestq.update_task", queue="frestq")
def update_task(msg):
    from app import db

    task = msg.task
    if task.status == "finished":
        # error, cannot update an already finished task!
        # TODO: send back an error update
        return

    keys = ['output_data', 'status', 'output_async_data']
    if msg.data[key]:
        task.output_data = msg.data[key]
    task.last_modified_date = datetime.utcnow()
    db.session.add(task)
    db.session.commit()

@decorators.task(action="testing.hello_world", queue="hello_world")
def hello_world(task):
    name = task.input_data['name']
    print "hello %s! sleeping..\n" % name
    from time import sleep
    sleep(5)
    print "woke up! time to update back =)\n"
    task.output_data = "hello %s!" % name