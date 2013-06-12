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
