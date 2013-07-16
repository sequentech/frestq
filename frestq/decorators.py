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
import types
from functools import wraps

from .action_handlers import ActionHandlers
from .fscheduler import FScheduler, INTERNAL_SCHEDULER_NAME

def message_action(action, queue, **kwargs):
    """
    Decorator for message actions
    """
    # Check if perm is given as string in order not to decorate
    # view function itself which makes debugging harder
    if not isinstance(action, basestring) or not isinstance(queue, basestring):
        raise Exception("action and queue args for message decorator must be strings")

    def decorator(view_func):
        '''
        This is the static wrapper, called when loading the code a wrapped
        funcion
        '''
        # register view_func as an action handler for the given queue
        ActionHandlers.add_action_handler(action, queue, view_func, kwargs)

        return view_func

    return decorator

def task(action, queue, **kwargs):
    """
    Decorator for tasks
    """

    # Check if perm is given as string in order not to decorate
    # view function itself which makes debugging harder
    if not isinstance(action, basestring) or not isinstance(queue, basestring):
        raise Exception("action and queue args for message decorator must be strings")

    def decorator(view_func):
        '''
        This is the static wrapper, called when loading the code a wrapped
        funcion
        '''
        # register view_func as an action handler for the given queue
        kwargs['is_task'] = True
        if  type(view_func) is types.ClassType:
            view_func.action = action
            view_func.queue_name = queue

        ActionHandlers.add_action_handler(action, queue, view_func, kwargs)
        FScheduler.reserve_scheduler(queue)

        return view_func

    return decorator

def internal_task(name, **kwargs):
    """
    Decorator for class based internal task handlers
    """

    # Check if perm is given as string in order not to decorate
    # view function itself which makes debugging harder
    if not isinstance(name, basestring):
        raise Exception("name must be a string")

    def decorator(klass):
        '''
        This is the static wrapper, called when loading the code a wrapped
        funcion
        '''
        # register view_func as an action handler for the given queue
        kwargs['is_task'] = True
        kwargs['is_internal'] = True
        klass.action = name
        klass.queue_name = INTERNAL_SCHEDULER_NAME
        ActionHandlers.add_action_handler(klass.action, klass.queue_name,
                                          klass, kwargs)
        FScheduler.reserve_scheduler(klass.queue_name)

        return klass

    return decorator