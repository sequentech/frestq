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

from __future__ import unicode_literals
import json
from datetime import datetime
import logging

from flask import Blueprint, request, make_response

from .action_handlers import ActionHandlers
from . import decorators

@decorators.message_action(action="frestq.update_task", queue="frestq")
def update_task(msg):
    from .app import db
    from .models import Task as ModelTask
    from .tasks import ReceiverTask

    task = msg.task
    logging.debug("UPDATING TASK with id %s" % task.id)
    if task.status == "finished" and msg.data['status'] != 'error':
        # error, cannot update an already finished task (unless it's an error)!
        # TODO: send back an error update
        return

    keys = ['output_data', 'status', 'output_async_data']
    for key in keys:
        if key in msg.input_data:
            if isinstance(msg.input_data[key], basestring):
                logging.debug("SETTING TASK FIELD '%s' to '%s'" % (key,
                    msg.input_data[key]))
            setattr(task, key, msg.input_data[key])
    task.last_modified_date = datetime.utcnow()
    db.session.add(task)
    db.session.commit()

    # do next (it might be a task with a parent task)
    receiver_task = ReceiverTask.instance_by_model(task)
    receiver_task.execute()


@decorators.task(action="frestq.virtual_empty_task", queue="frestq")
def virtual_empty_task(task):
    logging.debug("EXECUTING virtual EMPTY TASK with id %s" % task.task_model.id)
