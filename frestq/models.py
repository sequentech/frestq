# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2013-2021 Sequent Tech Inc <legal@sequentech.io>
# SPDX-FileCopyrightText: 2014-2021 Sequent Tech Inc <legal@sequentech.io>
#
# SPDX-License-Identifier: AGPL-3.0-only

import json
from datetime import datetime

import sqlalchemy
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import TypeDecorator, UnicodeText
from flask import Flask, jsonify

from .app import app
from .utils import dumps, loads


class JSONEncodedDict(TypeDecorator):
    impl = UnicodeText

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return dumps(value)

    def process_result_value(self, value, dialect):
        if not value:
            return None
        return loads(value)


class MutationObj(Mutable):
    @classmethod
    def coerce(cls, key, value):
        if isinstance(value, dict) and not isinstance(value, MutationDict):
            return MutationDict.coerce(key, value)
        if isinstance(value, list) and not isinstance(value, MutationList):
            return MutationList.coerce(key, value)
        return value

    @classmethod
    def _listen_on_attribute(cls, attribute, coerce, parent_cls):
        key = attribute.key
        if parent_cls is not attribute.class_:
            return

        # rely on "propagate" here
        parent_cls = attribute.class_

        def load(state, *args):
            val = state.dict.get(key, None)
            if coerce:
                val = cls.coerce(key, val)
                state.dict[key] = val
            if isinstance(val, cls):
                val._parents[state.obj()] = key

        def set(target, value, oldvalue, initiator):
            if not isinstance(value, cls):
                value = cls.coerce(key, value)
            if isinstance(value, cls):
                value._parents[target.obj()] = key
            if isinstance(oldvalue, cls):
                oldvalue._parents.pop(target.obj(), None)
            return value

        def pickle(state, state_dict):
            val = state.dict.get(key, None)
            if isinstance(val, cls):
                if 'ext.mutable.values' not in state_dict:
                    state_dict['ext.mutable.values'] = []
                state_dict['ext.mutable.values'].append(val)

        def unpickle(state, state_dict):
            if 'ext.mutable.values' in state_dict:
                for val in state_dict['ext.mutable.values']:
                    val._parents[state.obj()] = key

        sqlalchemy.event.listen(parent_cls, 'load', load, raw=True, propagate=True)
        sqlalchemy.event.listen(parent_cls, 'refresh', load, raw=True, propagate=True)
        sqlalchemy.event.listen(attribute, 'set', set, raw=True, retval=True, propagate=True)
        sqlalchemy.event.listen(parent_cls, 'pickle', pickle, raw=True, propagate=True)
        sqlalchemy.event.listen(parent_cls, 'unpickle', unpickle, raw=True, propagate=True)

class MutationDict(MutationObj, dict):
    @classmethod
    def coerce(cls, key, value):
        """Convert plain dictionary to MutationDict"""
        self = MutationDict((k,MutationObj.coerce(key,v)) for (k,v) in value.items())
        self._key = key
        return self

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, MutationObj.coerce(self._key, value))
        self.changed()

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self.changed()

class MutationList(MutationObj, list):
    @classmethod
    def coerce(cls, key, value):
        """Convert plain list to MutationList"""
        self = MutationList((MutationObj.coerce(key, v) for v in value))
        self._key = key
        return self

    def __setitem__(self, idx, value):
        list.__setitem__(self, idx, MutationObj.coerce(self._key, value))
        self.changed()

    def __setslice__(self, start, stop, values):
        list.__setslice__(self, start, stop, (MutationObj.coerce(self._key, v) for v in values))
        self.changed()

    def __delitem__(self, idx):
        list.__delitem__(self, idx)
        self.changed()

    def __delslice__(self, start, stop):
        list.__delslice__(self, start, stop)
        self.changed()

    def append(self, value):
        list.append(self, MutationObj.coerce(self._key, value))
        self.changed()

    def insert(self, idx, value):
        list.insert(self, idx, MutationObj.coerce(self._key, value))
        self.changed()

    def extend(self, values):
        list.extend(self, (MutationObj.coerce(self._key, v) for v in values))
        self.changed()

    def pop(self, *args, **kw):
        value = list.pop(self, *args, **kw)
        self.changed()
        return value

    def remove(self, value):
        list.remove(self, value)
        self.changed()

MutationObj.associate_with(JSONEncodedDict)

