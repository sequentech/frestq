# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2013-2021 Sequent Tech Inc <legal@sequentech.io>
# SPDX-FileCopyrightText: 2014-2021 Sequent Tech Inc <legal@sequentech.io>
#
# SPDX-License-Identifier: AGPL-3.0-only

import json
from datetime import datetime

import sqlalchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_json import mutable_json_type
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy


from .app import db
from .utils import dumps, loads


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

    input_data = db.Column(mutable_json_type(dbtype=JSONB, nested=True))

    output_status = db.Column(db.Integer)

    pingback_date = db.Column(db.DateTime, default=None)

    expiration_date = db.Column(db.DateTime, default=None)

    info_text = db.Column(db.Unicode(2048))

    # fixed broken FK bug, when taskid exists in a non local db
    # task_id = db.Column(db.Unicode(128), db.ForeignKey('task.id'))
    #task = db.relationship('Task',
    #    backref=db.backref('messages', lazy='dynamic'))
    task_id = db.Column(db.Unicode(128))

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
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

    # this can be "simple", "sequential", "parallel", "external" or
    # "synchronized"
    task_type = db.Column(db.Unicode(1024))

    # for example used in synchronous tasks to store the algorithm
    task_metadata = db.Column(mutable_json_type(dbtype=JSONB, nested=True))

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

    input_data = db.Column(mutable_json_type(dbtype=JSONB, nested=True))

    output_data = db.Column(mutable_json_type(dbtype=JSONB, nested=True))

    reservation_data = db.Column(mutable_json_type(dbtype=JSONB, nested=True))

    pingback_date = db.Column(db.DateTime, default=None)

    pingback_pending = db.Column(db.Boolean, default=False)

    expiration_date = db.Column(db.DateTime, default=None)

    expiration_pending = db.Column(db.Boolean, default=False)

    # used to store scheduled jobs and remove them when they have finished
    # or need to be removed
    jobs = dict()

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
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
            'output_data': self.output_data,
            'reservation_data': self.reservation_data,
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
