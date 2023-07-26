# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2013-2021 Sequent Tech Inc <legal@sequentech.io>
# SPDX-FileCopyrightText: 2014-2021 Sequent Tech Inc <legal@sequentech.io>
#
# SPDX-License-Identifier: AGPL-3.0-only

import json
import logging
from datetime import datetime

from flask import Blueprint, request, make_response
from flask import current_app

from .action_handlers import ActionHandlers
from .utils import loads, dumps

api = Blueprint('api', __name__)


def error(status, message=""):
    if message:
        data = dumps(dict(message=message))
    else:
        data=""
    return make_response(data, status)


def call_action_handler(msg_id, queue_name):
    '''
    Calls asynchronously to the action handler
    '''
    from .models import Message
    from .tasks import post_task, TaskError
    logging.debug('EXEC ACTION handler for MESSAGE id %s (QUEUE %s)' % (
        msg_id, queue_name))
    msg = Message.query.get(msg_id)
    action_handler = ActionHandlers.get_action_handler(msg.action, queue_name)
    if not action_handler:
        raise Exception('action handler not found')
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

    from .app import app
    from .models import Message

    logging.debug('RECEIVED MESSAGE in queue %s' % queue_name)
    data = request.get_json(force=True, silent=True)
    if not data:
        return error(400, "invalid json")

    # check input data
    requirements = [
        {'name': 'message_id', 'isinstance': str},
        {'name': 'action', 'isinstance': str},
        {'name': 'sender_url', 'isinstance': str},
    ]
    for req in requirements:
        if req['name'] not in data or not isinstance(data[req['name']],
            req['isinstance']):
            return error(400, "invalid/notfound %s parameter" % req['name'])

    sender_ssl_cert = request.environ.get('X-Sender-SSL-Certificate', None)
    # NOTE: nginx adds \t to the certificate because otherwise it would be not
    # possible to send it as a proxy header, so we have to remove those tabs.
    # A PEM certificate does never contain tabs, so this replace is safe anyway.
    # For more details see:
    # - https://www.ruby-forum.com/topic/155918 and
    # - http://nginx.org/en/docs/http/ngx_http_ssl_module.html
    if sender_ssl_cert:
        sender_ssl_cert = sender_ssl_cert.replace('\t', '')

    # check for a local message
    if data['sender_url'] == current_app.config.get('ROOT_URL'):
        # check that the certificate is really local
        from .protocol import certs_differ, SecurityException
        local_ssl_cert = current_app.config['SSL_CERT_STRING']
        if certs_differ(sender_ssl_cert, local_ssl_cert):
            raise SecurityException()

        logging.debug('The MESSAGE is LOCAL and with id %s' % data['message_id'])
        msg = Message.query.get(data['message_id'])
    else:
        logging.debug('The MESSAGE is NOT LOCAL and with id %s' % data['message_id'])
        kwargs = {
                'id': data.get('message_id', ''),
                'action': data.get('action', ''),
                'queue_name': queue_name,
                'sender_url': data.get('sender_url', ''),
                'receiver_url': current_app.config.get('ROOT_URL'),
                'is_received': True,
                'sender_ssl_cert': sender_ssl_cert,
                'input_data': data.get('data', None),
                'pingback_date': data.get('pingback_date', None),
                'expiration_date': data.get('expiration_date', None),
                'info_text': data.get('info_text', None),
                'task_id': data.get('task_id', None),
                'output_status': 200
        }
        msg = Message(**kwargs)
        app.db.session.add(msg)
        app.db.session.commit()

    action_handler = ActionHandlers.get_action_handler(msg.action, queue_name)
    if not action_handler:
        logging.error('Action handler for action %s not found (message id %s)' % (
            msg.action, msg.id))
        return error(404, "Action handler %s not found in the queue %s" %(
            msg.action, queue_name))

    # 3. call to action handle
    from .fscheduler import FScheduler
    sched = FScheduler.get_scheduler(queue_name)
    sched.add_now_job(call_action_handler, [msg.id, queue_name])

    # 4. return output message
    return make_response("", msg.output_status)
