Contact Info
============

Group Members & Email Addresses:

    Person 1, person1@uky.edu
    Person 2, person2@uky.edu

Versioning
==========

Github Link: 

General Info
============
The current server milestone checks that two TCP clients can connect, receive player-side
assignments, and relay newline-delimited JSON messages to each other. It does not yet run
the Pong game or synchronize game state.

Install Instructions
====================

Run the following line to install the required libraries for this project:

`pip3 install -r requirements.txt`

Connectivity Test
=================
From the project root, run:

`python -m unittest discover -s pong -p "test_*.py"`

Start the server with:

`python pong/pongServer.py`

Connect two clients to the server host on port 5000. The first client receives the `left`
assignment and the second receives `right`. After the welcome message, each client can
send a newline-terminated JSON message; the server forwards it unchanged to the other
client. The automated test uses two local sockets to verify both directions.
