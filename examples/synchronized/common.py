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


from frestq import decorators
from frestq.app import app
from frestq.action_handlers import SynchronizedSubtaskHandler
from frestq.utils import dumps

from threading import Lock


# list of reserved ports
_byebye_ports = list()
_byebyes_lock = Lock()

@decorators.task(action="testing.goodbye_cruel_world", queue="goodbye_world")
class GoodbyeCruelWorldHandler(SynchronizedSubtaskHandler):
    def reserve(self):
        range_min, range_max = app.config.get('BYEBYE_PORT_RANGE')
        port = None
        with _byebyes_lock:
            for port in xrange(range_min, range_max):
                if port not in _byebye_ports:
                    _byebye_ports.append(port)
                    break

        self.task.set_reservation_data(dict(port=port))

    def cancel_reservation(self):
        port = self.task.get_reservation_data()['port']
        with _byebyes_lock:
            if port in _byebye_ports:
                _byebye_ports.remove(port)

    def execute(self):
        username = self.task.get_data()['input_data']['username']
        print "our reservation: ", dumps(self.task.get_reservation_data())
        print "others reservation: ", dumps(self.task.get_data()['input_data'])

        print "woke up! time to finish =)\n"
        server_name = app.config.get('SERVER_NAME')

        # free the port
        self.cancel_reservation()

        self.task.set_output_data("goodbye %s from port %d in server %s!" % (
            username,
            self.task.get_reservation_data()['port'],
            app.config.get('SERVER_NAME')
        ))
