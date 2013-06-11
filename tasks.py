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
import requests
import logging
import json
from uuid import uuid4
from datetime import datetime

from flask import request

class BaseTask(object):
    task_model = None

    def __init__(self):
        super(BaseTask, self).__init__()
        pass

    def create(self):
        '''
        Reimplement
        '''
        return None

    def create_and_send(self):
        '''
        Create the task in the DB and sends the task to the receiver
        '''
        task = self.create()
        self.send()

    def send(self):
        # send task
        from app import app, db
        msg_data = {
            'action': self.task_model.action,
            'queue_name': self.task_model.queue_name,
            'sender_url': app.config.get('ROOT_URL'),
            'receiver_url': self.task_model.receiver_url,
            'data': self.task_model.input_data,
            'task_id': self.task_model.id
        }
        logging.debug('SEND task MESSAGE to %s, TASK id = %s' % (
            self.task_model.receiver_url, msg_data['task_id']))

        # update db
        self.task_model.status = "sent"
        db.session.add(self.task_model)
        db.session.commit()

        send_message(msg_data)

class SimpleTask(BaseTask):
    receiver_url = None
    action = None
    queue = None
    data = None
    async_data = None
    info_text = None
    expiration_date = None
    pingback_date = None

    def __init__(self, receiver_url, action, queue, data=None, async_data=None,
            info_text=None, pingback_date=None, expiration_date=None):
        super(SimpleTask, self).__init__()
        self.receiver_url = receiver_url
        self.action = action
        self.data = data
        self.queue = queue
        self.async_data = async_data
        self.info_text = info_text
        self.expiration_date = expiration_date
        self.pingback_date = pingback_date

    @classmethod
    def create_from_model(cls, task_model):
        ret = cls(
            receiver_url=task_model.receiver_url,
            action=task_model.action,
            queue=task_model.queue_name,
            data=task_model.input_data,
            async_data=task_model.input_async_data,
            pingback_date=task_model.pingback_date,
            expiration_date=task_model.expiration_date
        )
        ret.task_model = task_model
        return ret

    def create(self):
        '''
        Create the task in the DB and returns the model
        '''
        from app import db, app
        from models import Task as ModelTask, Message as ModelMessage

        # create task
        task_id = str(uuid4())
        logging.debug('CREATE local TASK for action %s with ID %s' % (
            self.action, task_id))
        kwargs = {
            'action': self.action,
            'queue_name': self.queue,
            'sender_url': app.config.get('ROOT_URL'),
            'receiver_url': self.receiver_url,
            'is_received': False,
            'is_local': app.config.get('ROOT_URL') == self.receiver_url,
            'sender_ssl_cert': app.config.get('SSL_CERT_STRING'),
            'input_data': self.data,
            'input_async_data': self.async_data,
            'pingback_date': self.pingback_date,
            'expiration_date': self.expiration_date,
            'info_text': self.info_text,
            'id': task_id,
            'status': 'created',
            'task_type': 'simple',
            'parent_id': None
        }
        self.task_model = ModelTask(**kwargs)
        db.session.add(self.task_model)
        db.session.commit()
        return self.task_model


class SequentialTask(BaseTask):
    _subtasks = []

    def __init__(self):
        super(SequentialTask, self).__init__()
        self._subtasks = []

    def add(self, subtask):
        if not self.task_model:
            self._subtasks.append(subtask)
            return

        from app import db
        model = subtask.create()
        model.order = self.count_subtasks()
        model.parent_id = self.task_model.id
        db.session.add(model)
        db.session.commit()

    def count_subtasks(self):
        '''
        Count the number of subtasks
        '''
        from app import db
        from models import Task as ModelTask
        return db.session.query(ModelTask).with_parent(self.task_model, "subtasks").count()

    def create(self):
        '''
        Create the task in the DB and returns the model
        '''
        from app import db, app
        from models import Task as ModelTask, Message as ModelMessage

        # create task
        task_id = str(uuid4())
        logging.debug('CREATE local SEQUENTIAL TASK with ID %s' % task_id)
        kwargs = {
            'action': 'frestq.virtual_empty_task',
            'queue_name': 'frestq',
            'sender_url': app.config.get('ROOT_URL'),
            'receiver_url': app.config.get('ROOT_URL'),
            'is_received': False,
            'is_local': True,
            'sender_ssl_cert': app.config.get('SSL_CERT_STRING'),
            'input_data': dict(),
            'input_async_data': dict(),
            'pingback_date': None,
            'expiration_date': None,
            'info_text': None,
            'id': task_id,
            'status': 'created',
            'task_type': 'sequential',
            'parent_id': None
        }
        self.task_model = ModelTask(**kwargs)
        # create also subtasks
        i = 0
        for subtask in self._subtasks:
            subtask_model = subtask.create()
            subtask_model.order = i
            subtask_model.parent_id = self.task_model.id
            db.session.add(subtask_model)
            i += 1
        db.session.add(self.task_model)
        db.session.commit()
        return self.task_model


