
#
# Copyright 2016-2018 Games Creators Club
#
# MIT License
#

import time
import traceback

import pyroslib

DEBUG_LEVEL_OFF = 0
DEBUG_LEVEL_INFO = 1
DEBUG_LEVEL_DEBUG = 2
DEBUG_LEVEL_ALL = 3
DEBUG_LEVEL = DEBUG_LEVEL_ALL


def doNothing():
    pass


lastProcessed = time.time()


def formatArgL(label, value, fieldSize):
    if len(label) > 0:
        return label + ":" + str(value).ljust(fieldSize)
    else:
        return str(value).ljust(fieldSize)


def formatArgR(label, value, fieldSize):
    if len(label) > 0:
        return label + ":" + str(value).rjust(fieldSize)
    else:
        return str(value).rjust(fieldSize)


def log(level, what):
    if level <= DEBUG_LEVEL:
        print(what)


def logArgs(*msg):
    tnow = time.time()

    logMsg = formatArgR("", int(tnow * 1000) % 100000, 7) + " " + " ".join(msg)
    log(DEBUG_LEVEL_DEBUG, logMsg)


def connected():
    # pyroslib.publish("sensor/gyro/continuous", "calibrate,50")
    pass


def handleAgentCommands(topic, message, groups):
    data = message.split(":")

    cmd = data[0]

    if cmd == "stop":
        stop()
    elif cmd == "start":
        start()


def stop():
    # pyroslib.publish("move", "0 0")
    # pyroslib.publish("move/stop", "")
    log(DEBUG_LEVEL_ALL, "Stopped driving...")
    pass


def start():
    log(DEBUG_LEVEL_ALL, "Started driving...")
    pass


def mainLoop():
    pass


if __name__ == "__main__":
    try:
        print("Starting template agent...")

        pyroslib.subscribe("templateAgent/command", handleAgentCommands)

        pyroslib.init("template-agent", unique=True, onConnected=connected)

        print("Started template agent.")

        pyroslib.forever(0.02, mainLoop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
