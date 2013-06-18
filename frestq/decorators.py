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

from functools import wraps

from .action_handlers import ActionHandlers
from .fscheduler import FScheduler

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

        def wrapped(*args, **kwargs):
            '''
            This is the runtime wrapper, called when a wrapped function is
            being called.
            '''
            # TODO: Place some callbacks in the scheduler
            return view_func(*args, **kwargs)
        return wraps(view_func)(wrapped)
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
        ActionHandlers.add_action_handler(action, queue, view_func, kwargs)
        FScheduler.reserve_scheduler(queue)

        def wrapped(*args, **kwargs):
            '''
            This is the runtime wrapper, called when a wrapped function is
            being called.
            '''
            return view_func(*args, **kwargs)
        return wraps(view_func)(wrapped)
    return decorator
