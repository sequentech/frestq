# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2013-2021 Sequent Tech Inc <legal@sequentech.io>
# SPDX-FileCopyrightText: 2014-2021 Sequent Tech Inc <legal@sequentech.io>
#
# SPDX-License-Identifier: AGPL-3.0-only

import datetime
import os
import json
import codecs

from prettytable import PrettyTable

__all__ = ['dumps', 'loads']

class JSONDateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        else:
            return json.JSONEncoder.default(self, obj)

def datetime_decoder(d):
    if isinstance(d, list):
        pairs = enumerate(d)
    elif isinstance(d, dict):
        pairs = d.items()
    result = []
    for k,v in pairs:
        # NOTE: change in year 2099
        if isinstance(v, str) and v.startswith("20"):
            try:
                v = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                pass
        elif isinstance(v, (dict, list)):
            v = datetime_decoder(v)
        result.append((k, v))
    if isinstance(d, list):
        return [x[1] for x in result]
    elif isinstance(d, dict):
        return dict(result)

def dumps(obj, **kwargs):
    '''
    dumps that also decodes datetimes
    '''
    return json.dumps(obj, cls=JSONDateTimeEncoder, **kwargs)

def loads(obj, **kwargs):
    '''
    loads that also encodes datetimes
    '''
    return json.loads(obj, object_hook=datetime_decoder, **kwargs)

# drb
def get_tasks(args):
    from .app import app
    from .models import Task

    filters=[]
    for filter in args.filters:
        key, value = filter.split("=")
        filters.append(getattr(Task, key).__eq__(value))

    if filters:
        tasks = app.db.session.query(Task).filter(*filters)
    else:
        tasks = app.db.session.query(Task)
    tasks = tasks.order_by(Task.created_date.desc()).limit(args.limit)

    return tasks

# drb
def list_tasks(args):
    '''
    Prints the list of tasks
    '''
    tasks = get_tasks(args)

    table = PrettyTable(['small id', 'sender_url', 'action', 'queue',
                         'task_type', 'status', 'created_date'])

    for task in tasks:
        dict = task.to_dict()
        table.add_row([str(task.id)[:8], task.sender_url, task.action,
                       task.queue_name, task.task_type, task.status,
                       task.created_date])
    print(table)

def list_messages(args):
    '''
    Prints the list of messages
    '''
    from .app import app
    from .models import Message

    filters=[]
    for filter in args.filters:
        key, value = filter.split("=")
        filters.append(getattr(Message, key).__eq__(value))

    if filters:
        msgs = app.db.session.query(Message).filter(*filters)
    else:
        msgs = app.db.session.query(Message)

    msgs = msgs.order_by(Message.created_date.desc()).limit(args.limit)
    table = PrettyTable(['small id', 'sender_url', 'action', 'queue', 'created_date', 'input_data'])
    for msg in msgs:
        table.add_row([str(msg.id)[:8], msg.sender_url, msg.action, msg.queue_name,
                       msg.created_date, str(msg.input_data)[:30]])
    print(table)

def print_task(task, base_task_id=None, level=0, mode="full"):
    '''
    Prints a task. Available modes are: full and oneline. level is used only
    in oneline mode.
    '''
    if mode == 'oneline':
        if level == 0:
            indent = " *"
        elif level == 1:
            indent = "   |-"
        elif level > 1:
            indent = "   " + "|  " * (level - 1) + "|-"

        extra = [str(task.id)[:8], task.status]
        if extra[0] == base_task_id:
            extra.append('root')

        print("%(indent)s %(action)s.%(queue)s - %(task_type)s (%(extra)s)" % dict(
            indent=indent,
            action=task.action,
            queue=task.queue_name,
            task_type=task.task_type,
            extra=", ".join(extra)))
    else:
        print(dumps(task.to_dict(), indent=4))

def traverse_tasktree(task, visitor_func, visitor_kwargs):
    visitor_func(task, **visitor_kwargs)

    from .app import app
    from .models import Task

    subtasks = app.db.session.query(Task)\
        .with_parent(task, "subtasks")\
        .order_by(Task.order)
    for subtask in subtasks:

        vargs = visitor_kwargs.copy()
        vargs['level'] += 1
        traverse_tasktree(subtask, visitor_func, vargs)

def show_task(args):
    from .app import app
    from .models import Task
    task_id = unicode(args.show_task)
    task_model = app.db.session.query(Task).filter(Task.id.startswith(task_id)).all()
    if not task_model:
        print("task %s not found" % task_id)
        return
    task_model = task_model[0]
    print_task(task_model)

def constant_time_compare(val1, val2):
    """
    Returns True if the two strings are equal, False otherwise.
    The time taken is independent of the number of characters that match.
    For the sake of simplicity, this function executes in constant time only
    when the two strings have the same length. It short-circuits when they
    have different lengths. Since Django only uses it to compare hashes of
    known expected length, this is acceptable.
    """
    if len(val1) != len(val2):
        return False
    result = 0
    for x, y in zip(val1, val2):
        result |= ord(x) ^ ord(y)
    return result == 0