class ReceiverTask(object):
    # set this to true to send an update to the sender
    send_update_to_sender = False

    # set this to true when you want to automatically finish your task and send
    # an update to sender with the finished state. This is for example set to
    # true in ReceiverSimpleTasks but to False in SequentialTasks, because sequentials
    # send auto finish when all subtask have finished (do_next does that).
    auto_finish_after_handler = False

    # reference to the task model
    task_model = None

    def __init__(self, task_model):
        self.task_model = task_model

    def do_next(self):
        '''
        Function that gets executed after a task's action handler has been
        executed.
        '''
        from app import db
        from models import Task as ModelTask
        # check if there's a parent task, and if so do_next() it
        if self.task_model.parent_id:
            parent = db.session.query(ModelTask).get(self.task_model.parent_id)
            parent_task = ReceiverTask.instance_by_model(parent)
            parent_task.do_next()

    @staticmethod
    def instance_by_model(task_model):
        '''
        This is a factory pattern
        '''
        if task_model.task_type == 'simple':
            return ReceiverSimpleTask(task_model)
        elif task_model.task_type == 'sequential':
            return ReceiverSequentialTask(task_model)
        else:
            raise Exception('unknown %s task type' % task_model.task_type)

    def execute(self):
        '''
        executes the task, sending it if it needed to the appropiate party.
        '''
        pass


class ReceiverSimpleTask(ReceiverTask):
    '''
    Represents a simple task
    '''
    auto_finish_after_handler = True

    def __init__(self, task_model):
        super(ReceiverSimpleTask, self).__init__(task_model)
        # local task do not need updates
        self.send_update_to_sender = not task_model.is_local

    def execute(self):
        '''
        Executes the task, sending it to the party that needs to execute.
        This will trigger the call to the appropiate action handler for this
        task in the party receiving the task.

        NOTE: If it has a parent task, parent_task.do_next() will be called if
        needed.

        NOTE: When it's a local task, it's also sent.
        '''
        simple_task = SimpleTask.create_from_model(self.task_model)
        simple_task.send()


