
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

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
turned = False
justScanWidth = False

leftDistance = 0
rightDistance = 0
corridorWidth = 0
idealDistance = 0

lastWallDistance = 0

scanTime = 0
SCAN_TIME = 1.2

continuousCounter = 0
wallEndWaitTimeout = 0

DISTANCE_AVG_TIME = 0.5

distances = {}

distanceTimestamp = 0
distanceDeg1 = -1
distanceDeg2 = -1
distance1 = -1
distance2 = -1
avgDistance1 = -1
avgDistance2 = -1
deltaDistance1 = -1
deltaDistance2 = -1

historyDistancesDeg1 = -1
historyDistancesDeg2 = -1
historyDistances1 = []
historyDistanceTimes1 = []
historyDistances2 = []
historyDistanceTimes2 = []

lastDistanceReceivedTime = 0

gyroAngle = 0
gyroDeltaAngle = 0
gyroStartAngle = 0
gyroIntegral = 0
EPSILON_ANGLE = 2

renewContinuous = time.time()
digestTime = time.time()
readingDistanceContinuous = True
readingGyroContinuous = True


def doNothing():
    pass


doDistance = doNothing
doGyro = doNothing
algorithm = doNothing
algorithmIndex = 0
algorithmsList = []


def setAlgorithm(alg):
    global algorithm
    algorithm = alg


def setAlgorithms(*algs):
    global algorithmIndex, algorithmsList

    algorithmIndex = 0
    algorithmsList[:] = []
    for a in algs:
        algorithmsList.append(a)
    setAlgorithm(algorithmsList[0])


def handleDistances(topic, message, groups):
    global historyDistancesDeg1, historyDistancesDeg2, historyDistances1, historyDistances2, historyDistanceTimes1, historyDistanceTimes2
    global distanceDeg1, distanceDeg2, distance1, distance2, avgDistance1, avgDistance2, distanceTimestamp, deltaDistance1, deltaDistance2
    global deltaTime, lastDistanceReceivedTime
    global received

    def addToHistoryWithTime(value, valueTime, history, historyTimes, maxTime):
        history.append(value)
        historyTimes.append(valueTime)

        while len(historyTimes) > 0 and historyTimes[0] < valueTime - maxTime:
            del history[0]
            del historyTimes[0]

        if len(history) > 1:
            return value - history[len(history) - 2], sum(history) / len(history)
        else:
            return 0, 0

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

    receivedTime = time.time()

    split = message.split(",")
    deg1 = -1
    val1 = -1
    deg2 = -1
    val2 = -1

    i = 0
    for s in split:
        kv = s.split(":")
        if kv[0] == "timestamp":
            distanceTimestamp = float(kv[1])
        else:
            distances[toFloatString(float(kv[0]))] = sanitise(float(kv[1]))

            deg = int(float(kv[0]))
            val = int(float(kv[1]))

            if i == 0:
                deg1 = deg
                val1 = val
            elif i == 1:
                deg2 = deg
                val2 = val

            i += 1

    distanceDeg1 = deg1
    distance1 = val1
    distanceDeg2 = deg2
    distance2 = val2

    if deg1 > deg2:
        tmp = deg2
        deg2 = deg1
        deg1 = tmp

        tmp = distanceDeg2
        distanceDeg2 = distanceDeg1
        distanceDeg1 = tmp

    if historyDistancesDeg1 != deg1 or historyDistancesDeg2 != deg2:
        historyDistances1 = []
        historyDistanceTimes1 = []
        historyDistancesDeg1 = deg1

        historyDistances2 = []
        historyDistanceTimes2 = []
        historyDistancesDeg2 = deg2

    deltaDistance1, avgDistance1 = addToHistoryWithTime(distance1, receivedTime, historyDistances1, historyDistanceTimes1, DISTANCE_AVG_TIME)
    deltaDistance2, avgDistance2 = addToHistoryWithTime(distance2, receivedTime, historyDistances2, historyDistanceTimes2, DISTANCE_AVG_TIME)

    deltaTime = receivedTime - lastDistanceReceivedTime
    lastDistanceReceivedTime = receivedTime

    received = True
    # if nextState is not None:
    #     nextState()

    doDistance()


