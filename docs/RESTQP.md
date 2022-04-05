<!--
SPDX-FileCopyrightText: 2014-2021 Sequent Tech Inc <legal@sequentech.io>

SPDX-License-Identifier: AGPL-3.0-only
-->

RMQP - REST Message Queue Protocol
==================================

RMQP arised as a way to do the communication between the nodes in frestq. It's
what we call a Dead Simple Protocol consisting on JSON messages exchanged
between two peers with HTTP POST calls on a concrete path on each side.

Each node running the RMQP has a root queues URL, for example this could be
"http://localhost:5000/queues". Messages for a receiver are posted in specificly
named queues, for example to post a message in a queue named "pepito", the
URL where the message should be posted would be
"http://localhost:5000/queues/pepito/".

Schematic example of two messages being sent, one from A to B's manuela queue,
and then another message originating from B to A's pepito queue.

A ------(POST /queues/path/manuela/ [message 1])----------------> B (receiver)


A <-----(POST /queues/path/pepito/ [message 2])------------------ B (sender)

The message is encapsulated in http or https (http + ssl). Both sender and
receiver could be authenticating the ssl transport if they choose to do so.

If the receiver is not available, the sender can store the message and retry
later or discard the message, both are valid options.

The input format of the messages is always on the following form and in UTF-8:

{
    "message_id": "<unique id of the message. required field>",
    "action": "<action text of the message. required field>",
    "sender_url": "<URL where the receiver can send messages to. required field>",
    "data": <put anything you want here, in json format. optional field>,
    "async_data": <see below information about async data. optional field>,
    "pingback_date": "<date in ISO-8601, optional field>",
    "expiration_date": "<date in ISO-8601, optional field>",
    "info": "<information text, optional field>",
    "task_id": <id, required field>
}

Detailed fields description:

* message_id

 Text field of up to 1024 characters. This is a required field.

* action

 Text field of up to 1024 characters. This is a required field, although the
 text could be empty. Indicates the name of the action to be done by the
 receiver. Action name is usually used in the code to discriminate which code
 path should deal with the message.

* sender_url

 Text field of up to 1024 characters. This is a required field and should be a
 URL. This protocol is based on the premise that a receiver always has a way
 of reaching the sender, i.e. it's a peer to peer protocol. Note that this URL
 corresponds with the root queues URL and not with a specific queue URL.

* data

 JSON field of any length. Length is only limited admitted by the backend
 database for VARCHAR. This is the payload of the message, use it as you
 want.

* async_data

 JSON Dictionary field of any length. Length is only limited admitted by the
 backend database for VARCHAR. Each key of this dictionary points to a
 value which should be an URL. This URL is meant to be downloaded locally by the
 receiver asynchronously on the background. Use this to transfer big chunks of
 data in standard ways, like an http/ftp file server. You could use for
 magnet/torrents links too or any other kind of stuff, why not.

* pingback_date

 Optional parameter containing a valid ISO-8601 timezoned date. It's up to the
 receiver to interpret what to do when the pingback_date happens.

* expiration_date

 Optional parameter containing a valid ISO-8601 timezoned date. It's up to the
 receiver to interpret what to do when the expiration_date happens.

* info

 Text field of up to 1024 characters. Optional. It's up to the receiver to
 interpret this text. Used usually as an user readable string for logging
 purpuses.


* task_id

 Optional, format would be user-defined.



The response of the receiver can vary depending on each case, indicated by the
HTTP status code returned:

The response of the receiver can vary depending on each case, indicated by the
HTTP status code returned:

* STATUS 200
 Message correctly received and processed.

* STATUS 503
 Indicates that the queue is full or the service is overloaded. Response will be
 empty. This is usually a temporary state.

* STATUS 400
 Invalid input data. This only happens if the input data doesn't follow the
 format defined previously. Response format is undefined/user-defined.

Other possible typical HTTP status not defined could happen. In general, if a
message is not answered with status 200, the receiver should probably try again
later.
