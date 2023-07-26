# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2013-2021 Sequent Tech Inc <legal@sequentech.io>
# SPDX-FileCopyrightText: 2014-2021 Sequent Tech Inc <legal@sequentech.io>
#
# SPDX-License-Identifier: AGPL-3.0-only

import logging
import os
import argparse
from fscheduler import FScheduler

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask import json as json_flask
from flask.wrappers import Request

from .utils import loads

class FrestqRequest(Request):
    '''
    We have to customize request so that by default it can overload the json
    object_hook for json.loads() so that it auto-parses datetimes
    '''

    def get_json(self, force=False, silent=False, cache=True):
        """Parse and return the data as JSON. If the mimetype does not
        indicate JSON (:mimetype:`application/json`, see
        :meth:`is_json`), this returns ``None`` unless ``force`` is
        true. If parsing fails, :meth:`on_json_loading_failed` is called
        and its return value is used as the return value.
        :param force: Ignore the mimetype and always try to parse JSON.
        :param silent: Silence parsing errors and return ``None``
            instead.
        :param cache: Store the parsed JSON to return for subsequent
            calls.
        """
        if cache and self._cached_json[silent] is not Ellipsis:
            return self._cached_json[silent]

        if not (force or self.is_json):
            return None

        data = self.get_data(cache=cache)

        try:
            rv = loads(data.decode('utf-8'))
        except ValueError as e:
            if silent:
                rv = None
                if cache:
                    normal_rv, _ = self._cached_json
                    self._cached_json = (normal_rv, rv)
            else:
                rv = self.on_json_loading_failed(e)
                if cache:
                    _, silent_rv = self._cached_json
                    self._cached_json = (rv, silent_rv)
        else:
            if cache:
                self._cached_json = (rv, rv)

        return rv

class FrestqApp(Flask):
    def __init__(self, *args, **kwargs):
        if 'parse_args' in kwargs:
            del kwargs['parse_args']
            self.parse_args()
        super(FrestqApp, self).__init__(*args, **kwargs)

    request_class = FrestqRequest

    pargs = None

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

        if self.pargs.createdb or self.pargs.messages or self.pargs.tasks or\
                self.pargs.tree or self.pargs.show_task or\
                self.pargs.show_message or self.pargs.show_external or\
                self.pargs.finish or self.pargs.show_activity:
            return

        logging.info("Launching with ROOT_URL = %s", self.config['ROOT_URL'])
        FScheduler.start_all_schedulers()

    def process_parser(self, parser):
        '''
        Reimplement to process the parser
        '''
        pass

    def parse_args(self):
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
        parser.add_argument("--show-task", help="prints a task in detail")
        parser.add_argument("--console", help="frestq command line",
                            action="store_true")
        parser.add_argument("--show-message", help="prints a task in detail")
        parser.add_argument("--show-external", help="prints an external task details")
        parser.add_argument("--show-activity", help="prints activity",
                            action="store_true")
        parser.add_argument("--finish", help="finish an external task",
                            nargs=2, default=None)
        parser.add_argument("--with-parents",
                            help="show in the tree parent tasks too",
                            action="store_true")
        parser.add_argument("-n", "--limit", help="limit number of results",
                            type=int, default=20)
        parser.add_argument("-ll", "--log-level", default=None,
                            help="show verbose output. set to ERROR by default",
                            choices=["debug","info", "error"])
        self.process_parser(parser)
        self.pargs = parser.parse_args()

        if self.pargs.limit < 1:
            print("limit must be >= 1")
            return

        if self.pargs.log_level != None:
            if self.pargs.log_level == "debug":
                logging.getLogger().setLevel(logging.DEBUG)
            elif self.pargs.log_level == "info":
                logging.getLogger().setLevel(logging.INFO)
            elif self.pargs.log_level == "error":
                logging.getLogger().setLevel(logging.ERROR)

    def run_args(self):
        if self.pargs.createdb:
            print("creating the database: " + self.config.get('SQLALCHEMY_DATABASE_URI', ''))
            from .app import app
            app.db.create_all()
            return
        elif self.pargs.messages:
            list_messages(self.pargs)
            return
        elif self.pargs.tasks:
            list_tasks(self.pargs)
            return
        elif self.pargs.tree:
            task_tree(self.pargs)
            return
        elif self.pargs.show_task:
            show_task(self.pargs)
            return
        elif self.pargs.show_message:
            show_message(self.pargs)
            return
        elif self.pargs.show_external:
            show_external_task(self.pargs)
        elif self.pargs.finish:
            finish_task(self.pargs)
            return
        elif self.pargs.show_activity:
            show_activity(self.pargs)
            return
        elif self.pargs.console:
            import ipdb; ipdb.set_trace()
            return
        else:
            self.parser.print_help()

    def run(self, *args, **kwargs):
        '''
        Reimplemented the run function.
        '''
        if self.pargs is not None:
            self.run_args()

        # ignore these threaded or use_reloader, we force those two
        if 'threaded' in kwargs:
            print("threaded provided but ignored (always set to True): " + kwargs['threaded'])
            del kwargs['threaded']
        if 'use_reloader' in kwargs:
            print("use_reloader provided but ignored (always set to True): " + kwargs['use_reloader'])
            del kwargs['use_reloader']

        if 'port' not in kwargs:
            kwargs['port'] = app.config.get('SERVER_PORT', None)

        return super(FrestqApp, self).run(threaded=True, use_reloader=False,
                                          *args, **kwargs)
