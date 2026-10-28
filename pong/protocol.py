"""Wire-message definitions for the Pong client/server protocol."""

import json
import math
from typing import Literal, TypedDict, Union


PROTOCOL_VERSION = 1
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480
PADDLE_HEIGHT = 50
PADDLE_TOP_MIN = 10
PADDLE_TOP_MAX = SCREEN_HEIGHT - PADDLE_TOP_MIN - PADDLE_HEIGHT


class WelcomeMessage(TypedDict):
    type: Literal["welcome"]
    protocol_version: int
    player: Literal["left", "right"]
    width: int
    height: int


class PaddleUpdate(TypedDict):
    type: Literal["paddle"]
    sequence: int
    y: float


class GameState(TypedDict):
    type: Literal["state"]
    sequence: int
    left_paddle_y: float
    right_paddle_y: float
    ball_x: float
    ball_y: float
    ball_vx: float
    ball_vy: float
    left_score: int
    right_score: int


ProtocolMessage = Union[WelcomeMessage, PaddleUpdate, GameState]


def make_welcome(player: Literal["left", "right"]) -> WelcomeMessage:
    """Create the initial server message assigning a player and screen size."""
    return {
        "type": "welcome",
        "protocol_version": PROTOCOL_VERSION,
        "player": player,
        "width": SCREEN_WIDTH,
        "height": SCREEN_HEIGHT,
    }


def make_paddle_update(sequence: int, y: Union[int, float]) -> PaddleUpdate:
    """Create a client input containing only its paddle's top-edge y position."""
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise ValueError("sequence must be a non-negative integer")
    if isinstance(y, bool) or not isinstance(y, (int, float)) or not math.isfinite(y):
        raise ValueError("paddle y must be a finite number")
    if not PADDLE_TOP_MIN <= y <= PADDLE_TOP_MAX:
        raise ValueError(
            f"paddle y must be between {PADDLE_TOP_MIN} and {PADDLE_TOP_MAX}"
        )
    return {"type": "paddle", "sequence": sequence, "y": float(y)}


def encode_message(message: ProtocolMessage) -> bytes:
    """Encode one protocol message as a newline-delimited UTF-8 JSON frame."""
    return json.dumps(message, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"


def decode_paddle_update(line: bytes) -> PaddleUpdate:
    """Decode and validate one complete client paddle-update frame."""
    if not line.endswith(b"\n"):
        raise ValueError("message must end with a newline")

    try:
        message = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("message must be valid UTF-8 JSON") from error

    if not isinstance(message, dict) or set(message) != {"type", "sequence", "y"}:
        raise ValueError("paddle update must contain only type, sequence, and y")
    if message["type"] != "paddle":
        raise ValueError("message type must be 'paddle'")
    return make_paddle_update(message["sequence"], message["y"])
