# =================================================================================================
# Contributing Authors: Ethan Winston
# Email Addresses: etwi236@uky.edu 
# Date:
# Purpose: Accept two test clients and relay messages between them.
# Misc:
# =================================================================================================

from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ContextManager, Literal, Sequence, TypedDict

if TYPE_CHECKING:
    from .protocol import GameState, PaddleUpdate, ProtocolMessage

if __package__:
    from .protocol import (
        PADDLE_HEIGHT,
        SCREEN_HEIGHT,
        SCREEN_WIDTH,
        decode_paddle_update,
        encode_message,
        make_welcome,
    )
else:
    from protocol import (
        PADDLE_HEIGHT,
        SCREEN_HEIGHT,
        SCREEN_WIDTH,
        decode_paddle_update,
        encode_message,
        make_welcome,
    )


HOST = "0.0.0.0"
PORT = 12345
PLAYER_SIDES: tuple[Literal["left", "right"], ...] = ("left", "right")
MAX_MESSAGE_BYTES = 4096
BALL_SIZE = 5
PADDLE_WIDTH = 10
WALL_THICKNESS = 10
WINNING_SCORE = 5
TICK_RATE = 60
TICK_INTERVAL = 1 / TICK_RATE


@dataclass
class ServerGameState:
    """State the server shares between the two connected players."""

    left_paddle_y: float = (SCREEN_HEIGHT / 2) - (PADDLE_HEIGHT / 2)
    right_paddle_y: float = (SCREEN_HEIGHT / 2) - (PADDLE_HEIGHT / 2)
    ball_x: float = SCREEN_WIDTH / 2
    ball_y: float = SCREEN_HEIGHT / 2
    ball_vx: float = -5.0
    ball_vy: float = 0.0
    left_score: int = 0
    right_score: int = 0
    sequence: int = 0
    last_input_sequence: dict[Literal["left", "right"], int] = field(
        default_factory=lambda: {"left": -1, "right": -1}
    )
    lock: ContextManager[bool] = field(default_factory=threading.Lock)
    stopped: threading.Event = field(default_factory=threading.Event)


class PlayerClient(TypedDict):
    side: Literal["left", "right"]
    socket: socket.socket


def send_message(client: socket.socket, message: ProtocolMessage) -> None:
    """Send one newline-delimited JSON message to a connected client."""
    client.sendall(encode_message(message))


def make_state_snapshot(state: ServerGameState) -> GameState:
    """Build the full state message while the caller holds the state lock."""
    return {
        "type": "state",
        "sequence": state.sequence,
        "left_paddle_y": state.left_paddle_y,
        "right_paddle_y": state.right_paddle_y,
        "ball_x": state.ball_x,
        "ball_y": state.ball_y,
        "ball_vx": state.ball_vx,
        "ball_vy": state.ball_vy,
        "left_score": state.left_score,
        "right_score": state.right_score,
    }


def broadcast_state(
    clients: tuple[PlayerClient, PlayerClient], state: ServerGameState
) -> None:
    """Send the same consistent server snapshot to each connected player."""
    with state.lock:
        message = make_state_snapshot(state)
        frame = encode_message(message)
        for player in clients:
            player["socket"].sendall(frame)


def apply_paddle_update(
    state: ServerGameState,
    side: Literal["left", "right"],
    update: PaddleUpdate,
) -> None:
    """Apply a newer client input to that player's paddle."""
    with state.lock:
        if update["sequence"] <= state.last_input_sequence[side]:
            raise ValueError("paddle sequence must increase for each player")

        if side == "left":
            state.left_paddle_y = update["y"]
        else:
            state.right_paddle_y = update["y"]
        state.last_input_sequence[side] = update["sequence"]


