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

from apscheduler.events import *
from apscheduler.scheduler import Scheduler
from apscheduler.threadpool import ThreadPool
from apscheduler.util import convert_to_datetime

INTERNAL_SCHEDULER_NAME = "internal.frestq"

EVENT_IDS = dict(
  EVENT_SCHEDULER_START = 1,
  EVENT_SCHEDULER_SHUTDOWN = 2,
  EVENT_JOBSTORE_ADDED = 4,
  EVENT_JOBSTORE_REMOVED = 8,
  EVENT_JOBSTORE_JOB_ADDED = 16,
  EVENT_JOBSTORE_JOB_REMOVED = 32,
  EVENT_JOB_EXECUTED = 64,
  EVENT_JOB_ERROR = 128,
  EVENT_JOB_MISSED = 256,
  EVENT_JOB_LAUNCHING = 512
)

logging.basicConfig(level=logging.DEBUG)

class NowTrigger(object):
    def __init__(self):
        pass

    def get_next_fire_time(self, start_date):
        return start_date

    def __str__(self):
        return 'now'

    def __repr__(self):
        return '<%s>' % (self.__class__.__name__)


class FThreadPool(ThreadPool):
    def submit(self, func, *args, **kwargs):
        return super(FThreadPool, self).submit(func, *args, **kwargs)

class FScheduler(Scheduler):
    _schedulers = dict()

    queue_name = None

    logger = logging.getLogger('fscheduler')

    def __init__(self, **options):
        from .app import app
        gconfig = {
            'apscheduler.threadpool': FThreadPool()
        }

        if len(FScheduler.logger.handlers) == 0:
            root_path = app.config.get('ROOT_PATH', "")
            hdlr = logging.FileHandler(os.path.join(root_path, "activity.json.log"))
            formatter = logging.Formatter('{"time": "%(asctime)s", "activity":%(message)s}')
            hdlr.setFormatter(formatter)
            FScheduler.logger.propagate = False
            FScheduler.logger.addHandler(hdlr)
            FScheduler.logger.setLevel(logging.DEBUG)

        super(FScheduler, self).__init__(gconfig, **options)
        self.add_listener(self)

    @staticmethod
    def get_scheduler(queue_name):
        '''
        returns a scheduler for a spefic queue name
        '''
        from .utils import dumps
        if queue_name in FScheduler._schedulers:
            return FScheduler._schedulers[queue_name]

        FScheduler._schedulers[queue_name] = sched = FScheduler()
        sched.queue_name = queue_name
        FScheduler.logger.info(dumps({"action": "CREATE_QUEUE", "queue": queue_name}))
        return sched

    @staticmethod
    def reserve_scheduler(queue_name):
        return FScheduler.get_scheduler(queue_name)

    @staticmethod
    def start_all_schedulers():
        '''
        Starts all the statically registered schedulers. It will also adjust
        the maximum number of threads now. This is not done in a previous stage
        because in frestq the app config is not guaranteed to be completely
        setup until this moment.
        '''
        from .utils import dumps
        from .app import app

        FScheduler.logger.info(dumps({"action": "START"}))
        FScheduler.reserve_scheduler(INTERNAL_SCHEDULER_NAME)
        queues_opts = app.config.get('QUEUES_OPTIONS', dict())

        for queue_name, sched in FScheduler._schedulers.iteritems():
            logging.info("starting %s scheduler" % queue_name)

            opts = queues_opts.get(queue_name, dict())
            if 'max_threads' in opts:
                logging.info("setting scheduler for queue %s with "\
                    "max_threads = %d " %(queue_name, opts['max_threads']))
                sched._threadpool.max_threads = opts['max_threads']
                FScheduler.logger.info(dumps({"action": "SET_QUEUE_MAX", "queue": queue_name, "max": opts['max_threads']}))

            sched.start()

    def __call__(self, event):
        from .utils import dumps
        def decode(code):
            if isinstance(code, int):
                for key, value in EVENT_IDS.items():
                    if value == code:
                        return key
            return code

        d = {"action": decode(event.code), "queue": self.queue_name}

        if isinstance(event, JobEvent):
            d["scheduled_run_time"] = event.scheduled_run_time
            d["retval"] = event.retval
            d["exception"] = event.exception
            d["traceback"] = event.traceback
        elif isinstance(event, JobStoreEvent):
            d["alias"] = event.alias

        if hasattr(event, "job"):
            d['job_name'] = event.job.name
            if callable(event.job.func) and hasattr(event.job.func, "__name__"):
                d['func_name'] = event.job.func.__name__

        FScheduler.logger.info(dumps(d))

    def add_now_job(self, func, args=None, kwargs=None, **options):
        """
        Schedules a job to be completed as soon as possible.
        Any extra keyword arguments are passed along to the constructor of the
        :class:`~apscheduler.job.Job` class (see :ref:`job_options`).

        :param func: callable to run at the given time
        :param name: name of the job
        :param jobstore: stored the job in the named (or given) job store
        :param misfire_grace_time: seconds after the designated run time that
            the job is still allowed to be run
        :type date: :class:`datetime.date`
        :rtype: :class:`~apscheduler.job.Job`
        """
        from .app import db

        logging.info("adding job in sched for queue %s" % self.queue_name)
        trigger = NowTrigger()
        options['max_runs'] = 1

        # autocommit to avoid dangling sessions
        def autocommit_wrapper(*args, **kwargs2):
            func(*args, **kwargs2)
            db.session.commit()

        autocommit_wrapper.__name__ = func.__name__

        if 'misfire_grace_time' not in options:
            # default to misfire_grace_time of 24 hours!
            options['misfire_grace_time'] = 3600*24

        return self.add_job(trigger, autocommit_wrapper, args, kwargs,
                            **options)

    def add_date_job(self, func, date, args=None, kwargs=None, **options):
        from .app import db

        # autocommit to avoid dangling sessions
        def autocommit_wrapper(*args, **kwargs2):
            func(*args, **kwargs2)
            db.session.commit()

        autocommit_wrapper.__name__ = func.__name__

        return super(FScheduler, self).add_date_job(autocommit_wrapper,
                                                    date, args, kwargs,
                                                    **options)
