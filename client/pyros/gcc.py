
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import pygame
import pyros

rovers = {
    "rover2": {
        "address": "172.24.1.184",
        "port": 1883
    },
    "rover3": {
        "address": "172.24.1.185",
        "port": 1883
    },
    "rover4": {
        "address": "172.24.1.186",
        "port": 1883
    },
    "rover2proxy": {
        "address": "172.24.1.1",
        "port": 1884
    },
    "rover3proxy": {
        "address": "172.24.1.1",
        "port": 1885
    },
    "rover4proxy": {
        "address": "172.24.1.1",
        "port": 1886
    },
}

selectedRover = "rover2"


def getHost():
    return rovers[selectedRover]["address"]


def getPort():
    return rovers[selectedRover]["port"]


def connect():
    pyros.connect(rovers[selectedRover]["address"], rovers[selectedRover]["port"], waitToConnect=False)


def handleConnectKeys(key):
    global selectedRover

    if key == pygame.K_2:
        selectedRover = "rover2"
        connect()
    elif key == pygame.K_3:
        selectedRover = "rover3"
        connect()
    elif key == pygame.K_4:
        selectedRover = "rover4"
        connect()
    elif key == pygame.K_5:
        selectedRover = "rover2proxy"
        connect()
    elif key == pygame.K_6:
        selectedRover = "rover3proxy"
        connect()
    elif key == pygame.K_7:
        selectedRover = "rover4proxy"
        connect()


def getSelectedRoverDetailsText():
    return selectedRover + " @ " + str(rovers[selectedRover]["address"]) + ":" + str(rovers[selectedRover]["port"])
