# ClientLayout.py
import socket
 
HOST = 'localhost'  # Must match the server's HOST
PORT = 12345        # Must match the server's PORT
BUFFER_SIZE = 1024
 
def start_client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        try:
            # Connect to the server
            client_socket.connect((HOST, PORT))
            print(f"Connected to server {HOST}:{PORT}. Type 'exit' to quit.")
 
            while True:  # Loop to send multiple messages
                # Get user input
                message = input("Enter message to send: ")
                
                # Send data to the server (encode string to bytes)
                client_socket.sendall(message.encode('utf-8'))
 
                # Exit if user types 'exit'
                if message.lower() == 'exit':
                    # Receive the server's goodbye response
                    response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                    print(f"Server: {response}")
                    break
 
                # Receive response from the server
                response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                print(f"Server response: {response}")
 
        except ConnectionRefusedError:
            print("Error: Could not connect to server. Is the server running?")
        except ConnectionResetError:
            print("Error: Server disconnected abruptly")
 
if __name__ == "__main__":
    start_client()