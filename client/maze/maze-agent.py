
import sys
import math
import time
import traceback
import pyroslib

MAX_TIMEOUT = 5

MAX_ROTATE_DISTANCE = 500
INITIAL_SPEED = 15
INITIAL_TURNING_RADIUS = 180
INITIAL_GAIN = 4


gain = INITIAL_GAIN
speed = INITIAL_SPEED
turningRadius = INITIAL_TURNING_RADIUS

driveAngle = 0

run = True
received = True

distances = {}

corridorWidth = 0
idealDistance = 0

lastWallDistance = 0

lastPing = time.time()

continuousCounter = 0


def doNothing():
    pass

nextState = doNothing


def sanitise(distance):
    distance -= 100
    if distance < 2:
        distance = 2
    return distance


def parseDistances(p):
    distances.clear()
    for pair in p.split(","):
        split = pair.split(":")
        distances[float(split[0])] = sanitise(float(split[1]))


def handleMoveResponse(topic, message, groups):

    if message.startswith("done-turn"):
        print("** Turned!")

    if message.startswith("done-move"):
        print("** Moved!")
        pyroslib.publish("sensor/distance/scan", "scan")
        print("** Asked for distance scan")


def handleSensorDistance(topic, message, groups):
    global received, driveAngle

    # print("** distance = " + message)
    if "," in message:
        parseDistances(message)
    else:
        split = message.split(":")
        d = float(split[1])
        if d >= 0:
            distances[float(split[0])] = sanitise(d)

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

    corridorWidth = distances[-90.0] + distances[90.0]

    idealDistance = (corridorWidth / 2) * math.sqrt(2)

    print("Corridor is " + str(corridorWidth) + "mm wide. Ideal distance=" + str(idealDistance))
    pyroslib.publish("sensor/distance/read", str(-45))
    pyroslib.publish("sensor/distance/continuous", "start")


def goForward():
    global nextState, lastWallDistance

    distance = distances[-45.0]

    if abs(distance) > idealDistance * 1.25:
        print("FORWARD: Got distance " + str(distance) + ", waiting for end of the wall...")
        pyroslib.publish("move/steer", str(int(-MAX_ROTATE_DISTANCE * 3)) + " " + str(speed))
        nextState = waitForTurning
    else:
        lastWallDistance = distance
        delta = idealDistance - distance

        if delta >= 0:
            rotateDistance = MAX_ROTATE_DISTANCE - delta * gain
            if rotateDistance < 100:
                rotateDistance = 100
        else:
            rotateDistance = -MAX_ROTATE_DISTANCE - delta * gain
            if rotateDistance > -100:
                rotateDistance = -100

        print("FORWARD: Got distance " + str(distance) + " where delta is " + str(delta) + " steering at distance " + str(rotateDistance))

        pyroslib.publish("move/steer", str(int(rotateDistance)) + " " + str(speed))
    doContinuousRead()


def waitForTurning():
    global nextState

    distance = distances[-45.0]

    if abs(distance) > idealDistance * 0.75:
        print("WAIT: Got distance " + str(distance) + ", starting turning at steering distance " + str(-turningRadius))
        pyroslib.publish("move/steer", str(int(-turningRadius)) + " " + str(speed))

        nextState = turning
    else:
        print("WAIT: Got distance " + str(distance) + ", waiting...")

    doContinuousRead()


def turning():
    global nextState

    distance = distances[-45.0]

    if abs(distance) < idealDistance * 0.75:
        print("TURN: Got distance " + str(distance) + ", back to hugging the wall")

        nextState = goForward
    else:
        print("TURN: Got distance " + str(distance) + ", turning at distance " + str(-turningRadius))
        pyroslib.publish("move/steer", str(int(-turningRadius)) + " " + str(speed))

    doContinuousRead()


def doContinuousRead():
    global continuousCounter
    continuousCounter += 1
    if continuousCounter > 10:
        pyroslib.publish("sensor/distance/continuous", "start")
        continuousCounter = 0


def connected():
    stop()


def handleMazePing(topic, message, groups):
    global lastPing
    lastPing = time.time()


def handleMazeSpeed(topic, message, groups):
    global speed

    speed = int(message)
    print("  Got turning speed of " + speed)


def handleMazeGain(topic, message, groups):
    global gain

    gain = float(message)
    print("  Got turning gain of " + gain)


def handleMazeRadius(topic, message, groups):
    global turningRadius

    turningRadius = int(message)
    print("  Got turning radius of " + turningRadius)

def handleMazeCommand(topic, message, groups):
    if message == "start":
        start()
    elif message == "stop":
        stop()


def loop():
    now = time.time()

    if now - lastPing > MAX_TIMEOUT:
        print("** Didn't receive ping for more than " + str(now - lastPing) + "s. Leaving...");
        sys.exit(0)


if __name__ == "__main__":
    try:
        print("Starting maze agent...")

        pyroslib.subscribe("move/feedback", handleMoveResponse)
        pyroslib.subscribe("sensor/distance", handleSensorDistance)
        pyroslib.subscribe("maze/ping", handleMazePing)
        pyroslib.subscribe("maze/command", handleMazeCommand)
        pyroslib.subscribe("maze/speed", handleMazeSpeed)
        pyroslib.subscribe("maze/gain", handleMazeGain)
        pyroslib.subscribe("maze/radius", handleMazeRadius)

        pyroslib.init("maze-agent", unique=True)

        print("Started maze agent.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))