def handleGyroData(topic, message, groups):
    global gyroAngle, gyroDeltaAngle, gyroDeltaTime, lastGyroReceivedTime

    data = message.split(",")

    gyroChange = float(data[2])

    gyroDeltaAngle = gyroChange

    gyroAngle += gyroChange

    gyroDeltaTime = float(data[3])

    lastGyroReceivedTime = time.time()

    doGyro()


def stop():
    global run, doDistance, doGyro
    doDistance = doNothing
    doGyro = doNothing

    print("Stoping...")
    setAlgorithm(doNothing)
    run = False
    pyroslib.publish("move/stop", "stop")
    print("Stopped.")


def start():
    global run, turned, justScanWidth
    print("Starting...")
    run = True
    turned = False
    justScanWidth = False

    preStartInitiateLeftScan()


def quickstart():
    global run, turned, justScanWidth, scanTime
    print("Quick Starting...")
    run = True
    turned = False
    justScanWidth = False

    scanTime = time.time() + SCAN_TIME
    pyroslib.publish("sensor/distance/read", str(45))
    setAlgorithm(preStart)


def scanWidth():
    global run, turned, justScanWidth
    print("Scanning width...")
    run = True
    turned = False
    justScanWidth = True

    preStartInitiateLeftScan()


def preStartInitiateLeftScan():
    global scanTime
    scanTime = time.time() + SCAN_TIME
    setAlgorithm(preStartLeftScan)
    pyroslib.publish("sensor/distance/read", str(0))


def preStartLeftScan():
    global leftDistance
    if time.time() > scanTime:
        leftDistance = avgDistance2
        if DEBUG:
            print("LeftDistance = " + str(leftDistance))
        preStartInitiateRightScan()


def preStartInitiateRightScan():
    global scanTime
    scanTime = time.time() + SCAN_TIME
    setAlgorithm(preStartRightScan)
    pyroslib.publish("sensor/distance/read", str(90))


def preStartRightScan():
    global rightDistance
    if time.time() > scanTime:
        rightDistance = avgDistance1
        if DEBUG:
            print("RightDistance = " + str(rightDistance))
        preStartWarmUp()


def preStartWarmUp():
    global corridorWidth, idealDistance, scanTime

    scanTime = time.time() + SCAN_TIME

    if justScanWidth:
        pyroslib.publish("sensor/distance/read", str(0))
        setAlgorithm(doNothing)
    else:
        pyroslib.publish("sensor/distance/read", str(45))
        setAlgorithm(preStart)

    corridorWidth = leftDistance + rightDistance

    idealDistance = (corridorWidth / 2) * SQRT2

    if DEBUG:
        print("Corridor is " + str(corridorWidth) + "mm wide. Ideal distance=" + str(idealDistance))

    pyroslib.publish("maze/data/corridor", str(corridorWidth))
    pyroslib.publish("maze/data/idealDistance", str(idealDistance))

    pyroslib.publish("sensor/distance/continuous", "start")


def preStartWarmUp():
    global corridorWidth, idealDistance, scanTime

    scanTime = time.time() + SCAN_TIME

    if justScanWidth:
        pyroslib.publish("sensor/distance/read", str(0))
        setAlgorithm(doNothing)
    else:
        pyroslib.publish("sensor/distance/read", str(45))
        setAlgorithm(preStart)

    corridorWidth = leftDistance + rightDistance
    idealDistance = (corridorWidth / 2) * SQRT2

    if DEBUG:
        print("Corridor is " + str(corridorWidth) + "mm wide. Ideal distance=" + str(idealDistance))

    pyroslib.publish("maze/data/corridor", str(corridorWidth))
    pyroslib.publish("maze/data/idealDistance", str(idealDistance))

    # pyroslib.publish("sensor/distance/continuous", "start")


def preStart():
    if time.time() > scanTime:
        setAlgorithm(goForward)


def goForward():
    global doDistance
    doDistance = goForwardDistanceHandler


