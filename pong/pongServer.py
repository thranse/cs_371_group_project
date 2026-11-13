# =================================================================================================
# Contributing Authors: Ethan Winston
# Email Addresses: etwi236@uky.edu 
# Date:
# Purpose: Accept two test clients and relay messages between them.
# Misc:
# =================================================================================================

import socket
import threading
from dataclasses import dataclass, field
from typing import Literal, Sequence, TypedDict

if __package__:
    from .protocol import (
        SCREEN_HEIGHT,
        SCREEN_WIDTH,
        GameState,
        PaddleUpdate,
        ProtocolMessage,
        decode_paddle_update,
        encode_message,
        make_welcome,
    )
else:
    from protocol import (
        SCREEN_HEIGHT,
        SCREEN_WIDTH,
        GameState,
        PaddleUpdate,
        ProtocolMessage,
        decode_paddle_update,
        encode_message,
        make_welcome,
    )


HOST = "0.0.0.0"
PORT = 12345
PLAYER_SIDES: tuple[Literal["left", "right"], ...] = ("left", "right")
MAX_MESSAGE_BYTES = 4096


@dataclass
class ServerGameState:
    """State the server shares between the two connected players."""

    left_paddle_y: float = (SCREEN_HEIGHT / 2) - 25
    right_paddle_y: float = (SCREEN_HEIGHT / 2) - 25
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
    lock: threading.Lock = field(default_factory=threading.Lock)
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
    clients: tuple[PlayerClient, PlayerClient],
    state: ServerGameState,
    side: Literal["left", "right"],
    update: PaddleUpdate,
) -> None:
    """Accept a newer paddle input and broadcast the resulting server state."""
    with state.lock:
        if update["sequence"] <= state.last_input_sequence[side]:
            raise ValueError("paddle sequence must increase for each player")

        if side == "left":
            state.left_paddle_y = update["y"]
        else:
            state.right_paddle_y = update["y"]
        state.last_input_sequence[side] = update["sequence"]
        state.sequence += 1

        frame = encode_message(make_state_snapshot(state))
        for player in clients:
            player["socket"].sendall(frame)


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
                apply_paddle_update(clients, state, player["side"], update)
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


def serve_clients(server_socket: socket.socket) -> None:
    """Accept two clients, exchange welcome/state messages, and process inputs."""
    clients: list[PlayerClient] = []
    state = ServerGameState()
    try:
        for player, side in enumerate(PLAYER_SIDES, start=1):
            connection, address = server_socket.accept()
            client: PlayerClient = {"side": side, "socket": connection}
            clients.append(client)
            print(f"Player {player} connected from {address}")
            send_message(connection, make_welcome(side))

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
        for handler in handlers:
            handler.join()
    finally:
        stop_session(clients, state)
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
