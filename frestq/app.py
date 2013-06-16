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

import logging
import argparse
from fscheduler import FScheduler

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

### configuration

# debug, set to false on production deployment
DEBUG = True

# database configuration
# example: sqlite:////absolute/path/to/db.sqlite
SQLALCHEMY_DATABASE_URI = ''

# own certificate, empty if there isn't any
SSL_CERT_STRING = ''

# queues root url
ROOT_URL = 'http://127.0.0.1:5000/api/queues'

# boostrap our little application
db = SQLAlchemy(app)

def get_scheduler():
    if not hasattr(FScheduler, "instance"):
        setattr(FScheduler, "instance", FScheduler())
    return FScheduler.instance

from . import models

from .api import api
app.register_blueprint(api, url_prefix='/api')

from . import protocol

def run_app(config_object=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--createdb", help="create the database", action="store_true")
    args = parser.parse_args()
    app.config.from_object(__name__)
    if config_object:
        app.config.from_object(config_object)
    app.config.from_envvar('FRESTQ_SETTINGS', silent=True)
    if args.createdb:
        print "creating the database"
        db.create_all()
        return

    get_scheduler().start()
    app.run(threaded=True, port=app.config.get('SERVER_PORT', None), use_reloader=False)

if __name__ == "__main__":
    run_app()
