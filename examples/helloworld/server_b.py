#!/usr/bin/env python
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

from frestq import decorators
from frestq.app import app, run_app

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
    print "I'm sleepy!..\n"

    # simulate we're working hard taking our time
    from time import sleep
    sleep(5)

    username = task.task_model.input_data['username']
    task.task_model.output_data = "hello %s!" % username

if __name__ == "__main__":
    run_app(config_object=__name__)
