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

from apscheduler.scheduler import Scheduler
from apscheduler.util import convert_to_datetime


class NowTrigger(object):
    def __init__(self):
        pass

    def get_next_fire_time(self, start_date):
        return start_date

    def __str__(self):
        return 'now'

    def __repr__(self):
        return '<%s>' % (self.__class__.__name__)


class FScheduler(Scheduler):
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
        trigger = NowTrigger()
        options['max_runs'] = 1
        return self.add_job(trigger, func, args, kwargs, **options)
