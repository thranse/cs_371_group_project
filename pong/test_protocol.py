"""Tests for the Pong wire-message contract."""

import json
import unittest

from pong.protocol import (
    PADDLE_TOP_MAX,
    PADDLE_TOP_MIN,
    decode_paddle_update,
    encode_message,
    make_paddle_update,
    make_welcome,
)


class ProtocolTests(unittest.TestCase):
    """Verify protocol message shapes and validation."""

    def test_welcome_assigns_side_and_screen_dimensions(self) -> None:
        """A welcome message identifies the player and protocol version."""
        self.assertEqual(
            make_welcome("left"),
            {
                "type": "welcome",
                "protocol_version": 1,
                "player": "left",
                "width": 640,
                "height": 480,
            },
        )

    def test_paddle_update_round_trips_as_one_json_line(self) -> None:
        """Paddle input is framed as JSON and contains no client-owned state."""
        update = make_paddle_update(7, 215)
        frame = encode_message(update)

        self.assertTrue(frame.endswith(b"\n"))
        self.assertEqual(
            decode_paddle_update(frame),
            {"type": "paddle", "sequence": 7, "y": 215.0},
        )

    def test_paddle_update_requires_valid_sequence_and_position(self) -> None:
        """Input values outside the agreed protocol are rejected."""
        for sequence in (-1, True, 1.5):
            with self.subTest(sequence=sequence):
                with self.assertRaises(ValueError):
                    make_paddle_update(sequence, 215)

        for y in (PADDLE_TOP_MIN - 1, PADDLE_TOP_MAX + 1, float("nan"), True):
            with self.subTest(y=y):
                with self.assertRaises(ValueError):
                    make_paddle_update(0, y)

    def test_paddle_decoder_rejects_non_paddle_or_extra_client_state(self) -> None:
        """Clients cannot include ball, score, or other player-owned fields."""
        invalid_frames = (
            b'{"type":"state","sequence":0,"y":215}\n',
            b'{"type":"paddle","sequence":0,"y":215,"ball_x":20}\n',
            b'{"type":"paddle","sequence":0,"y":215}',
        )
        for frame in invalid_frames:
            with self.subTest(frame=frame):
                with self.assertRaises(ValueError):
                    decode_paddle_update(frame)

    def test_encoded_welcome_is_json(self) -> None:
        """The shared encoder emits a valid JSON protocol frame."""
        frame = encode_message(make_welcome("right"))
        self.assertEqual(json.loads(frame.decode("utf-8")), make_welcome("right"))


if __name__ == "__main__":
    unittest.main()
