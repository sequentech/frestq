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

@decorators.task(action="testing.goodbye_cruel_world", queue="hello_world")
def goodbye_cruel_world(task):
    username = task.get_data()['input_data']['username']
    print "goodbye %s! sleeping..\n" % username

    from time import sleep
    sleep(5)

    print "woke up! time to finish =)\n"
    task.set_output_data("goodbye %s!" % username)
