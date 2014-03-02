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
import requests
import logging
import json
import types
import OpenSSL

import copy
from uuid import uuid4
from datetime import datetime

from flask import request

from .app import db, app
from .fscheduler import FScheduler, INTERNAL_SCHEDULER_NAME
from .models import Task as ModelTask, Message as ModelMessage
from .utils import dumps

class BaseTask(object):
    '''
    Base task to be inherited by SimpleTask, SequentialTask, etc.

    It implements the public interface of a task that is going to be sent to
    the task executer/receiver (which can be our own server or another one).

    It has a constructor, and two important functions to be reimplemented:
    create() and send(). Create() actually creates the task in the database and
    send() sends it to the receiver.
    '''
    label = ""

    # set this to true to send an update to the sender
    send_update_to_sender = False

    # set this to true when you want to automatically finish your task and send
    # an update to sender with the finished state.
    auto_finish_after_handler = False

    # reference to the task model
    task_model = None

    # the action handler for this task, if any
    action_handler = None

    # the action handler for this task, if action_handler is a class
    action_handler_object = None

    error = None

    propagate = False


    def __init__(self):
        super(BaseTask, self).__init__()
        pass

    def create(self):
        '''
        Reimplement
        '''
        return None

    def is_internal(self):
        '''
        Returns whether the task is internal
        '''
        return self.task_model.queue_name.startswith("internal.")

    def create_and_send(self):
        '''
        Create the task in the DB and sends the task to the receiver
        '''
        self.task_model = self.create()
        self.send()

    def send(self):
        # send task
        msg_data = {
            'action': self.task_model.action,
            'queue_name': self.task_model.queue_name,
            'sender_url': app.config.get('ROOT_URL'),
            'sender_ssl_cert': app.config.get('SSL_CERT_STRING', ''),
            'receiver_url': self.task_model.receiver_url,
            'input_data': self.task_model.input_data,
            'task_id': self.task_model.id
        }
        logging.debug('SEND task MESSAGE to %s, TASK id = %s' % (
            self.task_model.receiver_url, msg_data['task_id']))

        # update db
        self.task_model.status = "sent"
        db.session.add(self.task_model)
        db.session.commit()

        send_message(msg_data, update_task_receiver_ssl_cert=True, task=self.task_model)

    def set_reservation_data(self, data):
        '''
        Sets reservation data
        '''
        self.task_model.reservation_data = data

    def get_reservation_data(self):
        '''
        Returns reservation data
        '''
        return self.task_model.reservation_data

    def get_data(self):
        '''
        Returns public task data available to the user
        '''
        return copy.deepcopy(self.task_model.to_dict())

    def set_output_data(self, data, send_update_to_sender=False):
        '''
        Setter of a task's output data.
        '''
        self.task_model.output_data = data
        if send_update_to_sender:
            db.session.add(self.task_model)
            db.session.commit()

            # if task is local, there's no update neeeded
            if self.task_model.is_local:
                return
            sched = FScheduler.get_scheduler(INTERNAL_SCHEDULER_NAME)
            sched.add_now_job(send_task_update, [self.task_model.id])

    @staticmethod
    def instance_by_id(task_id):
        task_model = ModelTask.query.get(task_id)
        return BaseTask.instance_by_model(task_model)

    @staticmethod
    def instance_by_model(task_model):
        '''
        This is a factory pattern
        '''
        if task_model.task_type == 'simple':
            return SimpleTask._create_from_model(task_model)
        elif task_model.task_type == 'sequential':
            return SequentialTask._create_from_model(task_model)
        elif task_model.task_type == 'external':
            return ExternalTask._create_from_model(task_model)
        elif task_model.task_type == 'parallel':
            return ParallelTask._create_from_model(task_model)
        elif task_model.task_type == 'synchronized':
            return SynchronizedTask._create_from_model(task_model)
        else:
            raise Exception('unknown %s task type' % task_model.task_type)


    def get_children(self):
        '''
        Returns the ordered list of children of this task if any
        '''
        subtasks = db.session.query(ModelTask).with_parent(self.task_model,
            "subtasks").order_by(ModelTask.order)

        children_tasks = [self.instance_by_model(task)
            for task in subtasks]
        return children_tasks

    def get_child(self, label):
        '''
        Gets a children by label
        '''
        task = db.session.query(ModelTask).with_parent(self.task_model,
            "subtasks").filter(ModelTask.label == label).first()
        if not task:
            return None
        return self.instance_by_model(task)

    def get_parent(self):
        '''
        Returns the parent BaseTask
        '''
        # check if there's a parent task, and if so execute() it
        if not self.task_model.parent_id:
            return None

        parent = db.session.query(ModelTask).get(self.task_model.parent_id)
        parent_task = self.instance_by_model(parent)
        return parent_task

    def get_siblings(self):
        '''
        Returns the list of siblings of this task if any
        '''
        if not self.task_model.parent_id:
            return []

        siblings = db.session.query(ModelTask)\
            .filter(ModelTask.id == self.task_model.parent_id,
                ModelTask.id != self.task_model.id)\
            .order_by(ModelTask.order)

        return [self.instance_by_model(task)
            for task in siblings]

    def get_sibling(self, label):
        '''
        Gets a children by label
        '''
        task = db.session.query(ModelTask).filter(
            ModelTask.id == self.task_model.parent_id,
            ModelTask.id != self.task_model.id,
            ModelTask.label == label).first()
        if not task:
            return None
        return self.instance_by_model(task)

    def get_prev(self):
        '''
        Get previous sibling if any
        '''
        if self.task_model.order == 0 or not self.task_model.parent_id:
            return None

        task = db.session.query(ModelTask)\
            .filter(ModelTask.parent_id == self.task_model.parent_id,
                ModelTask.order == self.task_model.order - 1).first()
        if not task:
            return None
        return self.instance_by_model(task)

    def get_next(self):
        '''
        Get previous sibling if any
        '''
        if not self.task_model.parent_id:
            return None

        task = db.session.query(ModelTask)\
            .filter(ModelTask.parent_id == self.task_model.parent_id,
                ModelTask.order == self.task_model.order + 1).first()
        if not task:
            return None
        return self.instance_by_model(task)

    def _init_from_model(self):
        '''
        Init function called by _create_from_model in inherited classes.
        '''
        from .action_handlers import ActionHandlers
        action_handler_data = ActionHandlers.get_action_handler(
            self.task_model.action, self.task_model.queue_name)

        if action_handler_data:
            self.action_handler = action_handler_data['handler_func']

        if type(self.action_handler) is types.TypeType:
            self.action_handler_object = self.action_handler(self)

    def run_action_handler(self):
        '''
        Executes action handler if it makes sense and the way it should:
         * if it's internal, it executes no action handler
         * if it's an action handler object, calls to its execute function
         * if it's a function, just calls it
        '''
        if self.is_internal():
            return None

        if self.action_handler_object:
            return self.action_handler_object.execute()
        else:
            return self.action_handler(self)

    @staticmethod
    def instance_by_id(task_id):
        '''
        Given an id, returns the appropiate Task instance. Assumes that the id
        exists.
        '''
        task_model = ModelTask.query.get(task_id)
        return BaseTask.instance_by_model(task_model)

    def execute(self):
        '''
        Function that gets executed after a task's action handler has been
        executed.

        Handles the finalization of the execution of the task, sending it if it
        needed to the appropiate party. This function might be called multiple
        times until the task is finished, so internally it should detect what to
        do in each case.

        For example, in SequentialTask, it's called after each subtask
        is completed.
        '''
        pass

    def execute_parent(self):
        '''
        Executes parent task if there's any.
        '''
        # check if there's a parent task, and if so execute() it
        if not self.task_model.parent_id:
            return

        parent = db.session.query(ModelTask).get(self.task_model.parent_id)
        parent_task = BaseTask.instance_by_model(parent)
        parent_task.execute()


