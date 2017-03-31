
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import sys
import math
import time
import traceback
import pyroslib

DEBUG = True

MAX_TIMEOUT = 5

MAX_WALL_END_WAIT_TIMEOUT = 2
MAX_ROTATE_DISTANCE = 500
MIN_ROTATE_DISTANCE = 0
MIN_DISTANCE = 100

SQRT2 = math.sqrt(2)

INITIAL_SPEED = 20
INITIAL_GAIN = 1.7


gain = INITIAL_GAIN
speed = INITIAL_SPEED

driveAngle = 0

run = True
received = True

distances = {}

corridorWidth = 0
idealDistance = 0

lastWallDistance = 0

lastPing = time.time()

continuousCounter = 0
wallEndWaitTimeout = 0


def doNothing():
    pass

nextState = doNothing


def sanitise(distance):
    # distance -= 100
    if distance < 2:
        distance = 2
    return distance


def toFloatString(f):
    r = str(round(f, 1))
    if "." not in r:
        return r + ".0"
    return r


def parseDistances(p):
    distances.clear()
    for pair in p.split(","):
        split = pair.split(":")
        distances[toFloatString(float(split[0]))] = sanitise(float(split[1]))


def handleSensorDistance(topic, message, groups):
    global received, driveAngle

    # print("** distance = " + message)
    if "," in message:
        parseDistances(message)
    else:
        split = message.split(":")
        d = float(split[1])
        if d >= 0:
            distances[toFloatString(float(split[0]))] = sanitise(d)

    received = True
    if nextState is not None:
        nextState()


def stop():
    global run, nextState
    print("Stoping...")
    nextState = doNothing
    run = False
    pyroslib.publish("move/stop", "stop")
    print("Stopped.")


def start():
    global run, nextState
    print("Starting...")
    run = True
    nextState = preStartInitiateRightScan
    preStartInitiateLeftScan()


def preStartInitiateLeftScan():
    global nextState
    nextState = preStartInitiateRightScan
    pyroslib.publish("sensor/distance/read", str(90))


def preStartInitiateRightScan():
    global nextState
    nextState = preStartWarmUp
    pyroslib.publish("sensor/distance/read", str(-90))


def preStartWarmUp():
    global corridorWidth, idealDistance, nextState

    nextState = goForward

    corridorWidth = distances["-90.0"] + distances["90.0"]

    idealDistance = (corridorWidth / 2) * SQRT2

    if DEBUG:
        print("Corridor is " + str(corridorWidth) + "mm wide. Ideal distance=" + str(idealDistance))

    pyroslib.publish("maze/data/corridor", str(corridorWidth))
    pyroslib.publish("maze/data/idealDistance", str(idealDistance))

    pyroslib.publish("sensor/distance/read", str(-45))
    pyroslib.publish("sensor/distance/continuous", "start")


def goForward():
    global nextState, lastWallDistance, wallEndWaitTimeout

    if "-45.0" in distances:
        distance = distances["-45.0"]

        if abs(distance) > idealDistance * 1.75:
            if DEBUG:
                print("FORWARD: Got distance " + str(distance) + ", waiting for end of the wall...")
            del distances["-90.0"]
            pyroslib.publish("sensor/distance/deg", "-90")
            pyroslib.publish("move/steer", str(int(-MAX_ROTATE_DISTANCE * 2)) + " " + str(speed))  # go straight

            wallEndWaitTimeout = 0
            nextState = waitForTurning
        else:
            lastWallDistance = distance

            realDistance = distance

            if distance < idealDistance:
                difference = distance / idealDistance

                difference *= difference
                difference *= gain
                if difference > 1:
                    difference = 1

                rotateDistance = MIN_ROTATE_DISTANCE + (MAX_ROTATE_DISTANCE - MIN_ROTATE_DISTANCE) * difference
                if DEBUG:
                    print("FORWARD: Move away from the wall at distance " + str(realDistance) + " where difference is " + str(round(difference, 1)) + " steering at distance " + str(round(rotateDistance, 1)))
            else:
                distance -= idealDistance
                difference = distance / idealDistance

                difference = 1 - difference

                difference *= difference
                difference *= gain
                if difference > 1:
                    difference = 1

                rotateDistance = MIN_ROTATE_DISTANCE + (MAX_ROTATE_DISTANCE - MIN_ROTATE_DISTANCE) * difference

                rotateDistance = -rotateDistance
                if DEBUG:
                    print("FORWARD: Move to the wall at distance " + str(realDistance) + " where difference is " + str(round(difference, 1)) + " steering at distance " + str(round(rotateDistance, 1)))

            pyroslib.publish("move/steer", str(int(rotateDistance)) + " " + str(speed))
    else:
        if DEBUG:
            print("FORWARD: waiting to get reading...")

    doContinuousRead()


