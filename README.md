frestq - Federated REST Task Queue
==================================

Introduction
------------

frestq implements a federated rest task queue. It allows the orchestration of
tasks with different peers with no central coordination authority.

It's developed in python3 with flask and sqlalchemy. It uses REST Message Queuing
Protocol (RESTQP) for communication of tasks and updates between any two peers.

Installation
------------

The easiest way to install latest stable version of frestq will be to do
"pip install frestq".  However, there's no stable version yet, so in the mean
time tou can proceed to install it manually as when you downloaded it:

1. Download from the git repository if you haven't got a copy

```
    $ git clone https://github.com/agoravoting/frestq && cd frestq
```

2. Install package and its dependencies

```
    $ mkvirtualenv myenv -p $(which python3)
    $ pip install -r requirements.txt
    $ sudo python setup.py install
```

Tutorial
--------

In this simple hello world in frestq, you will need two running frestq server
instances. This due to the fact that frestq is based on the asumption that all
communication is between two peers.

Note: if you want, you can find the example code of this tutorial in
examples/helloworld.

So, you will have launch two different shell sessions. In one of them we will
execute a frestq http server in http://127.0.0.1:5000/ and the other in port
5001. For server A we will just use default settings, but for server B we will
configure port 5001.

First let's see an overall description of how our frestq based service will
work:

 1. user calls to POST http://127.0.0.1:5000/say/hello/<username> in server
 A.
 2. flask view in /say/<message> creates a simple task "hello_world" in queue
 "say_queue" to be executed in server B.
 3. server B receives the "say_hello" task, which is executed by an action
 handler.
 4. After the execution of the action handler, server B sends a "finished"
 status update notification to server A, along with the tasks results, if
 any.

So some notes and observations about this:
 * In frestq, the standard way to launch a task is to launch it within a flask
   view in a frestq server. This reduces the complexity of implementation
   because frestq itself is written with flask, so frestq in fact can be used
   as a library without any out of process comunication going on between the
   flask view code and frestq task sender.

   This also needed because the server receiving a task (in this case, server B)
   asumes that he can communicate the updates to the task sender, which must be
   also a frestq server. So to bootstrap, we need to create tasks to be sent
   within server A frestq process itself. Note that this is not design flaw,
   it's a deliberated design choice for a peer to peer task queue.

 * Tasks are created in a "sender server" (A) and executed in "receiver server"
   (B). What task is to be executed is set by the sender server by specifying
   an "action" to be executed, and a "queue" where that action belongs. This is
   simply a way to dispatch different tasks. The receiving server must have a
   python function that acts as an "action handler". The sender can also send
   some input data to be processed.

 * The communication between servers is completely asynchronous. When the task
   is sent from server A to server B, server B immediately processes the
   incoming message with the task data, and without executing the tasks, returns
   the call to server A just saying "task received". Only after doing that the
   task is executed in a thread in server B. When the task finishes whatever it
   needs to do, then server B contacts back with server A sending a task update
   marking the task as finished and also transferring the output result of the
   task.

 * Because everything is executed asynchronously, the initial
   POST http://127.0.0.1:5000/say/hello/<username> call is executed also in this
   manner. The task is created, sent, and then the flask view returns without
   waiting for the task to finish.

The code of server_a.py is this:

```
#!/usr/bin/env python3
from flask import Blueprint, make_response

from frestq.tasks import SimpleTask
from frestq.app import app, run_app

# set database uri
import os
ROOT_PATH = os.path.split(os.path.abspath(__file__))[0]
SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/db.sqlite' % ROOT_PATH

say_api = Blueprint('say', __name__)

@say_api.route('/hello/<username>', methods=['POST'])
def post_hello(username):
    task = SimpleTask(
        receiver_url='http://127.0.0.1:5001/api/queues',
        action="hello_world",
        queue="say_queue",
        data={
            'username': username
        }
    )
    task.create_and_send()
    return make_response("", 200)

app.register_blueprint(say_api, url_prefix='/say')

if __name__ == "__main__":
    run_app(config_object=__name__)
```

