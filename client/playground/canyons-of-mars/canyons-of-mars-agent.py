
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


lastOdo = [5, 6, 7, 8]
odo = [0, 0, 0, 0]
requiredOdo = [5, 6, 7, 8]

timeToSendData = 0
running = False


def doNothing():
    pass


lastProcessed = time.time()


def deltaDeg(old, new):
    d = new - old
    if d > 32768:
        d -= 32768
    elif d < -32768:
        d += 32768

    # 100, 102 -> 2
    # 102, 100 -> -2

    # 359, 1 -> -358 -> 2
    # 1, 359 -> 358 -> -2

    return d


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


def handleOdo(topic, message, groups):
    data = message.split(",")

    deltas = [0, 0, 0, 0]
    for i in range(4):
        d = i * 2
        if data[d + 2] == "0":
            newOdo = int(data[d + 1])
            d = deltaDeg(lastOdo[i], newOdo)
            if i == 2:
                d = -d

            deltas[i] = d
            odo[i] += d
            lastOdo[i] = newOdo
    print(str(odo) + ", " + str(deltas) + ", " + str(lastOdo))


def handleAgentCommands(topic, message, groups):
    data = message.split(" ")

    print("Command " + message)

    cmd = data[0]

    if cmd == "stop":
        stop()
    elif cmd == "start":
        start(data[1])


def stop():
    global running

    pyroslib.publish("move/stop", "")

    running = False

    log(DEBUG_LEVEL_ALL, "Stopped driving...")


def start(distanceStr):
    global running

    distance = int((int(distanceStr) / 360) * 4096)
    for i in range(4):
        odo[i] = 0
        requiredOdo[i] = distance

    running = True

    pyroslib.publish("move/drive", "0 100")

    log(DEBUG_LEVEL_ALL, "Started driving... for  " + distanceStr + " (" + str(requiredOdo) + ")")


def mainLoop():
    global timeToSendData

    def sendData():
        pyroslib.publish("canyons/odo", ",".join([str(x) for x in odo]))

    now = time.time()

    if timeToSendData <= now:
        sendData()
        timeToSendData = now + 0.2

    if running:
        stopped = False
        for i in range(4):
            if odo[i] >= requiredOdo[i]:
                stop()
                stopped = True
        if not stopped:
            print(str(odo) + " <-> " + str(requiredOdo))


if __name__ == "__main__":
    try:
        print("Starting canyons-of-mars agent...")

        pyroslib.subscribe("canyons/command", handleAgentCommands)
        pyroslib.subscribe("wheel/speed/status", handleOdo)

        pyroslib.init("canyons-of-mars-agent", unique=True, onConnected=connected)

        print("Started canyons-of-mars agent.")

        pyroslib.forever(0.02, mainLoop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
