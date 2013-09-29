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

from frestq.app import app
from frestq import decorators
from frestq.tasks import ExternalTask

from flask import Blueprint, make_response

# configuration:

# set database uri
import os
ROOT_PATH = os.path.split(os.path.abspath(__file__))[0]
SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/db2.sqlite' % ROOT_PATH

SERVER_NAME = '127.0.0.1:5001'

SERVER_PORT = 5001

ROOT_URL = 'http://127.0.0.1:5001/api/queues'


# action handler:
@decorators.task(action="hello_world", queue="say_queue")
def hello_world(task):

    approve_task = ExternalTask(data=dict(type="approve"))
    task.add(approve_task)

    return dict(
        output_data = None
    )

approve_api = Blueprint('approve', __name__)

@approve_api.route('/<task_id>', methods=['POST'])
def approve(task_id):
    task = ExternalTask.instance_by_id(task_id)
    task.finish(data=dict(yeah="whatever"))
    return make_response("", 200)

app.register_blueprint(approve_api, url_prefix='/approve')
app.configure_app(config_object=__name__)

if __name__ == "__main__":
    app.run(parse_args=True)