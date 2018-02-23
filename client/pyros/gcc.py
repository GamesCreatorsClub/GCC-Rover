
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import pygame
import pyros
import pyros.gccui
import threading
import time
import socket
import netifaces
import sys

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
WAIT_TIMEOUT = 20  # 5 seconds

sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sckt.settimeout(5)

connected = 5

while connected > 0:
    try:
        sckt.bind(('', THIS_PORT))
        connected = 0
    except:
        THIS_PORT = THIS_PORT + 1


broadcasts = []
doDiscovery = True


def poplulateBroadcasts():
    global broadcasts
    broadcasts = []

    ifacenames = netifaces.interfaces()
    for ifname in ifacenames:
        addrs = netifaces.ifaddresses(ifname)

        for d in addrs:
            for dx in addrs[d]:
                if "broadcast" in dx:
                    broadcasts.append(dx["broadcast"])


def removeFromList(ip, port):
    for i in range(len(rovers) - 1, -1, -1):
        rover = rovers[i]
        if rover["address"] == ip and rover["port"] == port:
            del rovers[i]


def addToList(ip, port, name):
    rovers.append({"address": ip, "port": port, "name": name})


def discover():
    packet = "Q#IP=255.255.255.255;PORT=" + str(THIS_PORT)

    receivedSomething = False

    now = time.time()
    while not receivedSomething and time.time() - now < WAIT_TIMEOUT:
        for broadcast in broadcasts:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            bs = bytes(packet, 'utf-8')
            s.sendto(bs, (broadcast, DISCOVERY_PORT))


        try:
            data, addr = sckt.recvfrom(1024)

            p = str(data, 'utf-8')

            if p.startswith("A#"):
                kvs = p[2:].split(";")

                ip = None
                name = None
                port = None
                deviceType = None

                for keyValue in kvs:
                    kvp = keyValue.split("=")
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
                            deviceType = kvp[1]

                if name is None:
                    name = ip
                if (port is not None) and (ip is not None) and deviceType == "ROVER":
                    removeFromList(ip, port)
                    addToList(ip, port, name)
                    receivedSomething = True

            print("Got " + p + "  Rovers: " + str(rovers))
        except:
            pass


def discovery():
    global doDiscovery

    counter = 1
    while True:
        if len(rovers) == 0 or doDiscovery:
            try:
                print("Getting interfaces to send UDP packets to.")
                poplulateBroadcasts()
                print("Starting discovery")
                discover()
                counter = 10
                doDiscovery = False
            except:
                pass

        time.sleep(1)


if len(sys.argv) > 1:
    kv = sys.argv[1].split(":")
    if len(kv) == 1:
        kv.append("1883")
    addToList(kv[0], int(kv[1]), "Rover")

else:
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
    global selectedRover, doDiscovery

    if key == pygame.K_1 and len(rovers) > 0:
        doDiscovery = True
    elif key == pygame.K_2 and len(rovers) > 0:
        # doDiscovery = True
        selectedRover = 0
        connect()
    elif key == pygame.K_3 and len(rovers) > 1:
        # doDiscovery = True
        selectedRover = 1
        connect()
    elif key == pygame.K_4 and len(rovers) > 2:
        # doDiscovery = True
        selectedRover = 2
        connect()
    elif key == pygame.K_5 and len(rovers) > 3:
        # doDiscovery = True
        selectedRover = 3
        connect()
    elif key == pygame.K_6 and len(rovers) > 4:
        # doDiscovery = True
        selectedRover = 4
        connect()
    elif key == pygame.K_7 and len(rovers) > 5:
        # doDiscovery = True
        selectedRover = 5
        connect()


def getSelectedRoverDetailsText():
    if len(rovers) == 0:
        return "No rovers discovered"

    name = str(selectedRover)
    if "name" in rovers[selectedRover]:
        name = rovers[selectedRover]["name"]

    return "(" + str(len(rovers)) + ") " + name + " @ " + str(rovers[selectedRover]["address"]) + ":" + str(rovers[selectedRover]["port"])


_connectionCounter = 1
_state = 1


def _drawRedIndicator():
    if _state == 1:
        pyros.gccui.drawRect((9, 10), (16, 16), (96, 0, 0, 128), 2, 0)
        pyros.gccui.drawRect((11, 12), (11, 11), (160, 0, 0, 64), 2, 0)
        pyros.gccui.drawFilledRect((13, 14), (8, 8), (255, 0, 0, 64))
    if _state == 0:
        pyros.gccui.drawFilledRect((9, 10), (16, 16), (160, 0, 0, 128))
        pyros.gccui.drawRect((11, 12), (11, 11), (180, 0, 0, 64), 2, 0)
        pyros.gccui.drawFilledRect((13, 14), (8, 8), (255, 0, 0, 64))


def _drawGreenIndicator():
    if _state == 0 or _state == 1:
        pyros.gccui.drawFilledRect((9, 10), (16, 16), (0, 128, 0, 128))
        pyros.gccui.drawRect((11, 12), (11, 11), (0, 180, 0, 64), 2, 0)
        pyros.gccui.drawFilledRect((13, 14), (8, 8), (0, 255, 0, 64))
    if _state == 2:
        pyros.gccui.drawFilledRect((11, 10), (16, 16), (0, 96, 0, 128))
        pyros.gccui.drawRect((9, 12), (15, 11), (0, 160, 0, 64), 2, 0)
        pyros.gccui.drawFilledRect((11, 14), (12, 8), (0, 220, 0, 64))


def drawConnection():
    global _connectionCounter, _state
    if pyros.isConnected():
        _connectionCounter -= 1
        if _connectionCounter < 0:
            if _state == 0:
                _state = 2
                _connectionCounter = 10
            elif _state == 1:
                _state = 0
                _connectionCounter = 10
            elif _state == 2:
                _state = 1
                _connectionCounter = 10

        _drawGreenIndicator()

        pyros.gccui.screen.blit(pyros.gccui.bigFont.render("Connected to rover: " + getSelectedRoverDetailsText(), 1, pyros.gccui.GREEN), (32, 0))
    else:
        _connectionCounter -= 1
        if _connectionCounter < 0:
            _connectionCounter = 10
            _state -= 1
            if _state < 0:
                _state = 3

        _drawRedIndicator()

        pyros.gccui.screen.blit(pyros.gccui.bigFont.render("Connecting to rover: " + getSelectedRoverDetailsText(), 1, pyros.gccui.RED), (32, 0))