def step_game_state(state: ServerGameState) -> None:
    """Advance the authoritative ball and scoring state by one server tick."""
    with state.lock:
        state.sequence += 1
        if max(state.left_score, state.right_score) >= WINNING_SCORE:
            return

        state.ball_x += state.ball_vx
        state.ball_y += state.ball_vy

        if state.ball_y <= WALL_THICKNESS and state.ball_vy < 0:
            state.ball_y = float(WALL_THICKNESS)
            state.ball_vy *= -1
        elif (
            state.ball_y + BALL_SIZE >= SCREEN_HEIGHT - WALL_THICKNESS
            and state.ball_vy > 0
        ):
            state.ball_y = float(SCREEN_HEIGHT - WALL_THICKNESS - BALL_SIZE)
            state.ball_vy *= -1

        left_paddle_x = WALL_THICKNESS
        right_paddle_x = SCREEN_WIDTH - WALL_THICKNESS - PADDLE_WIDTH
        ball_right = state.ball_x + BALL_SIZE
        ball_bottom = state.ball_y + BALL_SIZE

        if (
            state.ball_vx < 0
            and state.ball_x <= left_paddle_x + PADDLE_WIDTH
            and ball_right >= left_paddle_x
            and ball_bottom > state.left_paddle_y
            and state.ball_y < state.left_paddle_y + PADDLE_HEIGHT
        ):
            state.ball_x = float(left_paddle_x + PADDLE_WIDTH)
            state.ball_vx = abs(state.ball_vx)
            state.ball_vy = float(
                (int(state.ball_y) + BALL_SIZE // 2
                 - (int(state.left_paddle_y) + PADDLE_HEIGHT // 2)) // 2
            )
        elif (
            state.ball_vx > 0
            and ball_right >= right_paddle_x
            and state.ball_x <= right_paddle_x + PADDLE_WIDTH
            and ball_bottom > state.right_paddle_y
            and state.ball_y < state.right_paddle_y + PADDLE_HEIGHT
        ):
            state.ball_x = float(right_paddle_x - BALL_SIZE)
            state.ball_vx = -abs(state.ball_vx)
            state.ball_vy = float(
                (int(state.ball_y) + BALL_SIZE // 2
                 - (int(state.right_paddle_y) + PADDLE_HEIGHT // 2)) // 2
            )

        if state.ball_x > SCREEN_WIDTH:
            state.left_score += 1
            reset_ball(state, direction=-1)
        elif state.ball_x < 0:
            state.right_score += 1
            reset_ball(state, direction=1)


def reset_ball(state: ServerGameState, direction: Literal[-1, 1]) -> None:
    """Place the ball at center after a point and set its horizontal direction."""
    state.ball_x = SCREEN_WIDTH / 2
    state.ball_y = SCREEN_HEIGHT / 2
    state.ball_vx = float(5 * direction)
    state.ball_vy = 0.0


def handle_client(
    player: PlayerClient,
    clients: tuple[PlayerClient, PlayerClient],
    state: ServerGameState,
) -> None:
    """Read, validate, and apply newline-delimited paddle updates from a player."""
    pending = bytearray()
    try:
        while not state.stopped.is_set():
            chunk = player["socket"].recv(4096)
            if not chunk:
                break
            pending.extend(chunk)
            while b"\n" in pending:
                line, _, remainder = pending.partition(b"\n")
                pending = bytearray(remainder)
                frame = line + b"\n"
                if len(frame) > MAX_MESSAGE_BYTES:
                    raise ValueError("client message exceeds the maximum frame size")
                update = decode_paddle_update(frame)
                apply_paddle_update(state, player["side"], update)
            if len(pending) >= MAX_MESSAGE_BYTES:
                raise ValueError("client message exceeds the maximum frame size")
    except OSError as error:
        if not state.stopped.is_set():
            print(f"{player['side']} client connection closed: {error}")
    except ValueError as error:
        print(f"Invalid message from {player['side']} client: {error}")
    finally:
        stop_session(clients, state)


def stop_session(
    clients: Sequence[PlayerClient], state: ServerGameState
) -> None:
    """Stop the two-player session and unblock the other client's reader."""
    if state.stopped.is_set():
        return
    state.stopped.set()
    for player in clients:
        try:
            player["socket"].shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


def run_game_loop(
    clients: tuple[PlayerClient, PlayerClient], state: ServerGameState
) -> None:
    """Advance and broadcast authoritative game state at a fixed update rate."""
    next_tick = time.monotonic()
    while not state.stopped.is_set():
        next_tick += TICK_INTERVAL
        step_game_state(state)
        try:
            broadcast_state(clients, state)
        except OSError as error:
            print(f"Client connection closed while broadcasting game state: {error}")
            stop_session(clients, state)
            return

        delay = next_tick - time.monotonic()
        if delay > 0:
            state.stopped.wait(delay)
        else:
            next_tick = time.monotonic()


def serve_clients(server_socket: socket.socket) -> None:
    """Accept two clients and run their server-authoritative Pong session."""
    clients: list[PlayerClient] = []
    handlers: list[threading.Thread] = []
    state = ServerGameState()
    try:
        for player, side in enumerate(PLAYER_SIDES, start=1):
            connection, address = server_socket.accept()
            client: PlayerClient = {"side": side, "socket": connection}
            clients.append(client)
            print(f"Player {player} connected from {address}")

        for client in clients:
            send_message(
                client["socket"],
                make_welcome(client["side"]),
            )

        client_pair = (clients[0], clients[1])
        broadcast_state(client_pair, state)
        handlers = [
            threading.Thread(
                target=handle_client,
                args=(client, client_pair, state),
                daemon=True,
            )
            for client in client_pair
        ]
        for handler in handlers:
            handler.start()
        run_game_loop(client_pair, state)
    finally:
        stop_session(clients, state)
        for handler in handlers:
            handler.join(timeout=1)
        for client in clients:
            client["socket"].close()


def main() -> None:
    """Start the two-client connectivity server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(2)
        print(f"Waiting for two clients on {HOST}:{PORT}")
        serve_clients(server_socket)


if __name__ == "__main__":
    main()
