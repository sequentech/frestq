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

from uuid import uuid4
from flask import request
from datetime import datetime
from flask import current_app
import requests

class SimpleTask(object):
    receiver_url = None
    action = None
    queue = None
    data = None
    async_data = None
    info_text = None
    def __init__(self, receiver_url, action, queue, data=None, async_data=None,
                 info_text=None):
        self.receiver_url = receiver_url
        self.action = action
        self.data = data
        self.queue = queue
        self.async_data = async_data
        self.info_text = info_text

    def create_and_send(self):
        from app import db
        from models import Task as ModelTask, Message as ModelMessage

        # create task
        kwargs = {
            'action': self.action,
            'queue_name': self.queue,
            'sender_url': current_app.config.get('ROOT_URL'),
            'receiver_url': self.receiver_url,
            'is_received': False,
            'is_local': current_app.config.get('ROOT_URL') == self.receiver_url,
            'sender_ssl_cert': current_app.config.get('SSL_CERT_STRING'),
            'input_data': self.data,
            'input_async_data': self.async_data,
            'pingback_date': None, # TODO
            'expiration_date': None, # TODO
            'info_text': self.info_text,
            'id': str(uuid4()),
            'task_type': 'simple'
        }
        task = ModelTask(**kwargs)
        db.session.add(task)
        db.session.commit()

        # send task
        msg_data = {
            'action': task.action,
            'queue_name': task.queue_name,
            'sender_url': current_app.config.get('ROOT_URL'),
            'receiver_url': task.receiver_url,
            'data': task.input_data,
            'task_id': task.id
        }
        send_message(msg_data)


def send_message(msg_data):
    '''
    Sends a message to a peer using RESTQP protocol. Assumes the following
    required fields in msg_data:
    * action
    * queue_name
    * receiver_url

    And the following optional fields:
    * receiver_ssl_cert
    * data
    * async_data
    * task_id
    * pingback_date
    * expiration_date
    * info
    '''
    from app import db
    from models import Task as ModelTask, Message as ModelMessage

    # create message and save it in the database
    msg_data = msg_data.copy()
    msg_data['id'] =  str(uuid4())
    msg_data['is_received'] = False
    msg_data['sender_url'] = current_app.config.get('ROOT_URL')
    msg_data['sender_ssl_cert'] = current_app.config.get('SSL_CERT_STRING', '')
    msg = ModelMessage(**msg_data)

    # send it to the peer
    url =  "%s/%s/" % (msg_data['receiver_url'], msg_data['queue_name'])
    payload = {
        'message_id': msg.id,
        'action': msg.action,
        'sender_url': msg.sender_url,
        "data": msg_data.get('data', '')
    }
    opts = ['async_data', 'task_id', 'pingback_date', 'expiration_date', 'info']
    for opt in opts:
        if opt in msg_data:
            payload[opt] = msg_data[opt]

    # TODO: use and check ssl certs here
    r = requests.post(url, data=payload)

    # TODO: check r.status_code and do some retries if it failed
    msg.output_status = r.status_code

    db.session.add(msg)
    db.session.commit()


def send_task_update(task_id):
    '''
    Sends to the task creator (which is not us) an update with the task
    information. Currently, the information sent is:
    task.output_data
    task.output_async_data
    task.output_status
    '''
    from app import db
    from models import Task as ModelTask, Message as ModelMessage
    task = ModelTask.query.get(task_id)
    update_msg = {
        "action": "frestq.update_task",
        "queue_name": "frestq",
        "receiver_url": task.sender_url,
        "receiver_ssl_cert": task.sender_ssl_cert,
        "data": {
            'task.output_data': task.output_data,
            'task.output_async_data': task.output_async_data,
            'task.status': task.status
        },
        "task_id": task.id
    }
    send_message(update_msg)
    task.last_modified_date = datetime.utcnow()
    db.session.add(task)
    db.session.commit()

def post_task(msg, action_handler):
    '''
    Called by api.post_message when action_handler is of type "task". Creates
    the requested task and processes it.
    '''
    from app import db, scheduler
    from models import (Task as ModelTask,
                        Message as ModelMessage,
                        ReceiverSimpleTask)

    # 1. create received task
    kwargs = {
        'action': msg.action,
        'queue_name': msg.queue_name,
        'sender_url': msg.sender_url,
        'receiver_url': request.url_root,
        'is_received': msg.is_received,
        'is_local': msg.is_local,
        'sender_ssl_cert': msg.sender_ssl_cert,
        'input_data': msg.input_data,
        'input_async_data': msg.input_async_data,
        'pingback_date': msg.pingback_date,
        'expiration_date': msg.expiration_date,
        'info_text': msg.info_text,
        'id': msg.task_id,
        'task_type': 'simple'
    }

    if not kwargs['id']:
        msg.task_id = kwargs['id'] = str(uuid4())
        db.session.add(msg)
        db.session.commit()

    # 2. call to the handler
    # TODO: In the future it will be a ReceiverChordTask

    # if msg originated from ourselves, it might already exist
    if msg.is_local:
        model_task = ModelTask.query.get(msg.task_id)
    else:
        model_task = ModelTask(**kwargs)
        db.session.add(model_task)
        db.session.commit()

    task = ReceiverSimpleTask(model_task)
    action_handler['handler_func'](task)

    # 4. update asynchronously the task sender if requested
    if task.auto_finish_after_handler:
        task.output_status = "finished"

    if task.send_update_to_sender:
        scheduler.add_date_job(send_task_update, datetime.utcnow(),
            [task.id])

    # 3. execute the task synchronously
    #
    # for simple task execute does nothing. For chord tasks this spawns the
    # next subtask (or update sender status to finished), and for parallel
    # tasks it launches all subtasks
    task.execute()
