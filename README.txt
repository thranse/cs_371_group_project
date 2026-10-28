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

Protocol Contract
=================
The protocol is defined in `pong/protocol.py`. Messages are UTF-8 JSON objects, one per
newline-terminated frame. TCP may split or combine frames, so the receiving side must
buffer bytes until it has a complete line.

The server owns the game state: player paddle positions, ball position and velocity, and
both scores. A client sends only its own paddle's top-edge y coordinate and a per-client,
non-negative input sequence number:

`{"type":"paddle","sequence":7,"y":215.0}`

The server sends both clients a state snapshot. Its monotonically increasing sequence is
the server tick:

`{"type":"state","sequence":42,"left_paddle_y":215.0,"right_paddle_y":200.0,"ball_x":320.0,"ball_y":240.0,"ball_vx":-5.0,"ball_vy":0.0,"left_score":1,"right_score":0}`

On connection, the server sends a welcome frame containing protocol version, assigned
side (`left` or `right`), and screen dimensions. The current relay server has not yet been
updated to enforce this contract or run the authoritative game loop.

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