class SimpleTask(BaseTask):
    '''
    Simple task instances are the only kind of tasks that will be actually sent
    to a receiver machine. This receiver might be the same as the sender.

    A simple task is sent to an action handler in a specific queue of a
    receiving server.

    It's worth noting that the sender server sees a simple task as only one
    single item, but the receiving server sees it *always* as a sequential task.
    This way the action handler can attach a tree of subtasks to decompose the
    work to do in a way that is transparent to the sender.
    '''
    receiver_url = None
    action = None
    queue = None
    data = None
    info_text = None
    expiration_date = None
    pingback_date = None

    auto_finish_after_handler = True

    def __init__(self, receiver_url, action, queue, data=None, label=None,
            info_text=None, pingback_date=None, expiration_date=None,
            receiver_ssl_cert=None):
        '''
        Constructor of a simple tasks. It takes as input all the information
        needed to send the single task to the receiver end.

        Note: to save the task in the database of the sender you need to call
        to create(), and to send it to the receiver, call to send().
        '''
        super(SimpleTask, self).__init__()
        self.label = label
        self.receiver_url = receiver_url
        self.action = action
        self.data = data
        self.queue = queue
        self.info_text = info_text
        self.expiration_date = expiration_date
        self.pingback_date = pingback_date
        self.receiver_ssl_cert = receiver_ssl_cert

    @classmethod
    def _create_from_model(cls, task_model):
        ret = cls(
            receiver_url=task_model.receiver_url,
            action=task_model.action,
            queue=task_model.queue_name,
            data=task_model.input_data,
            pingback_date=task_model.pingback_date,
            expiration_date=task_model.expiration_date,
            label=task_model.label
       )
        ret.task_model = task_model
        # local task do not need updates
        ret.send_update_to_sender = not task_model.is_local
        ret._init_from_model()
        return ret

    def create(self):
        '''
        Create the simple task in the DB and returns the model.
        '''

        # create task
        task_id = str(uuid4())
        logging.debug('CREATE local TASK for action %s with ID %s' % (
            self.action, task_id))
        kwargs = {
            'action': self.action,
            'queue_name': self.queue,
            'label': self.label,
            'sender_url': app.config.get('ROOT_URL'),
            'receiver_url': self.receiver_url,
            'is_received': False,
            'is_local': app.config.get('ROOT_URL') == self.receiver_url,
            'sender_ssl_cert': app.config.get('SSL_CERT_STRING', ''),
            'receiver_ssl_cert': self.receiver_ssl_cert,
            'input_data': self.data,
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

    def execute(self):
        '''
        Executes the task, sending it to the party that needs to execute.
        This will trigger the call to the appropiate action handler for this
        task in the party receiving the task. See the class description for
        more details behind this behaviour.

        NOTE: If it has a parent task, parent_task.execute() will be called if
        needed.

        NOTE: When it's a local task, it's also sent, if hasn't been sent yet.
        '''
        if self.task_model.status == 'created':
            logging.debug('SENDING TASK %s' % self.task_model.id)
            simple_task = SimpleTask._create_from_model(self.task_model)
            simple_task.send()
        elif self.task_model.status == "finished":
            self.execute_parent()
        elif self.task_model.status == "error":
            self.execute_parent()


class ExternalTask(SimpleTask):
    '''
    Represents a task that requires external asynchronous input.

    A typical example is a task that requires user input. This kind of task
    doesn't execute any code, it just keep in "executing" state until you
    manually change the state to "finished" with finish()
    '''

    def __init__(self, data=None, label=None, expiration_date=None):
        '''
        Constructor of a external tasks. It takes as input all the information
        needed to send the single task to the receiver end.

        Note: to save the task in the database of the sender you need to call
        to create(), and to send it to the receiver, call to send().
        '''
        super(ExternalTask, self).__init__(
            receiver_url=app.config.get('ROOT_URL'),
            receiver_ssl_cert=app.config.get('SSL_CERT_STRING', ''),
            data=data,
            label=label,
            pingback_date=None,
            expiration_date=expiration_date,
            queue=INTERNAL_SCHEDULER_NAME,
            action="frestq.virtual_empty_task")

    @classmethod
    def _create_from_model(cls, task_model):
        ret = cls(
            data=task_model.input_data,
            expiration_date=task_model.expiration_date,
            label=task_model.label
       )
        ret.task_model = task_model
        # local task do not need updates
        ret.send_update_to_sender = False
        ret._init_from_model()
        return ret

    def create(self):
        '''
        Create the external task in the DB and returns the model.
        '''

        # create task
        task_id = str(uuid4())
        logging.debug('CREATE EXTERNAL TASK with ID %s' % task_id)
        kwargs = {
            'action': 'frestq.virtual_empty_task',
            'queue_name': INTERNAL_SCHEDULER_NAME,
            'label': self.label,
            'sender_url': app.config.get('ROOT_URL'),
            'receiver_url': self.receiver_url,
            'is_received': False,
            'is_local': app.config.get('ROOT_URL') == self.receiver_url,
            'sender_ssl_cert': app.config.get('SSL_CERT_STRING', ''),
            'receiver_ssl_cert': self.receiver_ssl_cert,
            'input_data': self.data,
            'pingback_date': self.pingback_date,
            'expiration_date': self.expiration_date,
            'id': task_id,
            'status': 'created',
            'task_type': 'external',
            'parent_id': None
        }
        self.task_model = ModelTask(**kwargs)
        db.session.add(self.task_model)
        db.session.commit()
        return self.task_model

    def finish(self, data=None):
        '''
        Sets the task as finishes and executes the next task if any
        '''
        logging.debug("SENDING FINISH MESSAGE to EXTERNAL SUBTASK with id %s" % self.task_model.id)
        msg_data = {
            "action": "frestq.finish_external_task",
            "queue_name": INTERNAL_SCHEDULER_NAME,
            'sender_url': app.config.get('ROOT_URL'),
            'receiver_url': self.task_model.receiver_url,
            'input_data': data,
            'task_id': self.task_model.id
        }
        send_message(msg_data)

    def execute(self):
        '''
        Marks the task as executing, but waits for user
        '''
        if self.task_model.status in ['created', 'sent']:
            self.task_model.status = "executing"
            db.session.add(self.task_model)
            db.session.commit()
        elif self.task_model.status == "finished":
            self.execute_parent()

class SequentialTask(BaseTask):
    '''
    A sequential task executes a list of subtasks in order one after the other.
    This kind of task is "virtual" (as ParallelTask also is, for example). This
    means that:
     * it is a container task, which is always executed in the sender and thus
       it has no receiver
     * it has no specific action handler, process and returns no data by itself

    To add subtasks, call to add(). This can be done before or after this task
    has been created in the database, but it needs to be created to be executed
    properly.

    NOTE: When you send a SimpleTask to a receiver, the receiver sees it as a
    SequentialTask. This is the way we support distributed task composition.
    '''
    _subtasks = []

    def __init__(self, label=""):
        '''
        Constructor. Takes no arguments.
        '''
        super(SequentialTask, self).__init__()
        self._subtasks = []
        self.label = label

    @classmethod
    def _create_from_model(cls, task_model):
        ret = cls()
        ret.task_model = task_model
        ret._init_from_model()
        return ret

    def add(self, subtask):
        '''
        Adds a subtask to this sequential task, making this one its parent. The
        task is added to be executed after all previously added subtasks.
        '''
        if not self.task_model:
            self._subtasks.append(subtask)
            return

        model = subtask.create()
        model.order = self._count_subtasks()
        model.parent_id = self.task_model.id
        db.session.add(model)
        db.session.commit()

    def _count_subtasks(self):
        '''
        Internal. Count the number of subtasks. Only meant to be executed after
        the sequential task has been created in the database.
        '''
        return db.session.query(ModelTask).with_parent(self.task_model,
            "subtasks").count()

    def create(self):
        '''
        Create the task in the DB and returns the model. It also creates all the
        subtasks if they have not been created.
        '''

        # create task
        task_id = str(uuid4())
        logging.debug('CREATE local SEQUENTIAL TASK with ID %s' % task_id)
        kwargs = {
            'action': 'frestq.virtual_empty_task',
            'queue_name': INTERNAL_SCHEDULER_NAME,
            'label': self.label,
            'sender_url': app.config.get('ROOT_URL'),
            'receiver_url': app.config.get('ROOT_URL'),
            'is_received': False,
            'is_local': True,
            'sender_ssl_cert': app.config.get('SSL_CERT_STRING', ''),
            'input_data': dict(),
            'pingback_date': None,
            'expiration_date': None,
            'id': task_id,
            'status': 'created',
            'task_type': 'sequential',
            'parent_id': None
        }
        self.task_model = ModelTask(**kwargs)
        # fix broken FK bug, when child added to parent that does not yet exist
        db.session.add(self.task_model)
        # create also subtasks
        i = 0
        for subtask in self._subtasks:
            subtask_model = subtask.create()
            subtask_model.order = i
            subtask_model.parent_id = self.task_model.id
            db.session.add(subtask_model)
            i += 1
        # fix broken FK bug, when child added to parent that does not yet exist
        # db.session.add(self.task_model)
        db.session.commit()
        return self.task_model

    def next_subtask(self):
        '''
        Returns next subtask if any or None
        '''
        return db.session.query(ModelTask).with_parent(self.task_model, "subtasks").\
            filter(ModelTask.status != 'finished').order_by(ModelTask.order).first()

    def execute(self):
        '''
        After executing the task handler, this funcion is called once per each
        subtask, and executes each subtask sequentally and in order
        '''
        if self.task_model.status in ['created', 'sent']:
            self.task_model.status = "executing"
            db.session.add(self.task_model)
            db.session.commit()

        if self.task_model.status in ['finished', 'error']:
            return

        next_subtask_model = self.next_subtask()

        # check if there's no subtask left to do, and send the do next signal
        # for parent task if it has one, and send the finished update to the
        # sender if it's not local
        if not next_subtask_model:
            self.task_model.status = "finished"
            db.session.add(self.task_model)
            db.session.commit()

            # update the sender if any
            if not self.task_model.is_local:
                sched = FScheduler.get_scheduler(self.task_model.queue_name)
                sched.add_now_job(send_task_update, [self.task_model.id])


            # check if there's a parent task, and if so execute() it
            self.execute_parent()
            return

        if next_subtask_model.status == 'error':
            self.error = TaskError(dict(subtask_failed=next_subtask_model))
            self.propagate = True
            if self.action_handler_object:
                try:
                    self.action_handler_object.handle_error(self.error)
                except:
                    self.propagate = True

            if self.propagate:
                self.task_model.status = "finished" if not self.propagate else "error"
                db.session.add(self.task_model)
                db.session.commit()

            if not self.task_model.is_local:
                sched = FScheduler.get_scheduler(INTERNAL_SCHEDULER_NAME)
                sched.add_now_job(send_task_update, [self.task_model.id])

            # execute the task synchronously
            #
            # for simple task this function does nothing. For sequential tasks this spawns
            # the next subtask (or update sender status to finished), and for parallel
            # tasks it launches all subtasks
            self.execute_parent()
            return


        if next_subtask_model.status in ['sent', 'executing']:
            return

        # execute next subtask
        next_subtask = BaseTask.instance_by_model(next_subtask_model)
        next_subtask.execute()


def execute_task(task_id):
    '''
    Used to execute a task asynchronously
    '''
    task_model = db.session.query(ModelTask).get(task_id)
    task = BaseTask.instance_by_model(task_model)
    task.execute()


class ParallelTask(BaseTask):
    '''
    Very similar to SequentialTask, but will execute all subtasks in parallel.
    '''
    _subtasks = []

    def __init__(self, label=""):
        '''
        Constructor, takes no arguments as it is a virtual task.
        '''
        super(ParallelTask, self).__init__()
        self._subtasks = []
        self.label = label

    @classmethod
    def _create_from_model(cls, task_model):
        ret = cls()
        ret.task_model = task_model
        ret._init_from_model()
        return ret

    def add(self, subtask):
        '''
        Adds a subtask.
        '''
        if not self.task_model:
            self._subtasks.append(subtask)
            return

        model = subtask.create()
        model.parent_id = self.task_model.id
        db.session.add(model)
        db.session.commit()

    def create(self):
        '''
        Create the task in the DB and returns the model, creating any previously
        added subtasks.
        '''

        # create task
        task_id = str(uuid4())
        logging.debug('CREATE local PARALLEL TASK with ID %s' % task_id)
        kwargs = {
            'action': 'frestq.virtual_empty_task',
            'queue_name': INTERNAL_SCHEDULER_NAME,
            'label': self.label,
            'sender_url': app.config.get('ROOT_URL'),
            'receiver_url': app.config.get('ROOT_URL'),
            'is_received': False,
            'is_local': True,
            'sender_ssl_cert': app.config.get('SSL_CERT_STRING', ''),
            'input_data': dict(),
            'pingback_date': None,
            'expiration_date': None,
            'info_text': None,
            'id': task_id,
            'status': 'created',
            'task_type': 'parallel',
            'parent_id': None
        }
        self.task_model = ModelTask(**kwargs)
        # fix broken FK bug, when child added to parent that does not yet exist
        db.session.add(self.task_model)
        # create also subtasks
        i = 0
        for subtask in self._subtasks:
            subtask_model = subtask.create()
            subtask_model.parent_id = self.task_model.id
            db.session.add(subtask_model)
            i += 1
        # fix broken FK bug, when child added to parent that does not yet exist
        # db.session.add(self.task_model)
        db.session.commit()
        return self.task_model

    def count_unfinished_subtasks(self):
        '''
        Count the number of subtasks
        '''
        return db.session.query(ModelTask).with_parent(self.task_model,
            "subtasks").filter(ModelTask.status != 'finished').count()

    def next_subtask(self):
        '''
        Returns next subtask if any or None
        '''
        return db.session.query(ModelTask).with_parent(self.task_model, "subtasks").\
            filter(ModelTask.status != 'finished').order_by(ModelTask.order).first()

    def errored_tasks(self):
        '''
        Count the number of subtasks with error
        '''
        return db.session.query(ModelTask).with_parent(self.task_model,
            "subtasks").filter(ModelTask.status == 'error')

    def execute(self):
        '''
        After executing the task handler, this funcion is called once per each
        subtask, and executes each subtask sequentally and in order
        '''
        # if task is already errored, this has already been dealt with
        if self.task_model.status == 'error':
            return

        num_unfinished_subtasks = self.count_unfinished_subtasks()

        # if we find an error, propagate, as this kind of task do not have an
        # action handler that can stop it
        errored_tasks = self.errored_tasks()
        if errored_tasks.count() > 0:
            self.error = SubTasksFailed(errored_tasks)
            self.task_model.status = "error"
            db.session.add(self.task_model)
            db.session.commit()

            # propagate
            self.execute_parent()
            return

        # if this is the first time do next is called and there are subtasks,
        # let's mark this task as executing and start all the subtasks in
        # parallel
        if self.task_model.status in ['created', 'sent'] and num_unfinished_subtasks > 0:
            # mark as executing this task
            self.task_model.status = "executing"
            db.session.add(self.task_model)
            db.session.commit()

            # start subtasks in parallel
            subtasks = db.session.query(ModelTask).with_parent(self.task_model, "subtasks")
            for subtask in subtasks:
                sched = FScheduler.get_scheduler(subtask.queue_name)
                sched.add_now_job(execute_task, [subtask.id])
            return


        # check if there's no subtask left to do, and send the do next signal
        # for parent task if it has one
        if num_unfinished_subtasks == 0:
            # mark as finished
            self.task_model.status = "finished"
            db.session.add(self.task_model)
            db.session.commit()

            # check if there's a parent task, and if so execute() it
            self.execute_parent()


def send_synchronization_message(task_id):
    '''
    Used to send asynchronously a synchronization message to a subtask of a
    SynchronizedTask
    '''
    logging.debug("SENDING SYNC MESSAGE to SUBTASK with id %s" % task_id)
    task = ModelTask.query.get(task_id)
    msg = {
        "action": "frestq.synchronize_task",
        "queue_name": INTERNAL_SCHEDULER_NAME,
        "receiver_url": task.receiver_url,
        "receiver_ssl_cert": task.receiver_ssl_cert,
        "input_data": {
            'task_id': task_id,
            'action': task.action,
            'queue_name': task.queue_name,
            'pingback_date': task.pingback_date,
            'input_data': task.input_data,
            'expiration_date': task.expiration_date
        },
        "task_id": task.id
    }
    send_message(msg)
    task.last_modified_date = datetime.utcnow()
    db.session.add(task)
    db.session.commit()



class SynchronizedTask(BaseTask):
    '''
    Executes subtasks at the same time/synchronized. Before the subtasks are
    executed, some synchronization messages are sent to transparently assure
    that all the receivers are able to launch at the same time their respective
    tasks.

    The user of this task can take advantage of these synchronization messages
    by specifying an sychronization_handler, which will be executed exactly
    before the subtask will.
    This will allow to process the synchronization information recopilated from
    subtasks. In turn, subtasks can send this sychronization information
    specifying a task decorator parameter called "synchronization_handler".

    See sychronization example for more details on how this works.
    '''
    _subtasks = []

    handler = None

    def __init__(self, label="", handler=None):
        '''
        Constructor, takes no arguments as it is a virtual task.
        '''
        super(SynchronizedTask, self).__init__()
        self._subtasks = []
        self.label = label
        self.handler = handler

    @classmethod
    def _create_from_model(cls, task_model):
        ret = cls()
        ret.task_model = task_model
        ret._init_from_model()
        return ret

    def add(self, subtask):
        '''
        Adds a subtask.
        '''
        if not self.task_model:
            self._subtasks.append(subtask)
            return

        model = subtask.create()
        model.parent_id = self.task_model.id
        db.session.add(model)
        db.session.commit()

    def create(self):
        '''
        Create the task in the DB and returns the model, creating any previously
        added subtasks.
        '''

        # create task
        task_id = str(uuid4())
        logging.debug('CREATE local SYNCHRONIZED TASK with ID %s' % task_id)

        if self.handler:
            action = self.handler.action
        else:
            action = 'frestq.virtual_empty_task'

        kwargs = {
            'action': action,
            'queue_name': INTERNAL_SCHEDULER_NAME,
            'label': self.label,
            'sender_url': app.config.get('ROOT_URL'),
            'receiver_url': app.config.get('ROOT_URL'),
            'is_received': False,
            'is_local': True,
            'sender_ssl_cert': app.config.get('SSL_CERT_STRING', ''),
            'input_data': dict(),
            'pingback_date': None,
            'expiration_date': None,
            'info_text': None,
            'id': task_id,
            'status': 'created',
            'task_type': 'synchronized',
            'parent_id': None
        }
        self.task_model = ModelTask(**kwargs)
        # create also subtasks
        i = 0
        for subtask in self._subtasks:
            subtask_model = subtask.create()
            subtask_model.parent_id = self.task_model.id
            db.session.add(subtask_model)
            i += 1
        db.session.add(self.task_model)
        db.session.commit()
        return self.task_model

    def count_unfinished_subtasks(self):
        '''
        Count the number of subtasks
        '''
        return db.session.query(ModelTask).with_parent(self.task_model,
            "subtasks").filter(ModelTask.status != 'finished').count()

    def next_subtask(self):
        '''
        Returns next subtask if any or None
        '''
        return db.session.query(ModelTask).with_parent(self.task_model, "subtasks").\
            filter(ModelTask.status != 'finished').order_by(ModelTask.order).first()

    def errored_tasks(self):
        '''
        Count the number of subtasks with error
        '''
        return db.session.query(ModelTask).with_parent(self.task_model,
            "subtasks").filter(ModelTask.status == 'error')

    def execute(self):
        '''
        After executing the task handler, this function is
        '''
        # if task is already errored, this has already been dealt with
        if self.task_model.status == 'error':
            return

        num_unfinished_subtasks = self.count_unfinished_subtasks()

        # if we find an error, propagate, as this kind of task do not have an
        # action handler that can stop it
        errored_tasks = self.errored_tasks()
        if errored_tasks.count() > 0:
            self.error = SubTasksFailed(errored_tasks)
            self.task_model.status = "error"
            db.session.add(self.task_model)
            db.session.commit()

            # propagate
            self.execute_parent()
            return

        # if this is the first time do next is called and there are subtasks,
        # let's mark this task as executing and start doing the synchronization
        if self.task_model.status in ['created', 'sent']:
            self._synchronize()

        # check if there's no subtask left to do, and send the do next signal
        # for parent task if it has one
        elif num_unfinished_subtasks == 0:
            self._finish()

    def _synchronize(self):
        # mark as executing this task
        self.task_model.status = "executing"
        db.session.add(self.task_model)
        db.session.commit()

        # send initial synchronization message to subtasks
        subtasks = db.session.query(ModelTask).with_parent(self.task_model, "subtasks")
        for subtask in subtasks:
            sched = FScheduler.get_scheduler(INTERNAL_SCHEDULER_NAME)
            sched.add_now_job(send_synchronization_message, [subtask.id])

    def _finish(self):
        '''
        Called by execute when all tasks have finished
        '''
        # mark as finished
        self.task_model.status = "finished"
        db.session.add(self.task_model)
        db.session.commit()

        # check if there's a parent task, and if so execute() it
        self.execute_parent()


def send_message(msg_data, update_task_receiver_ssl_cert=False, task=None):
    '''
    Sends a message to a peer using RESTQP protocol. Assumes the following
    required fields in msg_data:
    * action
    * queue_name
    * receiver_url

    And the following optional fields:
    * receiver_ssl_cert
    * input_data
    * task_id
    * pingback_date
    * expiration_date
    * info
    '''

    # create message and save it in the database
    msg_data = msg_data.copy()
    msg_data['id'] =  str(uuid4())
    msg_data['is_received'] = False
    msg_data['sender_url'] = app.config.get('ROOT_URL')
    msg_data['sender_ssl_cert'] = app.config.get('SSL_CERT_STRING', '')
    msg = ModelMessage(**msg_data)

    # send it to the peer
    url =  "%s/%s/" % (msg_data['receiver_url'], msg_data['queue_name'])
    payload = {
        'message_id': msg.id,
        'action': msg.action,
        'sender_url': msg.sender_url,
        "data": msg_data.get('input_data', '')
    }
    opts = ['async_data', 'task_id', 'pingback_date', 'expiration_date', 'info']
    for opt in opts:
        if opt in msg_data and msg_data[opt] != None:
            payload[opt] = msg_data[opt]

    logging.debug('SENDING MESSAGE id %s with action %s to %s' % (
        msg.id, msg.action, url))

    # msg is saved before sending the message so that it's registered (it might
    # get even be retrieved from DB by api.py:post_message() if it's a local
    # message, but it's also updated when the msg is sent to update output
    db.session.add(msg)
    db.session.commit()

    session = requests.sessions.Session()

    if app.config.get('SSL_CERT_PATH', ''):
        # verification is done later
        r = session.request('post', url, data=dumps(payload), verify=False,
                          cert=(app.config.get('SSL_CERT_PATH', ''),
                                app.config.get('SSL_KEY_PATH', '')))

        # convert the asn1 cert retrieved from the socket into pem format
        try:
            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, r.raw.peer_cert)
            msg.receiver_ssl_cert = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
            if update_task_receiver_ssl_cert and task:
                task.receiver_ssl_cert = msg.receiver_ssl_cert
        except Exception, e:
            pass

    else:
        r = session.request('post', url, data=dumps(payload))


    # TODO: check r.status_code and do some retries if it failed
    msg.output_status = r.status_code

    db.session.add(msg)
    db.session.commit()


