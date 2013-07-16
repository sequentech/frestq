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
import logging
from threading import Condition
from datetime import datetime, timedelta

from flask import Blueprint, request, make_response

from .action_handlers import ActionHandlers
from . import decorators
from .fscheduler import FScheduler, INTERNAL_SCHEDULER_NAME
from .utils import dumps

@decorators.message_action(action="frestq.update_task", queue=INTERNAL_SCHEDULER_NAME)
def update_task(msg):
    from .app import db
    from .models import Task as ModelTask
    from .tasks import ReceiverTask

    task = msg.task
    logging.debug("UPDATING TASK with id %s" % task.id)
    if task.status == "finished" and msg.input_data['status'] != 'error':
        # error, cannot update an already finished task (unless it's an error)!
        # TODO: send back an error update
        return

    keys = ['output_data', 'status']
    for key in keys:
        if key in msg.input_data:
            if isinstance(msg.input_data[key], basestring):
                logging.debug("SETTING TASK FIELD '%s' to '%s'" % (key,
                    msg.input_data[key]))
            else:
                logging.debug("SETTING TASK FIELD '%s' to: %s" % (key,
                    dumps(msg.input_data[key])))
            setattr(task, key, msg.input_data[key])
    task.last_modified_date = datetime.utcnow()
    db.session.add(task)
    db.session.commit()

    # do next (it might be a task with a parent task)
    receiver_task = ReceiverTask.instance_by_model(task)
    receiver_task.execute()

# used to notify reserve threads about events
_reserve_condition = Condition()

def reserve_task(task_id):
    '''
    This executes the synchronization negotiation details for a synchronized
    task from the receiver's point of view. When synced, this also executes the
    task.
    '''
    from .app import db, app
    from .models import Task as ModelTask
    from .tasks import ReceiverTask

    # 1. get task and check everything is ok
    task = db.session.query(ModelTask).filter(ModelTask.id == task_id).first()
    if not task or task.status != 'syncing':
        # probably means we timedout or maybe there was some kind of error, so
        # we finish here
        return

    # 2. generate reservation data
    task_instance = ReceiverTask.instance_by_model(task)
    if task_instance.action_handler_object:
        reservation_data = task_instance.action_handler_object.reserve()
        task.reservation_data = reservation_data

    # 3. send reserved message to sender
    task.status = 'reserved'
    task.last_modified_date = datetime.utcnow()
    db.session.add(task)
    db.session.commit()
    ack_reservation(task_id)

    # 4. set reservation timeout
    sched = FScheduler.get_scheduler(INTERNAL_SCHEDULER_NAME)
    date = datetime.utcnow() + timedelta(seconds=app.config.get('RESERVATION_TIMEOUT'))
    sched.add_date_job(cancel_reserved_subtask, date, [task.id])

    # 5. wait for a cancel or execute message
    with _reserve_condition:
        while True:
            _reserve_condition.wait()
            # fetch again the task to get the newly obtained status info
            db.session.commit()
            task = db.session.query(ModelTask).filter(ModelTask.id == task_id).first()

            # we probably received a _reserve_condition that was sent to another thread
            # because our task didn't change state, so we ignore the signal
            if task.status == 'reserved':
                continue

            # timedout, notify and exit thread
            elif task.status == 'created':
                logging.debug("TASK TIMEDOUT with id %s", task.id)
                return

            # 6. task received confirmation, we're ready to finally execute the task
            elif task.status == 'confirmed':
                logging.debug("EXECUTING synchronized SUBTASK with id %s, "\
                    "action = %s" % (task.id, task.action))
                # adapted from the final part of tasks.py:post_task() function
                from .tasks import ReceiverTask, update_task
                task_model = task
                task_model.status = 'executing'
                task_model.last_modified_date = datetime.utcnow()
                db.session.add(task_model)
                db.session.commit()

                task = ReceiverTask.instance_by_model(task_model)
                task_output = task.run_action_handler()
                if task_output:
                    update_task(task, task_output)

                # 7. update asynchronously the task sender if requested
                if task.auto_finish_after_handler:
                    task_model.status = "finished"
                    task_model.last_modified_date = datetime.utcnow()
                    db.session.add(task_model)
                    db.session.commit()

                if task.send_update_to_sender:
                    sched = FScheduler.get_scheduler(INTERNAL_SCHEDULER_NAME)
                    sched.add_now_job(send_task_update, [task_model.id, task_output])

                # 8. execute the task synchronously
                #
                # for simple task this function does nothing. For sequential tasks this spawns
                # the next subtask (or update sender status to finished), and for parallel
                # tasks it launches all subtasks
                task.execute()
                return

