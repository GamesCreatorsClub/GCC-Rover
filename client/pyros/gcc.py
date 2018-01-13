
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import pygame
import pyros
import threading
import time
import socket
import netifaces

rovers = []

# {
#     "rover2": {
#         "address": "172.24.1.184",
#         "port": 1883
#     },
#     "rover3": {
#         "address": "172.24.1.185",
#         "port": 1883
#     },
#     "rover4": {
#         "address": "172.24.1.186",
#         "port": 1883
#     },
#     "rover2proxy": {
#         "address": "gcc-wifi-ap",
#         "port": 1884
#     },
#     "rover3proxy": {
#         "address": "gcc-wifi-ap",
#         "port": 1885
#     },
#     "rover4proxy": {
#         "address": "gcc-wifi-ap",
#         "port": 1886
#     },
# }

selectedRover = 0

THIS_PORT = 0xd15d
DISCOVERY_PORT = 0xd15c
WAIT_TIMEOUT = 20 # 5 seconds

sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sckt.bind(('', THIS_PORT))
broadcasts = []

def poplulateBroadcasts():
    ifacenames = netifaces.interfaces()
    for ifname in ifacenames:
        addrs = netifaces.ifaddresses(ifname)

        for d in addrs:
            for dx in addrs[d]:
                if "broadcast" in dx:
                    broadcasts.append(dx["broadcast"])


def removeFromList(ip, port):
    for i in range(len(rovers) -1, -1, -1):
        rover = rovers[i]
        if rover["address"] == ip and rover["port"] == port:
            del rovers[i]


def addToList(ip, port, name):
    rovers.append({ "address": ip, "port": port, "name": name })


def discover():
    packet = "Q#IP=255.255.255.255;PORT=" + str(THIS_PORT)

    for broadcast in broadcasts:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        bs = bytes(packet, 'utf-8')
        s.sendto(bs, (broadcast, DISCOVERY_PORT))

    now = time.time()
    while time.time() - now < WAIT_TIMEOUT:
        data, addr = sckt.recvfrom(1024)

        try:
            p = str(data, 'utf-8')

            if p.startswith("A#"):
                kvs = p[2:].split(";")

                ip = None
                name = None
                port = None
                type = None

                for kv in kvs:
                    kvp = kv.split("=")
                    if len(kvp) == 2:
                        if kvp[0] == "IP":
                            ip = kvp[1]
                        elif kvp[0] == "PORT":
                            try:
                                port = int(kvp[1])
                            except:
                                pass
                        elif kvp[0] == "NAME":
                            name = kvp[1]
                        elif kvp[0] == "TYPE":
                            type = kvp[1]

                if name is None:
                    name = ip
                if (not port is None) and (not ip is None) and type == "ROVER":
                    removeFromList(ip, port)
                    addToList(ip, port, name)

            print("Got " + p + "  Rovers: " + str(rovers))
        except:
            pass


def discovery():
    while True:
        discover()
        time.sleep(15)


poplulateBroadcasts()

thread = threading.Thread(target=discovery, args=())
thread.daemon = True
thread.start()


def getHost():
    if len(rovers) == 0:
        return None
    print("Selected rover " + str(rovers[selectedRover]))
    return rovers[selectedRover]["address"]


def getPort():
    if len(rovers) == 0:
        return None
    return rovers[selectedRover]["port"]


def connect():
    if len(rovers) == 0:
        return None
    pyros.connect(rovers[selectedRover]["address"], rovers[selectedRover]["port"], waitToConnect=False)


def handleConnectKeys(key):
    global selectedRover

    if key == pygame.K_2 and len(rovers) > 0:
        selectedRover = 0
        connect()
    elif key == pygame.K_3 and len(rovers) > 1:
        selectedRover = 1
        connect()
    elif key == pygame.K_4 and len(rovers) > 2:
        selectedRover = 2
        connect()
    elif key == pygame.K_5 and len(rovers) > 3:
        selectedRover = 3
        connect()
    elif key == pygame.K_6 and len(rovers) > 4:
        selectedRover = 4
        connect()
    elif key == pygame.K_7 and len(rovers) > 5:
        selectedRover = 5
        connect()


def getSelectedRoverDetailsText():
    if len(rovers) == 0:
        return "No rovers discovered"

    name = str(selectedRover)
    if "name" in rovers[selectedRover]:
        name = rovers[selectedRover]["name"]

    return "(" + str(len(rovers)) + ") " + name + " @ " + str(rovers[selectedRover]["address"]) + ":" + str(rovers[selectedRover]["port"])