class TaskError(Exception):
    '''
    Exception that can be thrown during the execution of a task to indicate
    something went wrong.

    This kind of exception propagates to parent task recursively. This can only
    be stopped by the error handler of a task, if any.
    '''
    def __init__(self, data):
        self.data = data


class SubTasksFailed(TaskError):
    def __init__(self, subtasks):
        self.subtasks = subtasks


def send_task_update(task_id):
    '''
    Sends to the task creator (which is not us) an update with the task
    information. Currently, the information sent is:
    task.output_data
    task.output_status
    '''
    logging.debug("SENDING UPDATE to TASK with id %s" % task_id)
    task = ModelTask.query.get(task_id)
    update_msg = {
        "action": "frestq.update_task",
        "queue_name": INTERNAL_SCHEDULER_NAME,
        "receiver_url": task.sender_url,
        "receiver_ssl_cert": task.sender_ssl_cert,
        "input_data": {
            'output_data': task.output_data,
            'status': task.status
        },
        "task_id": task.id
    }
    logging.debug("update_msg.inputdata: %s" % dumps(update_msg["input_data"]))
    send_message(update_msg)
    task.last_modified_date = datetime.utcnow()
    db.session.add(task)
    db.session.commit()

    # task finished. check if there's a parent task, and if so execute() it
    if task.parent_id:
        parent = db.session.query(ModelTask).get(task.parent_id)
        parent_task = BaseTask.instance_by_model(parent)
        parent_task.execute()

