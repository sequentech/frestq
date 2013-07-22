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

def dumps(obj):
    '''
    dumps that also decodes datetimes
    '''
    return json.dumps(obj, cls=JSONDateTimeEncoder)

def loads(obj):
    '''
    loads that also encodes datetimes
    '''
    return json.loads(obj, object_hook=datetime_decoder)

def list_tasks(args):
    from .app import db
    from .models import Task
    tasks = db.session.query(Task).order_by(Task.created_date.desc()).limit(args.limit)
    table = PrettyTable(['small id', 'sender_url', 'action', 'queue', 'status', 'created_date'])
    for task in tasks:
        table.add_row([str(task.id)[:8], task.sender_url, task.action, task.queue_name,
                       task.status, task.created_date])
    print table

def list_messages(args):
    from .app import db
    from .models import Message
    msgs = db.session.query(Message).order_by(Message.created_date.desc()).limit(args.limit)
    table = PrettyTable(['small id', 'sender_url', 'action', 'queue', 'created_date', 'input_data'])
    for msg in msgs:
        table.add_row([str(msg.id)[:8], msg.sender_url, msg.action, msg.queue_name,
                       msg.created_date, str(msg.input_data)[:30]])
    print table