def cancel_reserved_subtask(task_id):
    '''
    Cancels a reserved task. This is done by setting the task to created and
    then sending a notification to the condition, so that the waiting threads
    (among which the correct one will be) will wake up take the notice.

    Note: this task is executed in cases where the task can be either local and
    not local.
    '''
    from .app import db
    from .models import Task as ModelTask
    from .tasks import ReceiverTask

    task = db.session.query(ModelTask).filter(ModelTask.id == task_id).first()

    task_instance = ReceiverTask.instance_by_model(task)
    # task action_handler_object might not be present, it's not mandatory, and
    # only provided in the task receiver node
    if task_instance.action_handler_object:
        task_instance.action_handler_object.cancel_reservation()

    if task.status not in ['syncing', 'reserved']:
        return

    task.status = "created"
    task.last_modified_date = datetime.utcnow()
    db.session.add(task)
    db.session.commit()
    with _reserve_condition:
        _reserve_condition.notify_all()

def ack_reservation(task_id):
    '''
    Sends a confirmation of a task reservation to task sender
    '''
    from .app import db, app
    from .models import Task as ModelTask
    from .tasks import send_message

    task = db.session.query(ModelTask).filter(ModelTask.id == task_id).first()
    if not task or task.status != 'reserved':
        return

    # reservation_timeout is also sent

    logging.debug("SENDING ACK RESERVATION TO SENDER of task with id %s", task_id)
    date = datetime.utcnow() + timedelta(seconds=app.config.get('RESERVATION_TIMEOUT'))
    task = ModelTask.query.get(task_id)
    msg = {
        "action": "frestq.confirm_task_reservation",
        "queue_name": INTERNAL_SCHEDULER_NAME,
        "receiver_url": task.sender_url,
        "receiver_ssl_cert": task.sender_ssl_cert,
        "input_data": {
            'reservation_data': task.reservation_data,
            'reservation_expiration_date': date,
        },
        "task_id": task.id
    }
    send_message(msg)

@decorators.message_action(action="frestq.synchronize_task", queue=INTERNAL_SCHEDULER_NAME)
def synchronize_task(msg):
    '''
    Receives a task that needs to be synchronized because its parent is a
    SynchronizedTask
    '''
    from .app import db, app
    from .models import Task as ModelTask

    logging.debug("SYNCING TASK with id %s" % msg.task_id)
    task = db.session.query(ModelTask).filter(ModelTask.id == msg.task_id).first()
    if task and task.status != 'created':
        # error, cannot update an already finished task (unless it's an error)!
        # TODO: send back an error update
        return

    # 1. create received task if needed
    is_local = msg.sender_url == app.config.get('ROOT_URL')
    if not task:
        kwargs = {
            'action': msg.input_data['action'],
            'queue_name': msg.input_data['queue_name'],
            'sender_url': msg.sender_url,
            'receiver_url': msg.receiver_url,
            'is_received': msg.is_received,
            'is_local': is_local,
            'sender_ssl_cert': msg.sender_ssl_cert,
            'input_data': msg.input_data['input_data'],
            'pingback_date': msg.input_data['pingback_date'],
            'expiration_date': msg.input_data['expiration_date'],
            'status': 'syncing',
            'id': msg.task_id,
            'task_type': 'sequential'
        }
        task = ModelTask(**kwargs)
        db.session.add(task)
        db.session.commit()
    else:
        if is_local and task.task_type == 'simple':
            # this could happen if the task was created with SimpleTask
            task.task_type = 'sequential'

        task.status = 'syncing'
        task.last_modified_date = datetime.utcnow()
        db.session.add(task)
        db.session.commit()

    sched = FScheduler.get_scheduler(task.queue_name)
    sched.add_now_job(reserve_task, [task.id])

    # schedule expiration
    if task.expiration_date:
        sched = FScheduler.get_scheduler(INTERNAL_SCHEDULER_NAME)
        date = datetime.utcnow() + timedelta(seconds=app.config.get('RESERVATION_TIMEOUT'))
        sched.add_date_job(cancel_reserved_subtask, date, [task.id])


