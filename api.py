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
import json
import logging
from datetime import datetime

from flask import Blueprint, request, make_response
from flask import current_app

from action_handlers import ActionHandlers
from tasks import post_task

api = Blueprint('api', __name__)


def error(status, message=""):
    if message:
        data = json.dumps(dict(message=message))
    else:
        data=""
    return make_response(data, status)


def call_action_handler(msg_id, queue_name):
    '''
    Calls asynchronously to the action handler
    '''
    from models import Message
    logging.debug('Action handler for msg_id %s (queue %s)' % (
        msg_id, queue_name))
    msg = Message.query.get(msg_id)
    action_handler = ActionHandlers.get_action_handler(msg.action, queue_name)
    if action_handler.get('is_task', False):
        post_task(msg, action_handler)
    else:
        action_handler["handler_func"](msg)


@api.route('/queues/<queue_name>/', methods=['POST'])
def post_message(queue_name):
    '''
    Post a message in a queue.

    For input and out format, refer to RESTQP.md
    '''
    # 1. register message in the db model

    from app import db, get_scheduler
    from models import Message
    logging.debug('Received data message in queue %s' % queue_name)
    try:
        data = json.loads(request.data)
    except:
        return error(400, "invalid json")

    # check input data
    requirements = [
        {'name': 'message_id', 'isinstance': basestring},
        {'name': 'action', 'isinstance': basestring},
        {'name': 'sender_url', 'isinstance': basestring},
    ]
    for req in requirements:
        if req['name'] not in data or not isinstance(data[req['name']],
            req['isinstance']):
            return error(400, "invalid/notfound %s parameter" % req['name'])

    sender_ssl_cert = request.headers.get('X-Sender-SSL-Certificate', None)

    # check for a local message
    if data['sender_url'] == current_app.config.get('ROOT_URL'):
        logging.debug('The message is local and with id %s' % data['message_id'])
        msg = Message.query.get(data['message_id'])
    else:
        logging.debug('The message is not local and with id %s' % data['message_id'])
        kwargs = {
                'id': data.get('message_id', ''),
                'action': data.get('action', ''),
                'queue_name': queue_name,
                'sender_url': data.get('sender_url', ''),
                'receiver_url': current_app.config.get('ROOT_URL'),
                'is_received': True,
                'sender_ssl_cert': sender_ssl_cert,
                'input_data': data.get('data', None),
                'input_async_data': data.get('async_data', None),
                'pingback_date': data.get('pingback_date', None),
                'expiration_date': data.get('expiration_date', None),
                'info_text': data.get('info_text', None),
                'task_id': data.get('task_id', None),
                'output_status': 200
        }
        msg = Message(**kwargs)
        db.session.add(msg)
        db.session.commit()

    action_handler = ActionHandlers.get_action_handler(msg.action, queue_name)
    if not action_handler:
        logging.error('Action handler for action %s (message id %s)' % (
            msg.action, msg.id))
        return error(404, "Action handler %s not found in the queue %s" %(
            msg.action, queue_name))

    # 3. call to action handle
    get_scheduler().add_now_job(call_action_handler, [msg.id, queue_name])

    # 4. return output message
    return make_response("", msg.output_status)
