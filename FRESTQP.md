Introduction
============

FRESTQP is the protocol we use in FRESTQ. It's based on the RESTQP protocol.
The diagram for a simple task is the following:


----------------------------------------------------------------------------> B
 ^=======================(task-19)============|==(task 19 actually starts)==>
 |                  ||           ||           ^
 |                  ||           ||           |
 | new task (id=19) || ack (200) || request   | sends
 |                  ||           || async data| async data
 |                  ||           ||           |
 |                  \/           \/           |
----------------------------------------------------------------------------> A


>---------------------------------------------------------------------------> B
>=======================(task-19 ends >>)==           ^
                                         || send      |
                                         || task      | ack (200)
                                         || update:   |
                                         || finished  |
                                         ||           |
                                         \/           |
>---------------------------------------------------------------------------> A