def goForwardDistanceHandler():
    global lastWallDistance, wallEndWaitTimeout, distances

    # if "-45.0" in distances:
    # distance = distances["-45.0"]
    if turned:
        distance = distance1
    else:
        distance = distance2

    if abs(distance) > idealDistance * 1.75:
        if DEBUG:
            print("FORWARD: Got distance " + str(distance) + ", waiting for end of the wall...")
        if "-90.0" in distances:
            del distances["-90.0"]
        pyroslib.publish("sensor/distance/deg", "0")
        pyroslib.publish("move/steer", str(int(-MAX_ROTATE_DISTANCE * 2)) + " " + str(speed))  # go straight

        wallEndWaitTimeout = 0
        setAlgorithm(waitForTurning)
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


def waitForTurning():
    global doDistance
    doDistance = waitForTurningDistanceHandler


def waitForTurningDistanceHandler():
    global lastWallDistance, wallEndWaitTimeout, distances

    # if "-90.0" in distances:
    # distance = distances["-90.0"]
    distance = distance2

    if abs(distance) >= idealDistance * 1.25:
        turnDistance = lastWallDistance

        if DEBUG:
            print("WAIT: Got distance " + str(distance) + ", starting turning at steering distance " + str(-round(turnDistance, 2)))
        if "-45.0" in distances:
            del distances["-45.0"]
        pyroslib.publish("sensor/distance/deg", "45")
        pyroslib.publish("move/steer", str(int(-turnDistance)) + " " + str(speed))

        setAlgorithm(turning)
    elif distance < MIN_DISTANCE or wallEndWaitTimeout >= MAX_WALL_END_WAIT_TIMEOUT:
        setAlgorithm(goForward)
        if "90.0" in distances:
            del distances["90.0"]

        delta = idealDistance - distance
        rotateDistance = MAX_ROTATE_DISTANCE - delta * gain
        if rotateDistance < 100:
            rotateDistance = 100
        pyroslib.publish("sensor/distance/deg", "45")
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

    wallEndWaitTimeout += 1


def turning():
    global doDistance
    doDistance = turningDistanceHandler


def turningDistanceHandler():
    global turned
    distance = distance2
    # distance = distances["-45.0"]

    if abs(distance) < idealDistance * 0.75:
        if DEBUG:
            print("TURN: Got distance " + str(distance) + ", back to hugging the wall")

        turned = True
        setAlgorithm(goForward)
    else:
        turnDistance = lastWallDistance
        if turnDistance < corridorWidth / 2:
            turnDistance = corridorWidth / 2
        turnDistance = corridorWidth / 2

        if DEBUG:
            print("TURN: Got distance " + str(distance) + ", turning at distance " + str(-turnDistance))
        pyroslib.publish("move/steer", str(int(-turnDistance)) + " " + str(speed))


def connected():
    stop()


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
    elif message == "quickstart":
        quickstart()
    elif message == "stop":
        stop()
    elif message == "scan":
        scanWidth()


def loop():
    global renewContinuous, digestTime

    thisTime = time.time()

    if thisTime > renewContinuous:
        renewContinuous = time.time() + 1
        if readingDistanceContinuous:
            pyroslib.publish("sensor/distance/continuous", "continue")
        if readingGyroContinuous:
            pyroslib.publish("sensor/gyro/continuous", "continue")

    if algorithm is not None:
        algorithm()

    if thisTime > digestTime:
        pyroslib.publish("maze/data/distances", str(distanceDeg1) + ":" + str(distance1) + ";" + str(avgDistance1) + "," + str(distanceDeg2) + ":" + str(distance2) + ";" + str(avgDistance2))
        pyroslib.publish("maze/data/gyro", str(gyroAngle))
        digestTime = thisTime + 0.1


if __name__ == "__main__":
    try:
        print("Starting maze agent...")

        pyroslib.subscribe("sensor/distance", handleDistances)
        pyroslib.subscribe("sensor/gyro", handleGyroData)

        pyroslib.subscribe("maze/command", handleMazeCommand)
        pyroslib.subscribe("maze/speed", handleMazeSpeed)
        pyroslib.subscribe("maze/gain", handleMazeGain)

        pyroslib.init("maze-agent", unique=True)

        print("Started maze agent.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
