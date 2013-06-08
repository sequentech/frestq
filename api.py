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


from flask import Blueprint, request, make_response
import json

from action_handlers import ActionHandlers

api = Blueprint('api', __name__)

def error(status, message=""):
    if message:
        data = json.dumps(dict(message=message))
    else:
        data=""
    return make_response(data, status)

@api.route('/queues/<queue_name>/', methods=['POST'])
def post_message(queue_name):
    '''
    Post a message in a queue.

    For input and out format, refer to RESTQP.md
    '''
    # 1. register message in the db model

    from app import db
    from models import Message
    try:
        data = json.loads(request.data)
    except:
        return error(400, "invalid json")

    # check input data
    requirements = [
        {'name': 'action', 'isinstance': basestring},
        {'name': 'sender_url', 'isinstance': basestring},
    ]
    for req in requirements:
        if req['name'] not in data or not isinstance(data[req['name']],
            req['isinstance']):
            return error(400, "invalid %s parameter" % req['name'])

    # TODO: get the sender ssl cert
    sender_ssl_cert = None

    kwargs = {
            'action': data.get('action', ''),
            'queue_name': queue_name,
            'sender_url': data.get('sender_url', ''),
            'receiver_url': request.url_root,
            'sender_ssl_cert': sender_ssl_cert,
            'input_data': data.get('input_data', None),
            'input_async_data': data.get('input_async_data', None),
            'pingback_date': data.get('pingback_date', None),
            'expiration_date': data.get('expiration_date', None),
            'info_text': data.get('info_text', None),
            'task_id': data.get('task_id', None),
    }
    msg = Message(**kwargs)
    db.session.add(msg)
    db.session.commit()

    action_handler = ActionHandlers.get_action_handler(msg.action, queue_name)
    if not action_handler:
        return error(404, "Action handler %s not found in the queue %s" %(
            msg.action, queue_name))

    # 3. call to action handle
    result = action_handler["handler_func"](msg)
    # 4. return output message

    data = {
        "id": msg.id,
        "data": msg.output_data,
    }

    if msg.output_async_data:
        data['async_data'] = msg.output_async_data

    if msg.task_id:
        data['task_id'] = msg.task_id

    if not msg.output_status:
        msg.output_status = 200
        db.session.add(msg)
        db.session.commit()

    return make_response(json.dumps(data), msg.output_status)
