# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2013-2021 Sequent Tech Inc <legal@sequentech.io>
# SPDX-FileCopyrightText: 2014-2021 Sequent Tech Inc <legal@sequentech.io>
#
# SPDX-License-Identifier: AGPL-3.0-only

from inspect import isfunction
from functools import wraps
from flask import request

from .action_handlers import ActionHandlers
from .fscheduler import FScheduler, INTERNAL_SCHEDULER_NAME
from .utils import DecoratorBase

def message_action(action, queue, **kwargs):
    """
    Decorator for message actions
    """
    # Check if perm is given as string in order not to decorate
    # view function itself which makes debugging harder
    if not isinstance(action, str) or not isinstance(queue, str):
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
    if not isinstance(action, str) or not isinstance(queue, str):
        raise Exception("action and queue args for message decorator must be strings")

    def decorator(view_func):
        '''
        This is the static wrapper, called when loading the code a wrapped
        funcion
        '''
        # register view_func as an action handler for the given queue
        kwargs['is_task'] = True
        if view_func is not None and not isfunction(view_func):
            view_func.action = action
            view_func.queue_name = queue
            wrapper_func = view_func
        else:
            def wrapper_func(*args, **kwargs):
                print(f"task: Starting task\n\n")
                ret = view_func(*args, **kwargs)
                print(f"task: Finished task\n\n")
                return ret

        ActionHandlers.add_action_handler(action, queue, wrapper_func, kwargs)
        FScheduler.reserve_scheduler(queue)

        return wrapper_func

    return decorator

class local_task(DecoratorBase):
    '''
    Use to assure that the task is sent from local. This is checked in a secure
    way by checking that the sender SSL certificate is the one specified.

    NOTE: if you use this decorator in a TaskHandler, put it before the task
    decorator or it won't work. Do it as shown in the following code example:

    from frestq import decorators
    from frestq.action_handlers import TaskHandler

    @decorators.local_task
    @decorators.task(...)
    class FooTask(TaskHandler):
       pass
    '''
    def __call__(self, *args):
        from .protocol import certs_differ, SecurityException
        from .app import app

        if  not isfunction(self.func):
            task = self.func.task
        else:
            task = args[0]

        sender_ssl_cert = task.task_model.sender_ssl_cert
        local_ssl_cert = app.config['SSL_CERT_STRING']
        if certs_differ(sender_ssl_cert, local_ssl_cert):
            raise SecurityException()

        print(f"local_task: Starting task.id={task.task_model.id}\n\n")
        ret = self.func(*args)
        print(f"local_task: Finished task.id={task.task_model.id}\n\n")
        return ret

def internal_task(name, **kwargs):
    """
    Decorator for class based internal task handlers
    """

    # Check if perm is given as string in order not to decorate
    # view function itself which makes debugging harder
    if not isinstance(name, str):
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
