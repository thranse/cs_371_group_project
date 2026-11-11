import time
import socket

# Connect to client and send messages after delay
# Meant to test the server's ability to handle multiple clients and messages
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("localhost", 5000))
for i in range(10):
    client.sendall(str(i).encode() + b"\n")
    time.sleep(1)