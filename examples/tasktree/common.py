# -*- coding: utf-8 -*-

#
# SPDX-FileCopyrightText: 2013-2021 Sequent Tech Inc <legal@sequentech.io>
#
# SPDX-License-Identifier: AGPL-3.0-only
#
from frestq import decorators

@decorators.task(action="testing.goodbye_cruel_world", queue="hello_world")
def goodbye_cruel_world(task):
    username = task.get_data()['input_data']['username']
    print("goodbye %s! sleeping..\n" % username)

    from time import sleep
    sleep(5)

    print("woke up! time to finish =)\n")
    task.set_output_data("goodbye %s!" % username)