def update_task(task, task_output):
    '''
    Updates a task
    '''
    if not isinstance(task_output, dict):
        return

    commit = False

    if 'output_data' in task_output:
        commit = True
        task.task_model.output_data = task_output['output_data']

    if 'output_status' in task_output:
        commit = True
        task.task_model.output_data = task_output['output_status']

    if commit:
        db.session.add(task.task_model)
        db.session.commit()

def post_task(msg, action_handler):
    '''
    Called by api.post_message when action_handler is of type "task". Creates
    the requested task and processes it.
    '''

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


    # if msg originated from ourselves, it might already exist. or if it's a
    # subtask of a synchronized task
    task_model = db.session.query(ModelTask).filter(ModelTask.id == msg.task_id).first()
    if task_model:
        if task_model.task_type == 'simple':
            # this could happen if the task was created with SimpleTask
            task_model.task_type = 'sequential'
            db.session.add(task_model)
            db.session.commit()
    else:
        task_model = ModelTask(**kwargs)
        db.session.add(task_model)
        db.session.commit()

    # 2. call to the handler
    task = BaseTask.instance_by_model(task_model)
    try:
        task_output = task.run_action_handler()
        if task_output:
            update_task(task, task_output)
    except Exception, e:
        import traceback; traceback.print_exc()
        task.error = e
        task.propagate = True
        if task.action_handler_object:
            try:
                task.action_handler_object.handle_error(e)
            except:
                task.propagate = True
            print "after error handler task(%s).propagate(%s)" % (task_model.id, task.propagate)

    # 3. update asynchronously the task sender if requested
    if task.auto_finish_after_handler or task.propagate:
        task_model.status = "finished" if not task.propagate else "error"
        db.session.add(task_model)
        db.session.commit()

    if task.send_update_to_sender:
        sched = FScheduler.get_scheduler(INTERNAL_SCHEDULER_NAME)
        sched.add_now_job(send_task_update, [task_model.id])

    # 4. execute the task synchronously
    #
    # for simple task this function does nothing. For sequential tasks this spawns
    # the next subtask (or update sender status to finished), and for parallel
    # tasks it launches all subtasks
    if task.propagate:
        task.execute_parent()
    else:
        task.execute()
