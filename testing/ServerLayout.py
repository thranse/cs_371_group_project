# ServerLayout.py
import socket
 
HOST = '0.0.0.0' # accepts connections from any IP address
PORT = 12345
BUFFER_SIZE = 1024
 
def start_server():
    # Create a TCP socket (SOCK_STREAM) using IPv4 (AF_INET)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # Allow reusing the port if the server restarts (avoids "address in use" errors)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind the socket to the host and port
        server_socket.bind((HOST, PORT))
        
        # Listen for incoming connections (backlog=5: max 5 pending connections)
        server_socket.listen(5)
        print(f"Server listening on {HOST}:{PORT}...")
 
        while True:  # Main loop: accept clients indefinitely
            # Accept a client connection (blocks until a client connects)
            client_socket, client_addr = server_socket.accept()
            print(f"\nNew connection from {client_addr}")
 
            with client_socket:  # Automatically closes the client socket when done
                connected = True
                while connected:  # Inner loop: communicate with the client
                    # Receive data from the client (blocks until data is received)
                    data = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                    
                    if not data:  # Client closed the connection abruptly
                        print(f"Client {client_addr} disconnected abruptly")
                        break
                    
                    print(f"Received from {client_addr}: {data}")
 
                    # Handle exit command
                    if data.lower() == 'exit':
                        response = "Goodbye! Closing connection."
                        client_socket.sendall(response.encode('utf-8'))
                        connected = False
                        print(f"Client {client_addr} requested exit. Connection closed.")
                    else:
                        # Process data and send a response
                        response = f"Server received: '{data}' (length: {len(data)})"
                        client_socket.sendall(response.encode('utf-8'))
 
if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\nServer shutting down (Ctrl+C pressed)")