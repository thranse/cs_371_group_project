import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("localhost", 5000))
buffer = b""

while True:
    data = client.recv(1024)
    if not data:
        break
    
    buffer += data
    while b"\n" in buffer:
        message, buffer = buffer.split(b"\n", 1)
        print("Received from server:", message.decode())