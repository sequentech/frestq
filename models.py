# -*- coding: utf-8 -*-

# This file is part of election-orchestra.
# Copyright (C) 2013  Eduardo Robles Elvira <edulix AT wadobo DOT com>

# election-orchestra is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# election-orchestra  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with election-orchestra.  If not, see <http://www.gnu.org/licenses/>.

from flask import Flask, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from datetime import datetime
from app import db

from sqlalchemy.types import TypeDecorator, VARCHAR
import json

class Message(db.Model):
    '''
    Represents an election
    '''

    id = db.Column(db.Integer, primary_key=True)

    sender_url = db.Column(db.Unicode(1024))

    receiver_url = db.Column(db.Unicode(1024))

    sender_ssl_cert = db.Column(db.UnicodeText)

    receiver_ssl_cert = db.Column(db.UnicodeText)

    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    action = db.Column(db.Unicode(1024))

    input_data = db.Column(db.UnicodeText)

    input_async_data = db.Column(db.UnicodeText)

    output_status = db.Column(db.Unicode(255))

    output_data = db.Column(db.UnicodeText)

    output_async_data = db.Column(db.UnicodeText)

    pingback_date = db.Column(db.DateTime, default=None)

    expiration_date = db.Column(db.DateTime, default=None)

    info_text = db.Column(db.Unicode(2048))

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
            'sender_url': self.sender_url,
            'receiver_url': self.receiver_url,
            'sender_ssl_cert': self.sender_ssl_cert,
            'receiver_ssl_cert': self.receiver_ssl_cert,
            'created_date': self.created_date,
            'input_data': self.input_data,
            'input_async_data': self.input_async_data,
            'output_data': self.output_data,
            'output_async_data': self.output_async_data,
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

    id = db.Column(db.Integer, primary_key=True)

    action = db.Column(db.Unicode(1024))

    status = db.Column(db.Unicode(1024))

    parent_task = db.relationship('Task',
        backref=db.backref('subtasks', lazy='dynamic'))

    receiver_url = db.Column(db.Unicode(1024))

    sender_url = db.Column(db.Unicode(1024))

    sender_ssl_cert = db.Column(db.UnicodeText)

    receiver_ssl_cert = db.Column(db.UnicodeText)

    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    last_modified_date = db.Column(db.DateTime, default=datetime.utcnow)

    input_data = db.Column(db.UnicodeText)

    input_async_data = db.Column(db.UnicodeText)

    output_data = db.Column(db.UnicodeText)

    output_async_data = db.Column(db.UnicodeText)

    pingback_date = db.Column(db.DateTime, default=None)

    pingback_pending = db.Column(db.Boolean, default=False)

    expiration_date = db.Column(db.DateTime, default=None)

    expiration_pending = db.Column(db.Boolean, default=False)

    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def __repr__(self):
        return '<Task %r>' % self.action

    def to_dict(self, full=False):
        '''
        Return an individual instance as a dictionary.
        '''
        ret = {
            'id': self.id,
            'action': self.action,
            'status': self.status,
            'sender_url': self.sender_url,
            'receiver_url': self.receiver_url,
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
            'parent_task_id': self.parent_task_id
        }

        if full:
            ret['task'] = self.task.to_dict()
        else:
            ret['task_id'] = self.task.id

        return ret
