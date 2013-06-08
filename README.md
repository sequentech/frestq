frestq - Federated REST Task Queue
==================================

Introduction
------------

frestq implements a federated rest task queue. It allows the orchestration of
tasks with different peers with no central coordination authority.

It's developed in python with flask and sqlalchemy. It uses REST Message Queuing
Protocol (RESTQP) for communication of tasks between any two peers.

Installation
------------

1. Install requirements.txt

```
    $ pip install -r requirements.txt
```

2. Configure you database connection creating a custom_settings.py and
   editting SQLALCHEMY_DATABASE_URI (by default uses sqlite). You sohuld also
   set DEBUG=False and change loggin level if you're running a production
   instance.

3. Create the database:

```
    $ python create_db.py
```

3. Run it! It's flask, s http://flask.pocoo.org/docs/deploying/ . Use the following
   command to run it in a development environment/debug mode:

```
    $ python app.py
```