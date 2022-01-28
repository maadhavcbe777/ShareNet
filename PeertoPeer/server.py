import socket
import uuid
import pickle
import threading
import sys

max_byte = 1024


class Server:
  def __init__(self, port, no_of_connections):
    self.port = port  # portNo of this machine
    self.host = socket.gethostbyname(socket.gethostname())  # ip of this machine
    self.no_of_connections = no_of_connections  # no.of connections
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    self.file = {}  # list of files registered
    self.peers = {}  # list of peers connected

    x = True
    while x:
      try:
        self.sock.bind((self.host, self.port))
      except OverflowError:
        self.port = input("Enter new port(>3000)")  # alternative portNo
      else:
        x = False

    print("listening through [", self.host, ":", self.port, "]")

  def peer_threads(self, client, addr):
      
    # generates unique id for each peer
    peer_id = uuid.uuid4().int >> 115

    print(addr)
    new_addr = (self.host, addr[1])
    print(new_addr)
    
    # appending peer specifications to list of peers
    self.peers[peer_id] = new_addr

    # sending peerId to the recipient and also the portNo for connection
    client.send(pickle.dumps((peer_id, addr[1])))


    while True:
      method = pickle.loads(client.recv(max_byte))

      print("Method opted by peer_id-", peer_id, " is ", method)

      if method == "search":
        # searching a file in the centralized server
        client.send(pickle.dumps("ok"))
        
        # loading up the name of the file needed for searching
        file_name = pickle.loads(client.recv(max_byte))


        if file_name in self.file:
          client.send(pickle.dumps('found'))
          
          # getting reply from the peer whether to send or not
          reply = pickle.loads(client.recv(max_byte))


          if reply == 'send':  # peer requests for downloading the file
            content = pickle.dumps(self.file[file_name])
            client.send(content)

            # In case of files contained by many peers
            # selection of file from which peer is needed
            peer_no = pickle.loads(client.recv(max_byte))
            client.send(pickle.dumps(self.peers[peer_no]))
          else:
            "Only search was performed.."
        else:
          client.send(pickle.dumps("File not found"))

      elif method == 'register':
        # registering files to the server by peers in order to access
        client.send(pickle.dumps('ok'))
        file_name = pickle.loads(client.recv(max_byte))
        print("For registering file by peer_id-", peer_id)

        if file_name in self.file:
          self.file[file_name].append(peer_id)

        else:
          # new file list created and peerIds are appended
          self.file[file_name] = []
          self.file[file_name].append(peer_id)

        client.send(pickle.dumps('success'))

      elif method == 'quit':
        client.send(pickle.dumps('ok'))

        list1 = []

        # peerIds present in the files are deleted in file list

        for i in self.file:
          try:
            self.file[i].remove(peer_id)
            if self.file[i] == []:
              list1.append(i)
          except ValueError:
            continue

        # peerIds are deleted in peers list
        del self.peers[peer_id]
        sys.exit(0)

  def connections(self):
    thread_id = []
    self.sock.listen(self.no_of_connections)

    while True:
      client, addr = self.sock.accept()  # accepting connections
      print("Connected with ", addr)

      # thread creation for each peer
      try:
        # creating threads and passing arguments
        t = threading.Thread(target=self.peer_threads, args=(client, addr))
        
        # starting the thread
        t.start()

        print("\nThread started")
      except:
        print("\nThread didn't start")

    self.sock.close()


if __name__ == '__main__':
  port = 9000
  s = Server(port, 5)
  s.connections()