class ReceiverSequentialTask(ReceiverTask):
    '''
    Represents the kind of base task executed when received by a frestq node.
    You can easily add subtasks with add() method.

    Subtasks will begin to be processed asynchronously when do_next() function
    is called.
    '''

    def __init__(self, task_model):
        super(ReceiverSequentialTask, self).__init__(task_model)

    def add(self, subtask):
        '''
        Add a subtask. Subtasks will be executed in chronological adding order.

        For subtask, supported types are:
         * SimpleTask
        '''
        from app import db
        model = subtask.create()
        model.order = self.count_subtasks()
        model.parent_id = self.task_model.id
        db.session.add(model)
        db.session.commit()

    def count_subtasks(self):
        '''
        Count the number of subtasks
        '''
        from app import db
        from models import Task as ModelTask
        return db.session.query(ModelTask).with_parent(self.task_model, "subtasks").count()

    def next_subtask(self):
        '''
        Returns next subtask if any or None
        '''
        from app import db
        from models import Task as ModelTask
        return db.session.query(ModelTask).with_parent(self.task_model, "subtasks").\
            filter(ModelTask.status != 'finished').order_by(ModelTask.order).first()

    def execute(self):
        '''

        '''
        self.do_next()

    def do_next(self):
        '''
        After executing the task handler, this funcion is called once per each
        subtask, and executes each subtask sequentally and in order
        '''
        from app import db, get_scheduler
        from models import Task as ModelTask
        next_subtask_model = self.next_subtask()

        # if there's no subtask left to do, send the finished signal to the
        # task creator
        if not next_subtask_model:
            self.task_model.status = "finished"
            from app import db
            db.session.add(self.task_model)
            db.session.commit()
            if not self.task_model.is_local:
                get_scheduler().add_now_job(send_task_update, [self.task_model.id])

            # check if there's a parent task, and if so do_next() it
            if self.task_model.parent_id:
                parent_model = db.session.query(ModelTask).get(self.task_model.parent_id)
                parent_task = ReceiverTask.instance_by_model(parent_model)
                parent_task.do_next()
            return

        if next_subtask_model.status in ['sent', 'executing', 'error']:
            return

        # execute next subtask
        next_subtask = ReceiverTask.instance_by_model(next_subtask_model)
        next_subtask.execute()


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
    from app import db, app
    from models import Task as ModelTask, Message as ModelMessage

    # create message and save it in the database
    msg_data = msg_data.copy()
    msg_data['id'] =  str(uuid4())
    msg_data['is_received'] = False
    msg_data['sender_url'] = app.config.get('ROOT_URL')
    msg_data['sender_ssl_cert'] = app.config.get('SSL_CERT_STRING', '')
    msg = ModelMessage(**msg_data)
    db.session.add(msg)
    db.session.commit()

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
        if opt in msg_data and msg_data[opt] != None:
            payload[opt] = msg_data[opt]

    logging.debug('SENDING MESSAGE id %s with action %s to %s' % (
        msg.id, msg.action, url))

    # TODO: use and check ssl certs here
    r = requests.post(url, data=json.dumps(payload))

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
    logging.debug("SENDING UPDATE to TASK with id %s" % task_id)
    from app import db
    from models import Task as ModelTask, Message as ModelMessage
    task = ModelTask.query.get(task_id)
    update_msg = {
        "action": "frestq.update_task",
        "queue_name": "frestq",
        "receiver_url": task.sender_url,
        "receiver_ssl_cert": task.sender_ssl_cert,
        "data": {
            'output_data': task.output_data,
            'output_async_data': task.output_async_data,
            'status': task.status
        },
        "task_id": task.id
    }
    send_message(update_msg)
    task.last_modified_date = datetime.utcnow()
    db.session.add(task)
    db.session.commit()

    # task finished. check if there's a parent task, and if so do_next() it
    if task.parent_id:
        parent = db.session.query(ModelTask).get(task.parent_id)
        parent_task = ReceiverTask.instance_by_model(parent)
        parent_task.do_next()

def post_task(msg, action_handler):
    '''
    Called by api.post_message when action_handler is of type "task". Creates
    the requested task and processes it.
    '''
    from app import db, get_scheduler, app
    from models import Task as ModelTask, Message as ModelMessage

    logging.debug('EXEC TASK with id %s' % msg.task_id)

    # 1. create received task
    is_local = msg.sender_url == app.config.get('ROOT_URL')
    kwargs = {
        'action': msg.action,
        'queue_name': msg.queue_name,
        'sender_url': msg.sender_url,
        'receiver_url': msg.receiver_url,
        'is_received': msg.is_received,
        'is_local': is_local,
        'sender_ssl_cert': msg.sender_ssl_cert,
        'input_data': msg.input_data,
        'input_async_data': msg.input_async_data,
        'pingback_date': msg.pingback_date,
        'expiration_date': msg.expiration_date,
        'status': 'executing',
        'info_text': msg.info_text,
        'id': msg.task_id,
        'task_type': 'sequential'
    }

    if not kwargs['id']:
        msg.task_id = kwargs['id'] = str(uuid4())
        db.session.add(msg)
        db.session.commit()

    # 2. call to the handler

    # if msg originated from ourselves, it might already exist
    if is_local:
        task_model = ModelTask.query.get(msg.task_id)
        if task_model.task_type == 'simple':
            # this could happen if the task was created with ReceiverSimpleTask
            task_model.task_type = 'sequential'
            db.session.add(task_model)
            db.session.commit()
    else:
        task_model = ModelTask(**kwargs)
        db.session.add(task_model)
        db.session.commit()

    task = ReceiverTask.instance_by_model(task_model)
    action_handler['handler_func'](task)

    # 3. update asynchronously the task sender if requested
    if task.auto_finish_after_handler:
        task_model.status = "finished"
        db.session.add(task_model)
        db.session.commit()

    if task.send_update_to_sender:
        get_scheduler().add_now_job(send_task_update, [task_model.id])

    # 4. do_next the task synchronously
    #
    # for simple task this function does nothing. For sequential tasks this spawns
    # the next subtask (or update sender status to finished), and for parallel
    # tasks it launches all subtasks
    task.do_next()