class Message(sqlalchemy.Model):
    '''
    Represents an election
    '''
    __tablename__ = 'message'

    id = sqlalchemy.Column(sqlalchemy.Unicode(128), primary_key=True)

    sender_url = sqlalchemy.Column(sqlalchemy.Unicode(1024))

    queue_name = sqlalchemy.Column(sqlalchemy.Unicode(1024))

    is_received = sqlalchemy.Column(sqlalchemy.Boolean)

    receiver_url = sqlalchemy.Column(sqlalchemy.Unicode(1024))

    sender_ssl_cert = sqlalchemy.Column(sqlalchemy.UnicodeText)

    receiver_ssl_cert = sqlalchemy.Column(sqlalchemy.UnicodeText)

    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.utcnow)

    action = sqlalchemy.Column(sqlalchemy.Unicode(1024))

    input_data = sqlalchemy.Column(JSONEncodedDict)

    output_status = sqlalchemy.Column(sqlalchemy.Integer)

    pingback_date = sqlalchemy.Column(sqlalchemy.DateTime, default=None)

    expiration_date = sqlalchemy.Column(sqlalchemy.DateTime, default=None)

    info_text = sqlalchemy.Column(sqlalchemy.Unicode(2048))

    # fixed broken FK bug, when taskid exists in a non local db
    # task_id = db.Column(db.Unicode(128), db.ForeignKey('task.id'))
    #task = db.relationship('Task',
    #    backref=db.backref('messages', lazy='dynamic'))
    task_id = sqlalchemy.Column(sqlalchemy.Unicode(128))

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


class Task(sqlalchemy.Model):
    '''
    Represents a task
    '''
    __tablename__ = 'task'

    id = sqlalchemy.Column(sqlalchemy.Unicode(128), primary_key=True)

    # this can be "simple", "sequential", "parallel", "external" or
    # "synchronized"
    task_type = sqlalchemy.Column(sqlalchemy.Unicode(1024))

    # for example used in synchronous tasks to store the algorithm
    task_metadata = sqlalchemy.Column(JSONEncodedDict)

    label = sqlalchemy.Column(sqlalchemy.Unicode(1024))

    action = sqlalchemy.Column(sqlalchemy.Unicode(1024))

    queue_name = sqlalchemy.Column(sqlalchemy.Unicode(1024))

    status = sqlalchemy.Column(sqlalchemy.Unicode(1024))

    is_received = sqlalchemy.Column(sqlalchemy.Boolean)

    is_local = sqlalchemy.Column(sqlalchemy.Boolean, default=False)

    parent_id = sqlalchemy.Column(sqlalchemy.Unicode(128), sqlalchemy.ForeignKey('task.id'))

    subtasks = sqlalchemy.relationship("Task", lazy="joined", join_depth=1)

    # used if it's a subtask
    order = sqlalchemy.Column(sqlalchemy.Integer)

    receiver_url = sqlalchemy.Column(sqlalchemy.Unicode(1024))

    sender_url = sqlalchemy.Column(sqlalchemy.Unicode(1024))

    sender_ssl_cert = sqlalchemy.Column(sqlalchemy.UnicodeText)

    receiver_ssl_cert = sqlalchemy.Column(sqlalchemy.UnicodeText)

    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.utcnow)

    last_modified_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.utcnow)

    input_data = sqlalchemy.Column(JSONEncodedDict)

    output_data = sqlalchemy.Column(JSONEncodedDict)

    reservation_data = sqlalchemy.Column(JSONEncodedDict)

    pingback_date = sqlalchemy.Column(sqlalchemy.DateTime, default=None)

    pingback_pending = sqlalchemy.Column(sqlalchemy.Boolean, default=False)

    expiration_date = sqlalchemy.Column(sqlalchemy.DateTime, default=None)

    expiration_pending = sqlalchemy.Column(sqlalchemy.Boolean, default=False)

    # used to store scheduled jobs and remove them when they have finished
    # or need to be removed
    jobs = dict()

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return '<Task %r>' % self.action

    def get_parent(self):
        return sqlalchemy.session.query(Task).get(self.parent_id)

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
            parent = sqlalchemy.session.query(Task).get(self.parent_id)
            ret['parent'] = parent.to_dict()
        else:
            ret['parent_id'] = self.parent_id

        return ret
