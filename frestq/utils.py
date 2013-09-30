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

import datetime
import json

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
        if isinstance(v, basestring):
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

def list_tasks(args):
    '''
    Prints the list of tasks
    '''
    from .app import db
    from .models import Task

    filters=[]
    for filter in args.filters:
        key, value = filter.split("=")
        filters.append(getattr(Task, key).__eq__(value))

    if filters:
        tasks = db.session.query(Task).filter(*filters)
    else:
        tasks = db.session.query(Task)
    tasks = tasks.order_by(Task.created_date.desc()).limit(args.limit)

    table = PrettyTable(['small id', 'sender_url', 'action', 'queue',
                         'task_type', 'status', 'created_date'])

    for task in tasks:
        table.add_row([str(task.id)[:8], task.sender_url, task.action,
                       task.queue_name, task.task_type, task.status,
                       task.created_date])
    print table

def list_messages(args):
    '''
    Prints the list of messages
    '''
    from .app import db
    from .models import Message

    filters=[]
    for filter in args.filters:
        key, value = filter.split("=")
        filters.append(getattr(Message, key).__eq__(value))

    if filters:
        msgs = db.session.query(Message).filter(*filters)
    else:
        msgs = db.session.query(Message)

    msgs = msgs.order_by(Message.created_date.desc()).limit(args.limit)
    table = PrettyTable(['small id', 'sender_url', 'action', 'queue', 'created_date', 'input_data'])
    for msg in msgs:
        table.add_row([str(msg.id)[:8], msg.sender_url, msg.action, msg.queue_name,
                       msg.created_date, str(msg.input_data)[:30]])
    print table

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

        print "%(indent)s %(action)s.%(queue)s - %(task_type)s (%(extra)s)" % dict(
            indent=indent,
            action=task.action,
            queue=task.queue_name,
            task_type=task.task_type,
            extra=", ".join(extra))
    else:
        print dumps(task.to_dict(), indent=4)

def traverse_tasktree(task, visitor_func, visitor_kwargs):
    visitor_func(task, **visitor_kwargs)

    from .app import db
    from .models import Task

    subtasks = db.session.query(Task)\
        .with_parent(task, "subtasks")\
        .order_by(Task.order)
    for subtask in subtasks:

        vargs = visitor_kwargs.copy()
        vargs['level'] += 1
        traverse_tasktree(subtask, visitor_func, vargs)

def show_task(args):
    from .app import db
    from .models import Task
    task_id = unicode(args.show)
    task_model = db.session.query(Task).filter(Task.id.startswith(task_id)).all()
    if not task_model:
        print "task %s not found" % task_id
        return
    task_model = task_model[0]
    print_task(task_model)

def show_external_task(args):
    from .app import db
    from .models import Task

    task_id = unicode(args.show_external)
    task_model = db.session.query(Task).filter(Task.id.startswith(task_id)).all()

    if not task_model:
        print "task %s not found" % task_id
        return
    task_model = task_model[0]

    if task_model.task_type != "external":
        print "task %s is not external" % task_id
        return

    print_task(task_model, mode="oneline")
    print "label: %s" % task_model.label
    print "info_text:\n%s" % task_model.input_data

def finish_task(args):
    from .app import db
    from .models import Task
    from .tasks import ExternalTask

    task_id = unicode(args.finish[0])
    try:
        finish_data = loads(unicode(args.finish[1]))
    except:
        print "error loading the json finish data"
        return

    task_model = db.session.query(Task).filter(Task.id.startswith(task_id)).all()

    if not task_model:
        print "task %s not found" % task_id
        return
    task_model = task_model[0]

    if task_model.task_type != "external":
        print "task %s is not external" % task_id
        return

    task = ExternalTask.instance_by_id(task_model.id)
    task.finish(data=finish_data)


def deny_task(args):
    # TODO not implemented
    pass

def task_tree(args):
    from .app import db
    from .models import Task
    task_id = unicode(args.tree)
    task_model = db.session.query(Task).filter(Task.id.startswith(task_id)).all()
    if not task_model:
        print "task %s not found" % task_id
        return
    task_model = task_model[0]
    if args.with_parents:
        while task_model.parent_id:
            try:
                task_model = db.session.query(Task).get(task_model.parent_id)
            except:
                print "task %s, which is the parent of %s not found" % (
                    str(task.parent_id)[:8],
                    str(task.id)[:8],
                )
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