# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2013-2021 Sequent Tech Inc <legal@sequentech.io>
# SPDX-FileCopyrightText: 2014-2021 Sequent Tech Inc <legal@sequentech.io>
#
# SPDX-License-Identifier: AGPL-3.0-only

import logging
import os
from sqlalchemy import exc

from apscheduler.events import *
from apscheduler.schedulers.background import BackgroundScheduler as Scheduler
from apscheduler.triggers.base import BaseTrigger
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

class NowTrigger(BaseTrigger):
    def __init__(self):
        pass

    def get_next_fire_time(self, previous_fire, now):
        return now

    def __str__(self):
        return 'now'

    def __repr__(self):
        return '<%s>' % (self.__class__.__name__)


class FScheduler(Scheduler):
    _schedulers = dict()

    queue_name = None

    logger = logging.getLogger('fscheduler')

    def __init__(self, **options):
        from .app import app

        if len(FScheduler.logger.handlers) == 0:
            root_path = app.config.get('ROOT_PATH', "")
            hdlr = logging.FileHandler(os.path.join(root_path, "activity.json.log"))
            formatter = logging.Formatter('{"time": "%(asctime)s", "activity":%(message)s}')
            hdlr.setFormatter(formatter)
            FScheduler.logger.propagate = False
            FScheduler.logger.addHandler(hdlr)
            FScheduler.logger.setLevel(logging.DEBUG)

        super(FScheduler, self).__init__(**options)
        self.add_listener(self)

    @staticmethod
    def get_scheduler(queue_name):
        '''
        returns a scheduler for a spefic queue name
        '''
        from .app import app
        from .utils import dumps
        if queue_name in FScheduler._schedulers:
            return FScheduler._schedulers[queue_name]

        options = {}
        queues_opts = app.config.get('QUEUES_OPTIONS', dict())
        opts = queues_opts.get(queue_name, dict())
        if 'max_threads' in opts:
            logging.info("setting scheduler for queue %s with "\
                "max_threads = %d " %(queue_name, opts['max_threads']))
            options['apscheduler.executors.default'] = {
                'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
                'max_workers': opts['max_threads'],
            }

        FScheduler._schedulers[queue_name] = sched = FScheduler(gconfig=options)
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

        FScheduler.logger.info(dumps({"action": "START"}))
        FScheduler.reserve_scheduler(INTERNAL_SCHEDULER_NAME)

        for queue_name, sched in FScheduler._schedulers.items():
            logging.info("starting %s scheduler" % queue_name)
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

        if isinstance(event, JobExecutionEvent):
            d["scheduled_run_time"] = event.scheduled_run_time
            d["retval"] = event.retval
            d["exception"] = event.exception
            d["traceback"] = event.traceback
        elif isinstance(event, JobEvent):
            if event.code in [EVENT_JOBSTORE_ADDED, EVENT_JOBSTORE_REMOVED]:
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

        # autocommit to avoid dangling sessions
        def autocommit_wrapper(*args, **kwargs2):
            try:
              func(*args, **kwargs2)
              db.session.commit()
            except exc.SQLAlchemyError:
              import traceback; traceback.print_exc()
              logging.info("SQLAlchemy exception, doing a rollback for recovery.")
              db.session.rollback()

        autocommit_wrapper.__name__ = func.__name__

        if 'misfire_grace_time' not in options:
            # default to misfire_grace_time of 24 hours!
            options['misfire_grace_time'] = 3600*24

        return self.add_job(autocommit_wrapper, args=args, kwargs=kwargs,
                            **options)

    def add_date_job(self, func, date, args=None, kwargs=None, **options):
        from .app import db

        # autocommit to avoid dangling sessions
        def autocommit_wrapper(*args, **kwargs2):
            func(*args, **kwargs2)
            db.session.commit()

        autocommit_wrapper.__name__ = func.__name__

        return super(FScheduler, self).add_job(autocommit_wrapper,
                                               'date', args, kwargs,
                                               run_date=date,
                                               **options)
