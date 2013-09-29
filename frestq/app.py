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

from __future__ import unicode_literals
import logging
import os
import argparse
from fscheduler import FScheduler

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

logging.basicConfig(level=logging.DEBUG)

class FrestqApp(Flask):
    def __init__(self, *args, **kwargs):
        super(FrestqApp, self).__init__(*args, **kwargs)

    def configure_app(self, config_object=None):
        '''
        Configures the application. It's intended to do everything to be able to
        run the application except calling app.run, so that it can be reused when
        using gunicorn or similar.
        '''
        self.config.from_object(__name__)
        if config_object:
            self.config.from_object(config_object)

        frestq_settings = os.environ.get('FRESTQ_SETTINGS', None)
        if frestq_settings is not None:
            if not os.path.isabs(frestq_settings):
                os.environ['FRESTQ_SETTINGS'] = os.path.abspath(frestq_settings)
            logging.debug("FRESTQ_SETTINGS = %s" % os.environ['FRESTQ_SETTINGS'])
            self.config.from_envvar('FRESTQ_SETTINGS', silent=False)
        else:
            logging.warning("FRESTQ_SETTINGS not set")

        # store cert in
        if self.config.get('SSL_CERT_PATH', None) and\
            self.config.get('SSL_KEY_PATH', None):

            with open(self.config.get('SSL_CERT_PATH', ''), 'r') as f:
                self.config['SSL_CERT_STRING'] = f.read()
        else:
            self.config['SSL_CERT_STRING'] = ''
            logging.warning("You are NOT using SSL in this instance")

        logging.info("Launching with ROOT_URL = %s", self.config['ROOT_URL'])
        FScheduler.start_all_schedulers()

    def run(self, *args, **kwargs):
        '''
        Reimplemented the run function.

        parse_args can be provided if you want yo parse the app arguments
        '''
        if kwargs.get('parse_args', False):
            # remove parse_args as it's not recognized by super
            del kwargs['parse_args']

            parser = argparse.ArgumentParser()
            parser.add_argument("--createdb", help="create the database",
                                action="store_true")
            parser.add_argument("--messages", help="list last messages",
                                action="store_true")
            parser.add_argument("--tasks", help="list last tasks",
                                action="store_true")
            parser.add_argument("--filters", nargs='+',
                help="filter items, with \"key=value\" ", default=[])
            parser.add_argument("--tree",
                                help="prints the tree of related tasks")
            parser.add_argument("--show", help="prints a task in detail")
            parser.add_argument("--show-external", help="prints an external task details")
            parser.add_argument("--finish", help="finish an external task",
                                nargs=2, default=None)
            parser.add_argument("--with-parents",
                                help="show in the tree parent tasks too",
                                action="store_true")
            parser.add_argument("-n", "--limit", help="limit number of results",
                                type=int, default=20)
            pargs = parser.parse_args()

            if pargs.limit < 1:
                print "limit must be >= 1"
                return

            if pargs.createdb:
                print "creating the database: ", self.config.get('SQLALCHEMY_DATABASE_URI', '')
                db.create_all()
                return
            elif pargs.messages:
                list_messages(pargs)
                return
            elif pargs.tasks:
                list_tasks(pargs)
                return
            elif pargs.tree:
                task_tree(pargs)
                return
            elif pargs.show:
                show_task(pargs)
                return
            elif pargs.show_external:
                show_external_task(pargs)
                return
            elif pargs.finish:
                finish_task(pargs)
                return

        # ignore these threaded or use_reloader, we force those two
        if 'threaded' in kwargs:
            print "threaded provided but ignored (always set to True): ", kwargs['threaded']
            del kwargs['threaded']
        if 'use_reloader' in kwargs:
            print "use_reloader provided but ignored (always set to True): ", kwargs['use_reloader']
            del kwargs['use_reloader']

        if 'port' not in kwargs:
            kwargs['port'] = app.config.get('SERVER_PORT', None)

        return super(FrestqApp, self).run(threaded=True, use_reloader=False,
                                          *args, **kwargs)

app = FrestqApp(__name__)

### configuration

# debug, set to false on production deployment
DEBUG = True

# database configuration
# example: sqlite:////absolute/path/to/db.sqlite
SQLALCHEMY_DATABASE_URI = ''

# own certificate, None if there isn't any
SSL_CERT_PATH = None
SSL_KEY_PATH = None

# queues root url
ROOT_URL = 'http://127.0.0.1:5000/api/queues'

# time a thread can be reserved in for synchronization purposes. In seconds.
RESERVATION_TIMEOUT = 60

app.config.from_object(__name__)

# boostrap our little application
db = SQLAlchemy(app)

# set to True to get real security
ALLOW_ONLY_SSL_CONNECTIONS = False

# options for each queue. example:
#QUEUES_OPTIONS = {
    #'mycustom_queue': {
        #'max_threads': 3,
    #}
#}
# thread data mapper is a function that would be called when a Synchronous task
# in this queue is going to be executed. It allows to set queue-specific
# settings, and even custom queue settings that can be used by you later.

QUEUES_OPTIONS = dict()

from . import models

from .api import api
app.register_blueprint(api, url_prefix='/api')

from . import protocol
from .utils import (list_messages, list_tasks, task_tree, show_task,
                    show_external_task, finish_task)

if __name__ == "__main__":
    app.run(parse_args=True)