@decorators.message_action(action="frestq.confirm_task_reservation", queue=INTERNAL_SCHEDULER_NAME)
def director_confirm_task_reservation(msg):
    '''
    Director of a synchronized task receives a task reservation
    '''
    from .app import db
    from .models import Task as ModelTask
    from .tasks import ReceiverTask, send_synchronization_message

    task = db.session.query(ModelTask).filter(ModelTask.id == msg.task_id).first()
    task_instance = ReceiverTask.instance_by_model(task)
    parent_instance = task_instance.get_parent()

    # it can be reserved if it's local
    if not task or task.status not in ['created', 'syncing', 'reserved'] or\
        parent_instance.task_model.status != 'executing':
        # unhandled state
        return

    task.status = 'reserved'
    task.reservation_data = msg.input_data.get('reservation_data', None)
    task.last_modified_date = datetime.utcnow()
    db.session.add(task)
    db.session.commit()

    logging.debug("CONFIRMED TASK RESERVATION with id %s" % msg.task_id)

    # set reservation timeout
    sched = FScheduler.get_scheduler(INTERNAL_SCHEDULER_NAME)
    date = msg.input_data['reservation_expiration_date']
    sched.add_date_job(director_cancel_reserved_subtask, date, [task.id])

    # call to the new_reservation handler
    if parent_instance.action_handler_object:
        parent_instance.action_handler_object.new_reservation(task_instance)

    # find any unreserved task, send reservation
    not_reserved_children_num = 0
    for child in parent_instance.get_children():
        if child.task_model.status == 'created':
            not_reserved_children_num += 1
            sched.add_now_job(send_synchronization_message, [child.task_model.id])

    # continue to do subtasks starting only if all are reserved
    if not_reserved_children_num != 0:
        return

    parent_instance.action_handler_object.pre_execute()

    # start all children in parallel
    for child in parent_instance.get_children():
        sched.add_now_job(director_synchronized_subtask_start, [child.task_model.id])

def director_cancel_reserved_subtask(task_id):
    '''
    Cancel a task because a reservation timeout in the director node
    '''
    from .app import db
    from .models import Task as ModelTask
    from .tasks import ReceiverTask

    task = db.session.query(ModelTask).filter(ModelTask.id == task_id).first()
    task_instance = ReceiverTask.instance_by_model(task)
    task_instance.get_parent().action_handler_object.cancelled_reservation(task_instance)

    if task.status != 'reserved':
        return

    task.status = "created"
    task.last_modified_date = datetime.utcnow()
    db.session.add(task)
    db.session.commit()

    #if all tasks are created, it means all tasks have expired, so we cannot
    #wait for a confirmation that will launch again all the expired tasks.
    #Conclusion: we send the reservations here
    sched = FScheduler.get_scheduler(INTERNAL_SCHEDULER_NAME)
    for child in parent_instance.get_children():
        if child.task_model.status != 'created':
            return

    # find any unreserved task, send reservation
    for child in parent_instance.get_children():
        if child.task_model.status == 'created':
            sched.add_now_job(send_synchronization_message, [child.task_model.id])

def director_synchronized_subtask_start(task_id):
    '''
    Launch the execution of a subtask
    '''
    from .app import db
    from .models import Task as ModelTask
    from .tasks import send_message

    task = ModelTask.query.get(task_id)
    if task.status != 'reserved':
        # ERROR!
        return

    # reservation_timeout is also sent
    task = ModelTask.query.get(task_id)
    msg = {
        "action": "frestq.execute_synchronized",
        "queue_name": INTERNAL_SCHEDULER_NAME,
        "receiver_url": task.receiver_url,
        "receiver_ssl_cert": task.receiver_ssl_cert,
        "input_data": {
            'action': task.action,
            'queue_name': task.queue_name,
            'input_data': task.input_data,
        },
        "task_id": task.id
    }
    send_message(msg)


@decorators.message_action(action="frestq.execute_synchronized", queue=INTERNAL_SCHEDULER_NAME)
def execute_synchronized(msg):

    from .app import db
    from .models import Task as ModelTask
    from .api import call_action_handler
    from .fscheduler import FScheduler
    from .tasks import ReceiverTask, post_task

    task = ModelTask.query.get(msg.task_id)
    if task.status != 'reserved':
        # ERROR!
        return

    task_instance = ReceiverTask.instance_by_model(task)
    task.input_data = msg.input_data['input_data']
    task.status = "confirmed"
    task.last_modified_date = datetime.utcnow()
    db.session.add(task)
    db.session.commit()
    with _reserve_condition:
        _reserve_condition.notify_all()