def show_activity(args):
    from .app import app
    root_path = app.config.get('ROOT_PATH', "")
    activity_path = os.path.join(root_path, "activity.json.log")
    data = dict(
      start_date=None,
      pools=dict()
    )
    with codecs.open(activity_path, encoding='utf-8', mode='r') as activity_f:
        for line in activity_f:
            action = json.loads(line)
            action_name = action['activity']['action']
            if action_name == 'START':
                data = dict(
                    start_date=action['time'],
                    pools=dict()
                )
            elif action_name == 'CREATE_QUEUE':
                queue_name = action['activity']['queue']
                if queue_name in data['pools']:
                    continue
                data['pools'][queue_name] = dict(
                    creation_date=action['time'],
                    executing=[],
                    errors=0)
            elif action_name == 'SET_QUEUE_MAX':
                queue_name = action['activity']['queue']
                if queue_name not in data['pools']:
                    data['pools'][queue_name] = dict(
                        creation_date=action['time'],
                        executing=[],
                        errors=0)
                data['pools'][queue_name]['max'] = action['activity']['max']
            elif action_name == 'EVENT_JOB_LAUNCHING':
                queue_name = action['activity']['queue']
                task = dict(
                    func_name=action['activity']['func_name'],
                    launch_time=action['time']
                )
                if queue_name not in data['pools']:
                    print("error, launching event in an inexistant queue? queue '%s'" % queue_name)
                    continue
                data['pools'][queue_name]['executing'].append(task)
            elif action_name == 'EVENT_JOB_ERROR':
                queue_name = action['activity']['queue']
                func_name=action['activity']['func_name']
                found = False
                if queue_name not in data['pools']:
                    print("error, error of an event in an inexistant queue? queue '%s'" % queue_name)
                    continue
                for task in data['pools'][queue_name]['executing']:
                    if task['func_name'] == func_name:
                        data['pools'][queue_name]['executing'].remove(task)
                        found = True
                        break
                if not found:
                    print("error,r error of an unregistered event in queue '%s'" % queue_name)
                ['pools'][queue_name]['errors'] += 1
            elif action_name == 'EVENT_JOB_EXECUTED':
                queue_name = action['activity']['queue']
                func_name=action['activity']['func_name']
                found = False
                if queue_name not in data['pools']:
                    print("error, error of an event in an inexistant queue? queue '%s'" % queue_name)
                    continue
                for task in data['pools'][queue_name]['executing']:
                    if task['func_name'] == func_name:
                        data['pools'][queue_name]['executing'].remove(task)
                        found = True
                        break
                if not found:
                    print("error, finished an unregistered event in queue '%s'" % queue_name)

    print(json.dumps(data, indent=4, sort_keys=True, ensure_ascii=False))


def show_message(args):
    from .app import app
    from .models import Message
    msg_id = unicode(args.show_message)
    msg_model = app.db.session.query(Message).filter(Message.id.startswith(msg_id)).all()
    if not msg_model:
        print("message %s not found" % msg_id)
        return
    msg_model = msg_model[0]
    print(dumps(msg_model.to_dict(), indent=4))

# drb
def get_external_task(args):
    from .app import app
    from .models import Task

    task_id = unicode(args.show_external)
    task_model = app.db.session.query(Task).filter(Task.id.startswith(task_id)).all()

    return task_model

# drb
def show_external_task(args):

    task_id = unicode(args.show_external)
    task_model = get_external_task(args)

    if not task_model:
        print("task %s not found" % task_id)
        return
    task_model = task_model[0]

    if task_model.task_type != "external":
        print("task %s is not external" % task_id)
        return

    print_task(task_model, mode="oneline")
    print("label: %s" % task_model.label)
    print("info_text:\n%s" % task_model.input_data)

def finish_task(args):
    from .app import app
    from .models import Task
    from .tasks import ExternalTask

    task_id = unicode(args.finish[0])
    try:
        finish_data = loads(unicode(args.finish[1]))
    except:
        print("error loading the json finish data")
        return

    task_model = app.db.session.query(Task).filter(Task.id.startswith(task_id)).all()

    if not task_model:
        print("task %s not found" % task_id)
        return
    task_model = task_model[0]

    if task_model.task_type != "external":
        print("task %s is not external" % task_id)
        return

    task = ExternalTask.instance_by_id(task_model.id)
    task.finish(data=finish_data)


def deny_task(args):
    # TODO not implemented
    pass

def task_tree(args):
    from .app import app
    from .models import Task
    task_id = unicode(args.tree)
    task_model = app.db.session.query(Task).filter(Task.id.startswith(task_id)).all()
    if not task_model:
        print("task %s not found" % task_id)
        return
    task_model = task_model[0]
    if args.with_parents:
        while task_model.parent_id:
            try:
                task_model = app.db.session.query(Task).get(task_model.parent_id)
            except:
                print("task %s, which is the parent of %s not found" % (
                    str(task.parent_id)[:8],
                    str(task.id)[:8],
                ))
                break

    level = 0
    traverse_tasktree(task=task_model, visitor_func=print_task,
        visitor_kwargs=dict(base_task_id=task_id, level=0, mode="oneline"))

class DecoratorBase(object):
    func = None

    def __init__(self, func):
        self.func = func

    def __getattribute__(self, name):
        if name == "func":
            return super(DecoratorBase, self).__getattribute__(name)

        return self.func.__getattribute__(name)

    def __setattr__(self, name, value):
        if name == "func":
            return super(DecoratorBase, self).__setattr__(name, value)

        return self.func.__setattr__(name, value)