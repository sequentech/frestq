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

import logging
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

### configuration

# debug, set to false on production deployment
DEBUG = True

# database configuration
SQLALCHEMY_DATABASE_URI = 'sqlite:///db.sqlite'

# import custom settings if any
try:
    from custom_settings import *
except:
    pass

# boostrap our little application
app.config.from_object(__name__)
db = SQLAlchemy(app)
import models

from api import api as api_v1
app.register_blueprint(api_v1, url_prefix='/api/v1')

from tasks_protocol import *

if __name__ == "__main__":
    # TODO: use sched to schedule and handle events
    app.run(threaded=True)
