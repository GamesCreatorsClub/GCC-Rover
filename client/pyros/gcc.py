
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
doDiscovery = True
showRovers = False
selectedRover = 0
connectedRover = 0
selectedRoverMap = {}

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

THIS_PORT = 0xd15d
DISCOVERY_PORT = 0xd15c
BROADCAST_TIMEOUT = 5  # every 5 seconds
ROVER_TIMEOUT = 30  # 30 seconds no

sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sckt.settimeout(1)


def setupListenSocket():
    global THIS_PORT
    connected = 5

    while connected > 0:
        try:
            sckt.bind(('', THIS_PORT))
            connected = 0
        except:
            THIS_PORT = THIS_PORT + 1


setupListenSocket()


def getBroadcasts():
    broadcasts = []

    ifacenames = netifaces.interfaces()
    for ifname in ifacenames:
        addrs = netifaces.ifaddresses(ifname)

        for d in addrs:
            for dx in addrs[d]:
                if "broadcast" in dx:
                    broadcasts.append(dx["broadcast"])
    return broadcasts


def addToList(roverMap):
    roverMap["lastSeen"] = time.time()

    for rover in rovers:
        if rover["IP"] == roverMap["IP"] and rover["PORT"] == roverMap["PORT"]:
            for key in roverMap:
                if key == "PORT":
                    rover[key] = int(roverMap[key])
                else:
                    rover[key] = roverMap[key]
            return

    rovers.append(roverMap)
    print("Found new rover " + str(roverMap["NAME"]) + " @ " + str(roverMap["IP"]) + ":" + str(roverMap["PORT"]))


def discover():
    global doDiscovery
    packet = "Q#IP=255.255.255.255;PORT=" + str(THIS_PORT)

    lastBroadcastTime = time.time()

    while True:
        if doDiscovery or time.time() - lastBroadcastTime > BROADCAST_TIMEOUT:
            doDiscovery = False
            try:
                broadcasts = getBroadcasts()

                for broadcast in broadcasts:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    bs = bytes(packet, 'utf-8')
                    s.sendto(bs, (broadcast, DISCOVERY_PORT))
                lastBroadcastTime = time.time()

                for i in range(len(rovers) - 1, -1, -1):
                    rover = rovers[i]
                    if rover["lastSeen"] + ROVER_TIMEOUT < time.time():
                        print("Lost connection to rover " + str(rovers[i]["name"]) + " @ " + str(rovers[i]["ip"]) + ":" + str(rovers[i]["port"]))
                        del rovers[i]
            except:
                pass

        try:
            data, addr = sckt.recvfrom(1024)

            p = str(data, 'utf-8')

            if p.startswith("A#"):
                kvs = p[2:].split(";")

                ip = None
                name = None
                port = None
                deviceType = None

                roverMap = {}

                for keyValue in kvs:
                    kvp = keyValue.split("=")
                    if len(kvp) == 2:
                        roverMap[kvp[0]] = kvp[1]
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
                    addToList(roverMap)
                    receivedSomething = True

            # print("Got " + p + "  Rovers: " + str(rovers))
        except:
            pass
        #
        # addToList("127.0.0,1", 1883, "Local1")
        # addToList("127.0.0,2", 1883, "Local2")
        # addToList("127.0.0,3", 1883, "Local3")
        # addToList("127.0.0,4", 1883, "Local4")
        # addToList("127.0.0,5", 1883, "Local5")
        # addToList("127.0.0,6", 1883, "Local6")


if len(sys.argv) > 1:
    roverMap = {}

    kv = sys.argv[1].split(":")
    if len(kv) == 1:
        kv.append("1883")

    roverMap["IP"] = kv[0]
    roverMap["PORT"] = int(kv[1])
    roverMap["NAME"] = "Rover(args)"
    roverMap["TYPE"] = "ROVER"
    roverMap["JOY_PORT"] = "1880"

    addToList(roverMap)

else:
    thread = threading.Thread(target=discover, args=())
    thread.daemon = True
    thread.start()


def getHost():
    if len(rovers) == 0:
        return None
    print("Selected rover " + str(rovers[selectedRover]))
    return rovers[selectedRover]["IP"]


def getPort():
    if len(rovers) == 0:
        return None
    return int(rovers[selectedRover]["PORT"])


