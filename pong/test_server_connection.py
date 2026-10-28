"""Integration tests for the two-client TCP connectivity server."""

import json
import socket
import threading
import unittest

from pongServer import serve_clients


class ServerConnectionTests(unittest.TestCase):
    """Verify client handshakes and message relay over TCP."""

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
        return client

    @staticmethod
    def receive_message(client: socket.socket) -> dict[str, object]:
        """Read one newline-delimited JSON message from a client socket."""
        data = bytearray()
        while not data.endswith(b"\n"):
            chunk = client.recv(4096)
            if not chunk:
                raise AssertionError("Server closed the connection before a message arrived")
            data.extend(chunk)
        return json.loads(data.decode("utf-8"))

    def test_two_clients_receive_sides_and_relay_messages(self) -> None:
        """The server should assign sides and relay messages both ways."""
        left_client = self.connect_client()
        right_client = self.connect_client()

        self.assertEqual(self.receive_message(left_client)["player"], "left")
        self.assertEqual(self.receive_message(right_client)["player"], "right")

        left_message = b'{"type":"test","message":"hello from left"}\n'
        right_message = b'{"type":"test","message":"hello from right"}\n'

        left_client.sendall(left_message)
        self.assertEqual(self.receive_message(right_client)["message"], "hello from left")

        right_client.sendall(right_message)
        self.assertEqual(self.receive_message(left_client)["message"], "hello from right")


if __name__ == "__main__":
    unittest.main()