The post_hello is the flask view that initiates the frestq task. This code will
be executed in server A. The "receiver_url" parameter of the SimpleTask created
corresponds with the ROOT_URL of server B.

The code server_b.py is:

```
#!/usr/bin/env python3
from frestq import decorators
from frestq.app import app, run_app

# configuration:

# set database uri
import os
ROOT_PATH = os.path.split(os.path.abspath(__file__))[0]
SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/db2.sqlite' % ROOT_PATH

SERVER_NAME = '127.0.0.1:5001'

SERVER_PORT = 5001

ROOT_URL = 'http://127.0.0.1:5001/api/queues'


# action handler:

@decorators.task(action="hello_world", queue="say_queue")
def hello_world(task):
    print "I'm sleepy!..\n"

    # simulate we're working hard taking our time
    from time import sleep
    sleep(5)

    username = task.get_data()['input_data']['username']
    return dict(
        output_data = "hello %s!" % username
    )

if __name__ == "__main__":
    run_app(config_object=__name__)
```

Note that we use task.task_model to get input data and set output data. Output
data will be sent back to server A transparently after the hello_world function
is executed.

You can create each of these two files in the same folder "example/". Asuming
you have already installed frestq, you can create the db of both servers this
way:

```
    $ python server_a.py --createdb
    $ python server_b.py --createdb
```

To launch each server, **run in different terminals** the following two commands:

```
    $ python server_a.py
    INFO:apscheduler.threadpool:Started thread pool with 0 core threads and 20 maximum threads
    INFO:apscheduler.scheduler:Scheduler started
    INFO:werkzeug: * Running on http://127.0.0.1:5000/
    DEBUG:apscheduler.scheduler:Looking for jobs to run
    DEBUG:apscheduler.scheduler:No jobs; waiting until a job is added
```


```
    $ python server_b.py
    INFO:apscheduler.threadpool:Started thread pool with 0 core threads and 20 maximum threads
    INFO:apscheduler.scheduler:Scheduler started
    INFO:werkzeug: * Running on http://127.0.0.1:5001/
    DEBUG:apscheduler.scheduler:Looking for jobs to run
    DEBUG:apscheduler.scheduler:No jobs; waiting until a job is added
```

And to launch the hello job, execute in another **new third terminal** the
following command:

```
    $ curl -X POST http://127.0.0.1:5000/say/hello/richard.stallman
```

Unfortunately we don't have yet an easy way to know the status of tasks, but if
everything went right, you'll be able to see the following lines at the end of
the output in the shell running server A:

```
    DEBUG:root:SETTING TASK FIELD 'output_data' to 'hello richard.stallman!'
    DEBUG:root:SETTING TASK FIELD 'status' to 'finished'
    INFO:apscheduler.scheduler:Job "call_action_handler (trigger: now, next run at: None)" executed successfully
    DEBUG:apscheduler.threadpool:Exiting worker thread
```

# License

Copyright (C) 2013-2020 Agora Voting SL and/or its subsidiary(-ies).
Contact: legal@agoravoting.com

This file is part of the frestq module of the Agora Voting project.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

Commercial License Usage
Licensees holding valid commercial Agora Voting project licenses may use this
file in accordance with the commercial license agreement provided with the
Software or, alternatively, in accordance with the terms contained in
a written agreement between you and Agora Voting SL. For licensing terms and
conditions and further information contact us at legal@agoravoting.com .

GNU Affero General Public License Usage
Alternatively, this file may be used under the terms of the GNU Affero General
Public License version 3 as published by the Free Software Foundation and
appearing in the file LICENSE.AGPL3 included in the packaging of this file, or
alternatively found in <http://www.gnu.org/licenses/>.

External libraries
This program distributes libraries from external sources. If you follow the
compilation process you'll download these libraries and their respective
licenses, which are compatible with our licensing.