def connect():
    global selectedRover, connectedRover

    connectedRover = selectedRover

    if len(rovers) == 0:
        return None
    pyros.connect(rovers[selectedRover]["IP"], rovers[selectedRover]["PORT"], waitToConnect=False)


lmeta = False
rmeta = False
lshift = False
rshift = False


def handleConnectKeyDown(key):
    global selectedRover, doDiscovery, showRovers
    global lmeta, rmeta, lshift, rshift

    if key == pygame.K_LMETA:
        lmeta = True
    elif key == pygame.K_RMETA:
        rmeta = True
    elif key == pygame.K_LSHIFT:
        lshift = True
    elif key == pygame.K_RSHIFT:
        rshift = True
    elif lmeta and key == pygame.K_q:
        sys.exit(0)

    if key == pygame.K_1 and (lmeta or rmeta):
        doDiscovery = True
        showRovers = True
    elif key == pygame.K_TAB:
        if showRovers:
            if lshift or rshift:
                selectedRover -= 1
                if selectedRover < 0:
                    selectedRover = len(rovers) - 1
            else:
                selectedRover += 1
                if selectedRover >= len(rovers):
                    selectedRover = 0
        else:
            showRovers = True
    elif showRovers and key == pygame.K_UP and selectedRover > 0:
        selectedRover -= 1
    elif showRovers and key == pygame.K_DOWN and selectedRover < len(rovers) - 1:
        selectedRover += 1
    elif showRovers and key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
        connect()
        showRovers = False
    elif showRovers and key == pygame.K_ESCAPE:
        showRovers = False
    elif key == pygame.K_F5:
        connect()

    return showRovers


def handleConnectKeyUp(key):
    global lmeta, rmeta, lshift, rshift

    if key == pygame.K_LMETA:
        lmeta = False
    elif key == pygame.K_RMETA:
        rmeta = False
    elif key == pygame.K_LSHIFT:
        lshift = False
    elif key == pygame.K_RSHIFT:
        rshift = False

    return showRovers


def getSelectedRoverDetailsText(i):
    if selectedRover >= len(rovers):
        return "No rovers"

    name = "Unknown Rover"

    if "name" in rovers[i]:
        name = rovers[i]["name"]

    if name.startswith("gcc-rover-"):
        name = "GCC Rover " + name[10:]

    return name


def getSelectedRoverIP(i):
    if selectedRover >= len(rovers):
        return ""

    return str(rovers[i]["IP"]) + ":" + str(rovers[i]["PORT"])


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

    def drawRover(roverIndex, pos, colour):
        w = pyros.gccui.font.size(getSelectedRoverDetailsText(roverIndex))[0]
        pyros.gccui.screen.blit(pyros.gccui.font.render(getSelectedRoverDetailsText(roverIndex), 1, colour), pos)
        pyros.gccui.screen.blit(pyros.gccui.smallFont.render(getSelectedRoverIP(roverIndex), 1, colour), (pos[0] + 8 + w, pos[1] + 5))

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
        drawRover(connectedRover, (32, 0), pyros.gccui.GREEN)
    else:
        _connectionCounter -= 1
        if _connectionCounter < 0:
            _connectionCounter = 10
            _state -= 1
            if _state < 0:
                _state = 3

        _drawRedIndicator()
        drawRover(connectedRover, (32, 0), pyros.gccui.RED)

    if showRovers:
        pyros.gccui.drawFrame(pygame.Rect(0, 30, 250, 178), pyros.gccui.LIGHT_BLUE, pyros.gccui.BLACK)

        st = 0
        if selectedRover > 2:
            st = selectedRover - 2

        en = st + 5
        if en > len(rovers):
            en = len(rovers)

        while en - st < 5 and st > 0:
            st = st - 1

        for i in range(st, en):
            y = 30 + (i - st) * 30 + 12
            if i == selectedRover:
                pygame.draw.rect(pyros.gccui.screen, pyros.gccui.DARK_GREY, pygame.Rect(8, y, 234, 30), 0)

            drawRover(i, (12, y), pyros.gccui.LIGHT_BLUE)

        if st > 0:
            pyros.gccui.drawUpArrow(120, 38, 130, 42, pyros.gccui.LIGHT_BLUE)
        if en < len(rovers):
            pyros.gccui.drawDownArrow(120, 194, 130, 198, pyros.gccui.LIGHT_BLUE)
