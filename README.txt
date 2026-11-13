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
assignments, and play a server-authoritative game. The server validates paddle updates,
advances the ball, handles collisions and scoring, and broadcasts shared snapshots at 60
updates per second.

Protocol Contract
=================
The protocol is defined in `pong/protocol.py`. Messages are UTF-8 JSON objects, one per
newline-terminated frame. TCP may split or combine frames, so the receiving side must
buffer bytes until it has a complete line.

The server owns the game state: player paddle positions, ball position and velocity, and
both scores. A client sends only its own paddle's top-edge y coordinate and a per-client,
non-negative input sequence number:

`{"type":"paddle","sequence":7,"y":215.0}`

The server sends both clients an initial state snapshot and then a snapshot for each
server tick. The snapshot sequence increases each tick:

`{"type":"state","sequence":42,"left_paddle_y":215.0,"right_paddle_y":200.0,"ball_x":320.0,"ball_y":240.0,"ball_vx":-5.0,"ball_vy":0.0,"left_score":1,"right_score":0}`

On connection, the server sends a welcome frame containing protocol version, assigned
side (`left` or `right`), and screen dimensions. It accepts only increasing paddle input
sequences. The ball bounces from the walls and paddles; a missed ball awards a point and
resets it toward the player who scored. The first player to five points wins, after which
the server freezes the ball. The client should apply the ball, score, and paddle values in
each state snapshot to render the authoritative game; the current client still simulates
the ball and score locally.

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

Connect two clients to the server computer's reachable IP address on port 12345. The
first client receives the `left` assignment and the second receives `right`. Each client
sends newline-delimited paddle updates; the server runs the game and sends state snapshots
to both players. The automated tests exercise both the production server and the game
physics.