def waitForTurning():
    global nextState, lastWallDistance, wallEndWaitTimeout

    if "-90.0" in distances:
        distance = distances["-90.0"]

        if abs(distance) >= idealDistance * 1.25:
            turnDistance = lastWallDistance

            if DEBUG:
                print("WAIT: Got distance " + str(distance) + ", starting turning at steering distance " + str(-round(turnDistance, 2)))
            del distances["-45.0"]
            pyroslib.publish("sensor/distance/deg", "-45")
            pyroslib.publish("move/steer", str(int(-turnDistance)) + " " + str(speed))

            nextState = turning
        elif distance < MIN_DISTANCE or wallEndWaitTimeout >= MAX_WALL_END_WAIT_TIMEOUT:
            nextState = goForward
            if "90.0" in distances:
                del distances["90.0"]

            delta = idealDistance - distance
            rotateDistance = MAX_ROTATE_DISTANCE - delta * gain
            if rotateDistance < 100:
                rotateDistance = 100
            pyroslib.publish("sensor/distance/deg", "-45")
            pyroslib.publish("move/steer", str(int(rotateDistance)) + " " + str(speed))
            if DEBUG:
                if wallEndWaitTimeout >= MAX_WALL_END_WAIT_TIMEOUT:
                    print("WAIT: Wall end timeot at distance " + str(distance) + " where delta is " + str(round(delta, 1)) + " steering at distance " + str(round(rotateDistance, 1)))
                else:
                    print("WAIT: Too close to wall " + str(distance) + " where delta is " + str(round(delta, 1)) + " steering at distance " + str(round(rotateDistance, 1)))
        else:
            lastWallDistance = distance
            if DEBUG:
                print("WAIT: Got distance " + str(distance) + ", waiting...")
    else:
        if DEBUG:
            print("WAIT: waiting to get reading...")

    wallEndWaitTimeout += 1

    doContinuousRead()


def turning():
    global nextState

    if "-45.0" in distances:
        distance = distances["-45.0"]

        if abs(distance) < idealDistance * 0.75:
            if DEBUG:
                print("TURN: Got distance " + str(distance) + ", back to hugging the wall")

            nextState = goForward
        else:
            turnDistance = lastWallDistance
            if turnDistance < corridorWidth / 2:
                turnDistance = corridorWidth / 2
            turnDistance = corridorWidth / 2

            if DEBUG:
                print("TURN: Got distance " + str(distance) + ", turning at distance " + str(-turnDistance))
            pyroslib.publish("move/steer", str(int(-turnDistance)) + " " + str(speed))
    else:
        if DEBUG:
            print("TURN: waiting to get reading...")

    doContinuousRead()


def doContinuousRead():
    global continuousCounter
    continuousCounter += 1
    if continuousCounter > 10:
        pyroslib.publish("sensor/distance/continuous", "start")
        continuousCounter = 0


def connected():
    stop()


def handlePing(topic, message, groups):
    global lastPing
    lastPing = time.time()


def handleMazeSpeed(topic, message, groups):
    global speed

    speed = int(message)
    if DEBUG:
        print("  Got turning speed of " + str(speed))


def handleMazeGain(topic, message, groups):
    global gain

    gain = float(message)
    if DEBUG:
        print("  Got turning gain of " + str(gain))


def handleMazeCommand(topic, message, groups):
    if message == "start":
        start()
    elif message == "stop":
        stop()


def loop():
    now = time.time()

    if now - lastPing > MAX_TIMEOUT:
        print("** Didn't receive ping for more than " + str(now - lastPing) + "s. Leaving...")
        sys.exit(0)


if __name__ == "__main__":
    try:
        print("Starting maze agent...")

        pyroslib.subscribe("sensor/distance", handleSensorDistance)
        pyroslib.subscribe("maze/ping", handlePing)
        pyroslib.subscribe("maze/command", handleMazeCommand)
        pyroslib.subscribe("maze/speed", handleMazeSpeed)
        pyroslib.subscribe("maze/gain", handleMazeGain)

        pyroslib.init("maze-agent", unique=True)

        print("Started maze agent.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))

