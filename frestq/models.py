#!/usr/bin/env python
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

from sqlalchemy.types import TypeDecorator, VARCHAR
from flask import Flask, jsonify
from flask.ext.sqlalchemy import SQLAlchemy

from .app import db


class JSONEncodedDict(TypeDecorator):
    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if not value:
            return None
        return json.loads(value)

class Message(db.Model):
    '''
    Represents an election
    '''
    __tablename__ = 'message'

    id = db.Column(db.Unicode(128), primary_key=True)

    sender_url = db.Column(db.Unicode(1024))

    queue_name = db.Column(db.Unicode(1024))

    is_received = db.Column(db.Boolean)

    receiver_url = db.Column(db.Unicode(1024))

    sender_ssl_cert = db.Column(db.UnicodeText)

    receiver_ssl_cert = db.Column(db.UnicodeText)

    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    action = db.Column(db.Unicode(1024))

    input_data = db.Column(JSONEncodedDict)

    input_async_data = db.Column(JSONEncodedDict)

    output_status = db.Column(db.Integer)

    pingback_date = db.Column(db.DateTime, default=None)

    expiration_date = db.Column(db.DateTime, default=None)

    info_text = db.Column(db.Unicode(2048))

    task_id = db.Column(db.Unicode(128), db.ForeignKey('task.id'))

    task = db.relationship('Task',
        backref=db.backref('messages', lazy='dynamic'))

    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def __repr__(self):
        return '<Message %r>' % self.id

    def to_dict(self, full=False):
        '''
        Return an individual instance as a dictionary.
        '''
        ret = {
            'id': self.id,
            'action': self.action,
            'queue_name': self.queue_name,
            'sender_url': self.sender_url,
            'receiver_url': self.receiver_url,
            'is_received': self.is_received,
            'sender_ssl_cert': self.sender_ssl_cert,
            'receiver_ssl_cert': self.receiver_ssl_cert,
            'created_date': self.created_date,
            'input_data': self.input_data,
            'input_async_data': self.input_async_data,
            'output_status': self.output_status,
            'pingback_date': self.pingback_date,
            'expiration_date': self.expiration_date,
            'info_text': self.info_text,
        }

        if full:
            ret['task'] = self.task.to_dict()
        else:
            ret['task_id'] = self.task.id

        return ret


class Task(db.Model):
    '''
    Represents a task
    '''
    __tablename__ = 'task'

    id = db.Column(db.Unicode(128), primary_key=True)

    # this can be "simple", "sequential", "parallel" or "synchronized"
    task_type = db.Column(db.Unicode(1024))

    # for example used in synchronous tasks to store the algorithm
    task_metadata = db.Column(JSONEncodedDict)

    label = db.Column(db.Unicode(1024))

    action = db.Column(db.Unicode(1024))

    queue_name = db.Column(db.Unicode(1024))

    status = db.Column(db.Unicode(1024))

    is_received = db.Column(db.Boolean)

    is_local = db.Column(db.Boolean, default=False)

    parent_id = db.Column(db.Unicode(128), db.ForeignKey('task.id'))

    subtasks = db.relationship("Task", lazy="joined", join_depth=1)

    # used if it's a subtask
    order = db.Column(db.Integer)

    receiver_url = db.Column(db.Unicode(1024))

    sender_url = db.Column(db.Unicode(1024))

    sender_ssl_cert = db.Column(db.UnicodeText)

    receiver_ssl_cert = db.Column(db.UnicodeText)

    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    last_modified_date = db.Column(db.DateTime, default=datetime.utcnow)

    input_data = db.Column(JSONEncodedDict)

    input_async_data = db.Column(JSONEncodedDict)

    output_data = db.Column(JSONEncodedDict)

    output_async_data = db.Column(JSONEncodedDict)

    pingback_date = db.Column(db.DateTime, default=None)

    pingback_pending = db.Column(db.Boolean, default=False)

    expiration_date = db.Column(db.DateTime, default=None)

    expiration_pending = db.Column(db.Boolean, default=False)

    # used to store scheduled jobs and remove them when they have finished
    # or need to be removed
    jobs = dict()

    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def __repr__(self):
        return '<Task %r>' % self.action

    def get_parent(self):
        return db.session.query(Task).get(self.parent_id)

    def to_dict(self, full=False):
        '''
        Return an individual instance as a dictionary.
        '''
        ret = {
            'id': self.id,
            'action': self.action,
            'label': self.label,
            'queue_name': self.queue_name,
            'status': self.status,
            'order': self.order,
            'sender_url': self.sender_url,
            'receiver_url': self.receiver_url,
            'is_received': self.is_received,
            'is_local': self.is_local,
            'sender_ssl_cert': self.sender_ssl_cert,
            'receiver_ssl_cert': self.receiver_ssl_cert,
            'created_date': self.created_date,
            'last_modified_date': self.last_modified_date,
            'input_data': self.input_data,
            'input_async_data': self.input_async_data,
            'output_data': self.output_data,
            'output_async_data': self.output_async_data,
            'pingback_date': self.pingback_date,
            'expiration_date': self.expiration_date,
            'pingback_pending': self.pingback_pending,
            'expiration_pending': self.expiration_pending,
        }

        if full:
            parent = db.session.query(Task).get(self.parent_id)
            ret['parent'] = parent.to_dict()
        else:
            ret['parent_id'] = self.parent_id

        return ret
