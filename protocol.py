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
import logging

from flask import Blueprint, request, make_response

from action_handlers import ActionHandlers
import decorators

@decorators.message_action(action="frestq.update_task", queue="frestq")
def update_task(msg):
    from app import db

    task = msg.task
    logging.debug("updating task with id %s" % task.id)
    if task.status == "finished" and msg.data['status'] != 'error':
        # error, cannot update an already finished task (unless it's an error)!
        # TODO: send back an error update
        return

    keys = ['output_data', 'status', 'output_async_data']
    for key in keys:
        if key in msg.input_data:
            task.output_data = msg.input_data[key]
    task.last_modified_date = datetime.utcnow()
    db.session.add(task)
    db.session.commit()

@decorators.task(action="testing.hello_world", queue="hello_world")
def hello_world(task):
    username = task.data.input_data['username']
    print "hello %s! sleeping..\n" % username
    from time import sleep
    sleep(5)
    print "woke up! time to update back =)\n"
    task.data.output_data = "hello %s!" % username
