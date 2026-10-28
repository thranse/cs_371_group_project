import socket
serverName = '127.0.0.1'
serverPort = 12000

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientSocket.connect((serverName, serverPort))

sentence = input("Input lowercase sentence: ")
clientSocket.sendall(sentence.encode())

modifiedSentence = clientSocket.recv(1024).decode()
print("From Server:", modifiedSentence)
clientSocket.close()