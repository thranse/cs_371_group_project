# =================================================================================================
# Contributing Authors:	    <Anyone who touched the code>
# Email Addresses:          <Your uky.edu email addresses>
# Date:                     <The date the file was last edited>
# Purpose:                  <How this file contributes to the project>
# Misc:                     <Not Required.  Anything else you might want to include>
# =================================================================================================

import socket
import threading

# This function handles data sent by clients
# It will be run seperatly for each client that connects
def handleClient(conn, addr):
    # Define buffer
    buffer = b""

    # Recieve data
    while (True):

        # Receive data
        try:
            data = conn.recv(1024)

        # Disconnect after connection errors
        except (ConnectionAbortedError, ConnectionResetError):
            data = b""

        if not data:
            print("Connection with client", addr, "closed")
            break

        # Filter messages for newline characters
        buffer += data
        while b"\n" in buffer:
            message, buffer = buffer.split(b"\n", 1)

            # Print data
            print ("Received from", addr, ":", message)
            with lock:
                for other in clients:         
                    if other is not conn:
                        other.sendall(message + b"\n")

    # Remove lock and close connection
    with lock:
        if conn in clients:
            clients.remove(conn)
    conn.close()


# Use this file to write your server logic
# You will need to support at least two clients
# You will need to keep track of where on the screen (x,y coordinates) each paddle is, the score 
# for each player and where the ball is, and relay that to each client
# I suggest you use the sync variable in pongClient.py to determine how out of sync your two
# clients are and take actions to resync the games

# Create list of clients
clients = []

# Make a lock
lock = threading.Lock()

# Set up a socket to listen for connections
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("localhost", 5000))
server.listen()
print("Waiting for connection...")

# Accept connection
while True:
    conn, addr = server.accept()

    # Establish lock and add clients
    with lock:
        clients.append(conn)

    # Start a new thread for each client
    t = threading.Thread(target=handleClient, args=(conn, addr), daemon=True)
    t.start()

    