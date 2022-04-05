# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2013-2021 Sequent Tech Inc <legal@sequentech.io>
# SPDX-FileCopyrightText: 2014-2021 Sequent Tech Inc <legal@sequentech.io>
#
# SPDX-License-Identifier: AGPL-3.0-only

class ActionHandlers(object):
    _static_queue_list = dict()

    @staticmethod
    def add_action_handler(action_name, queue_name, handler_func, kwargs):
        '''
        Adds an action handler to a queue.
        '''
        queue = ActionHandlers._static_queue_list.get(queue_name, dict())
        if queue_name not in ActionHandlers._static_queue_list:
            ActionHandlers._static_queue_list[queue_name] = queue

        if action_name in queue:
            raise Exception("duplicated action handler %s for queue %s" % (
                action_name, queue_name))

        queue[action_name] = kwargs.copy()
        queue[action_name]["handler_func"] = handler_func

    @staticmethod
    def get_action_handler(action_name, queue_name):
        '''
        Get an action handler from a queue, or return None if not found.
        '''
        if queue_name not in ActionHandlers._static_queue_list:
            return None

        queue = ActionHandlers._static_queue_list[queue_name]
        if action_name not in queue:
            return None

        return queue[action_name]

    @staticmethod
    def get_queue(queue_name):
        '''
        Get a queue by name.
        '''
        if queue_name not in ActionHandlers._static_queue_list:
            return None

        return ActionHandlers._static_queue_list[queue_name]

class TaskHandler(object):
    '''
    This is a class-based task handler. Substitutes the function-based
    task handlers.
    '''
    # task member variable will contain a pointer to the task model when
    # TaskHandler.execute is called.
    task = None

    def __init__(self, task):
        self.task = task

    def execute(self):
        '''
        Executes the task handler.

        Reimplementing this function is optional but highly recommendable.
        '''
        pass

    def handle_error(self, error):
        '''
        Handles an error occured during the execution of this task of a subtask.

        By default does nothing and then the error is propagated to the parent
        task. If you reimplement this function, you can stop propagation by
        setting self.task.propagate = False.
        '''
        pass

class SynchronizedSubtaskHandler(TaskHandler):
    '''
    A task handler for tasks whose parent (which could be a remote parent) is
    a SynchronizedTask.
    '''

    def reserve(self):
        '''
        called when the task is going to be reserved. Return data will be sent
        to the task sender and set as reservation_data.

        Implementing this function is optional.
        '''
        pass

    def cancel_reservation(self):
        '''
        called when the task, for some reason (perhaps an error ocurred, or
        maybe the reservation just timedout), is going to be unreserved.

        Implementing this function is optional.
        '''
        pass


class SynchronizedTaskHandler(TaskHandler):
    '''
    A task handler for synchronized tasks. This deals with synchronization data
    coming and being sent to subtasks.
    '''

    def new_reservation(self, subtask):
        '''
        called when the task is going to be reserved.

        subtask.get_data()["reservation_data"] will be set with the data
        returned by SynchronizedSubtaskHandler.reserve.

        Implementing this function is optional.
        '''
        pass

    def cancelled_reservation(self, subtask):
        '''
        called when the subtask, for some reason (perhaps an error ocurred, or
        maybe the reservation just timedout), is going to be unreserved.
        '''
        pass

    def pre_execute(self):
        '''
        Called after the subtasks have been executed, just before the signal
        to start the execution of all subtasks is going to be sent.

        It's the last opportunity to modify the input_data of each subtask
        before that data is sent to the subtasks for execution. Here's an
        example of how to do that:

        child = self.task.get_children()[0]
        child.task_model.input_data["last_minute_detail"] = "foobar"
        db.session.add(child.task_model)
        db.session.commit()
        '''
        pass