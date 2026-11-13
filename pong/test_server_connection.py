"""Integration tests for the two-player authoritative Pong server."""

import json
import socket
import threading
import time
import unittest
from collections.abc import Callable

from pong.pongServer import (
    BALL_SIZE,
    PADDLE_HEIGHT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    ServerGameState,
    serve_clients,
    step_game_state,
)


class ServerConnectionTests(unittest.TestCase):
    """Verify welcome messages, game ticks, and server-owned game state."""

    def setUp(self) -> None:
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(2)
        self.listener.settimeout(3)
        self.server_thread = threading.Thread(
            target=serve_clients, args=(self.listener,), daemon=True
        )
        self.server_thread.start()
        self.clients: list[socket.socket] = []
        self.buffers: dict[socket.socket, bytearray] = {}

    def tearDown(self) -> None:
        for client in self.clients:
            client.close()
        self.listener.close()
        self.server_thread.join(timeout=3)

    def connect_client(self) -> socket.socket:
        """Connect to the local test server and return the client socket."""
        client = socket.create_connection(self.listener.getsockname(), timeout=3)
        client.settimeout(3)
        self.clients.append(client)
        self.buffers[client] = bytearray()
        return client

    def receive_message(self, client: socket.socket) -> dict[str, object]:
        """Read one newline-delimited JSON message, retaining any extra frames."""
        pending = self.buffers[client]
        while b"\n" not in pending:
            chunk = client.recv(4096)
            if not chunk:
                raise AssertionError("Server closed the connection before a message arrived")
            pending.extend(chunk)
        line, _, remainder = pending.partition(b"\n")
        self.buffers[client] = bytearray(remainder)
        return json.loads(line.decode("utf-8"))

    def connect_players(self) -> tuple[socket.socket, socket.socket]:
        """Connect two players and verify their welcome and initial state."""
        left_client = self.connect_client()
        right_client = self.connect_client()

        left_welcome = self.receive_message(left_client)
        right_welcome = self.receive_message(right_client)
        self.assertEqual((left_welcome["type"], left_welcome["player"]), ("welcome", "left"))
        self.assertEqual(
            (right_welcome["type"], right_welcome["player"]), ("welcome", "right")
        )

        left_state = self.receive_message(left_client)
        right_state = self.receive_message(right_client)
        self.assertEqual(left_state["type"], "state")
        self.assertEqual(right_state["type"], "state")
        self.assertEqual(left_state["left_paddle_y"], right_state["left_paddle_y"])
        self.assertEqual(left_state["right_paddle_y"], right_state["right_paddle_y"])
        return left_client, right_client

    def test_first_client_waits_until_second_client_connects(self) -> None:
        """The server sends no welcome or game state before both players join."""
        first_client = self.connect_client()
        first_client.settimeout(0.1)

        with self.assertRaises(socket.timeout):
            first_client.recv(1)

        first_client.settimeout(3)
        second_client = self.connect_client()
        left_welcome = self.receive_message(first_client)
        right_welcome = self.receive_message(second_client)

        self.assertEqual((left_welcome["type"], left_welcome["player"]), ("welcome", "left"))
        self.assertEqual(
            (right_welcome["type"], right_welcome["player"]), ("welcome", "right")
        )
        self.assertEqual(self.receive_message(first_client)["type"], "state")
        self.assertEqual(self.receive_message(second_client)["type"], "state")

    def wait_for_state(
        self,
        client: socket.socket,
        predicate: Callable[[dict[str, object]], bool],
    ) -> dict[str, object]:
        """Read snapshots until one satisfies a predicate or the socket times out."""
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            state = self.receive_message(client)
            if state.get("type") == "state" and predicate(state):
                return state
        self.fail("No game-state message met the requested condition")

    def test_server_ticks_and_broadcasts_paddle_input(self) -> None:
        """The server advances the ball and reflects paddle input to both players."""
        left_client, right_client = self.connect_players()

        left_client.sendall(b'{"type":"paddle","sequence":0,"y":300}\n')
        left_state = self.wait_for_state(
            left_client, lambda state: state["left_paddle_y"] == 300
        )
        right_state = self.wait_for_state(
            right_client, lambda state: state["left_paddle_y"] == 300
        )

        self.assertGreater(left_state["sequence"], 0)
        self.assertEqual(left_state["left_paddle_y"], right_state["left_paddle_y"])
        self.assertLess(left_state["ball_x"], SCREEN_WIDTH / 2)
        self.assertEqual(left_state["left_score"], 0)
        self.assertEqual(left_state["right_score"], 0)

    def test_invalid_client_state_is_rejected(self) -> None:
        """Clients cannot supply ball or score values in a paddle update."""
        left_client, right_client = self.connect_players()
        left_client.sendall(b'{"type":"paddle","sequence":0,"y":215,"ball_x":100}\n')

        self.assertEqual(left_client.recv(1), b"")
        self.assertEqual(right_client.recv(1), b"")


class GamePhysicsTests(unittest.TestCase):
    """Verify deterministic ball, wall, paddle, and scoring behavior."""

    def test_ball_bounces_off_top_wall(self) -> None:
        """A ball moving into the top wall is clamped and reflected."""
        state = ServerGameState(ball_y=11, ball_vy=-3)
        step_game_state(state)

        self.assertEqual(state.ball_y, 10)
        self.assertEqual(state.ball_vy, 3)

    def test_ball_bounces_from_paddle(self) -> None:
        """A collision reverses horizontal velocity and sets vertical deflection."""
        paddle_y = float(SCREEN_HEIGHT // 2 - PADDLE_HEIGHT // 2)
        state = ServerGameState(
            left_paddle_y=paddle_y,
            ball_x=21,
            ball_y=paddle_y + PADDLE_HEIGHT - BALL_SIZE,
            ball_vx=-5,
            ball_vy=0,
        )
        step_game_state(state)

        self.assertEqual(state.ball_x, 20)
        self.assertEqual(state.ball_vx, 5)
        self.assertGreater(state.ball_vy, 0)

    def test_scoring_resets_ball_and_freezes_at_winning_score(self) -> None:
        """A point increments the correct score, and five points end movement."""
        state = ServerGameState(ball_x=SCREEN_WIDTH, ball_vx=5)
        step_game_state(state)

        self.assertEqual(state.left_score, 1)
        self.assertEqual(state.ball_x, SCREEN_WIDTH / 2)
        self.assertEqual(state.ball_vx, -5)

        state.left_score = 5
        ball_position = (state.ball_x, state.ball_y)
        step_game_state(state)
        self.assertEqual((state.ball_x, state.ball_y), ball_position)

    def test_ball_passing_left_edge_awards_right_player(self) -> None:
        """A ball exiting the left side increments the right player's score."""
        state = ServerGameState(ball_x=0, ball_vx=-5)
        step_game_state(state)

        self.assertEqual(state.right_score, 1)
        self.assertEqual(state.ball_x, SCREEN_WIDTH / 2)
        self.assertEqual(state.ball_vx, 5)


if __name__ == "__main__":
    unittest.main()
