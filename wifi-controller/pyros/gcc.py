
import pygame
import pyros

rovers = {
    "2": {
        "address": "172.24.1.184",
        "port": 1883
    },
    "3": {
        "address": "172.24.1.185",
        "port": 1883
    },
    "4": {
        "address": "172.24.1.186",
        "port": 1883
    }
}

selectedRover = "2"


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
