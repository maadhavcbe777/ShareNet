import socket
import sys
import threading
import pickle
import traceback
import re
import queue
import time

max_byte = 1024


class Peer:
  def __init__(self, host, port, no_of_connections):
    self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.host = host  # ip address of the server
    self.port = port  # portNo of the server
    print("\n")
    print(self.host, ":", self.port)
    self.no_of_connections = no_of_connections  # maximum no.of.connections

    try:
      self.s.connect((self.host, self.port))
      # trying for connection with the server
    except ConnectionRefusedError:
      print("Failed to establish connection with server\n")
      sys.exit()
    except TimeoutError:
      print('\npeer not responding connection failed\n')
      sys.exit()
    else:
      # receiving peerId and port of the peer
      a = self.s.recv(max_byte)
      a = pickle.loads(a)
      print("\nConnection Established:\nPeer_ID:", a[0])
      self.peerport = a[1]

  def download(self, addr, file_name):
    try:
      # downloading the file and Creating a client mode
      print(addr)
      self.s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.s1.connect(addr)
      self.s1.send(pickle.dumps(file_name))
      a = pickle.loads(self.s1.recv(max_byte))
      process_res = False  # Result of the process

      if a == 'filefound':
        print("File found in the host peer")
        self.s1.send(pickle.dumps('send'))
        # opening the output file
        file = open("output-files/" + file_name, 'wb')
        data = self.s1.recv(max_byte)
        print("data: ", data)
        # writing into the file
        while True:
          eof = 'end'
          a = re.findall(eof, str(data))
          if a:
            break
          file.write(data)
          data = self.s1.recv(max_byte)
        file.flush()
        file.close()

        self.s1.send(pickle.dumps('received'))  # Acknowledgement to host peer
        process_res = True  # File sharing process successful
        self.s1.close()
      elif a == 'filenotfound':
        process_res = False  # File sharing process failed
        self.s1.close()
    except ConnectionRefusedError:
      print("Connection not able to establish with server")
      process_res = False  
    except TimeoutError:
      print("Peer not responding. Connection failed")
      process_res = False  
    return process_res

  def senddata(self, client, addr, que):
    try:
      print("Preparing for sending to peer")
      # sending the file from the peer containing it
      file_name = client.recv(max_byte)
      file_name = pickle.loads(file_name)
      f = open(file_name, 'rb')
      msg = 'filefound'
      client.send(pickle.dumps(msg))
      ack = pickle.loads(client.recv(max_byte))
      if ack == 'send':
        # reading the file
        a = f.read(max_byte)
        while bool(a):
          client.send(a)
          a = f.read(max_byte)
        f.close()
        time.sleep(1)
        client.send(pickle.dumps('end'))
        data = pickle.loads(client.recv(max_byte))
        # if reply is received file is sent
        if data == 'received':
          print(file_name + ' sent')
          client.close()
    except FileNotFoundError:
      a = "filenotfound"
      client.send(pickle.dumps(a))
      que.put(False)
    except:
      print("File transfer failed")
      que.put(False)
    else:
      que.put('okay')

  def search(self, file_name):
    # searching for the file in the centralized server
    self.s.send(pickle.dumps('search'))
    a = False
    reply = self.s.recv(max_byte)
    # reply from server
    if pickle.loads(reply) == 'ok':
      self.s.send(pickle.dumps(file_name))
      data = self.s.recv(max_byte)
      data = pickle.loads(data)
      if data == 'found':
        print("File found")
        proceed = input("Proceed further to download(y/n): ")
        if proceed == 'y':
          self.s.send(pickle.dumps('send'))
          data = self.s.recv(max_byte)
          data = pickle.loads(data)
          if len(data) == 1:
            # only one peer contains the file
            self.s.send(pickle.dumps(data[0]))
          else:
            # In case of many peers, the peerId of the peer process from which peer file
            # has to be extracted must be specified
            print("Select the peer from which the file has to be extracted")
            for i in range(len(data)):
              print(i + 1, "-> ", data[i])
            choice = int(input("Enter the choice of the peer: "))
            self.s.send(pickle.dumps(data[choice - 1]))

          print("Receiving address of the peer having file from server ...")
          addr = pickle.loads(self.s.recv(max_byte))
          a = self.download(addr, file_name)
        elif proceed == 'n':
          self.s.send(pickle.dumps('n'))
          a = 'sch'  # Only search was performed
      elif data == 'not found':
        print("File not found in any peer")
        a = False
    return a

  def seed(self):
    try:
      # making the peer for seeding
      self.s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.host1 = socket.gethostbyname(socket.gethostname())  # host of the peer
      self.s1.bind((self.host1, self.peerport))
      self.s1.listen(self.no_of_connections)

      print("Peer host: ", self.host, "\tPeer port: ", self.peerport)
      print("Seeding mode ...")

      while True:
        # accepting clients
        client, addr = self.s1.accept()
        print("Connected with " + str(addr[0]), ":", addr[1])

        try:
          que = queue.Queue()
          # creating threads for peers individually
          t = threading.Thread(target=self.senddata, args=(client, addr, que))
          t.start()
          var = que.get()
          self.s1.close()
          return var
        except:
          print("Thread did not start")
          traceback.print_exc()
    except KeyboardInterrupt:
      print("seeding stopped")
    return True

  def register(self, file_name):
    # for registering the file
    self.s.send(pickle.dumps('register'))
    reply = pickle.loads(self.s.recv(max_byte))
    # asking for reply
    if reply == 'ok':
      self.s.send(pickle.dumps(file_name))
      reply = pickle.loads(self.s.recv(max_byte))
      if reply == 'success':
        return True
      else:
        return False
    else:
      return False

  def quit(self):
    self.s.send(pickle.dumps('quit'))
    if pickle.loads(self.s.recv(max_byte)) == 'ok':
      self.s.close()
      sys.exit(0)


if __name__ == "__main__":
  # Entering the ip address and portNo of the server
  ip_address = input("\nEnter the IP address of the server: ")
  port_no = int(input("Enter the port no of the server: "))

  p = Peer(ip_address, port_no, 5)

  while True:
    # methods which can be done
    # select any one of the below
    print("\n\n1. Register file with server")
    print("2. Seeding mode(Upload)")
    print("3. Search and Download")
    print("4. Quit")

    choice = int(input("\nEnter your choice(1/2/3/4): "))
    if choice == 1:
      # for registering the file
      file_name = input("Enter the filename to register: ")
      try:
        # try opening the file
        file = open(file_name, 'r')
      except FileNotFoundError:
        print("File not found in this server\n")
      else:
        file.close()
      a = p.register(file_name)
      
      if a:
        print("Registration successful")
      else:
        print("Registration failed")
    elif choice == 2:
      p.seed()
    elif choice == 3:
      file_name = input("Enter the filename to search: ")
      b = p.search(file_name)
      if b == 'sch':
        print("Only search successful")
      else:
        if b:
          print("Search and download successful")
        else:
          print("Search and download failed")
    elif choice == 4:
      p.quit()
