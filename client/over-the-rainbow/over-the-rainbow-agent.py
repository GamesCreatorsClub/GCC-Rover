
#
# Copyright 2016-2018 Games Creators Club
#
# MIT License
#

import time
import threading
import traceback

import pyroslib
from RPi import GPIO

DEBUG = True
STROBO_LIGHT_GPIO = 4

stroboTime = -1
nextTime = time.time()
state = False


FORWARD_SPEED = 25
TURN_SPEED = 50
ROTATE_SPEED = 50

DISTANCE_AVG_TIME = 0.5

distanceDeg1 = -1
distanceDeg2 = -1
distance1 = -1
distance2 = -1
avgDistance1 = -1
avgDistance2 = -1

historyDistancesDeg1 = -1
historyDistancesDeg2 = -1
historyDistances1 = []
historyDistanceTimes1 = []
historyDistances2 = []
historyDistanceTimes2 = []

gyroAngle = 0

readingDistanceContinuous = True
readingGyroContinuous = True
renewContinuous = time.time()
digestTime = time.time()

algorithm = None


def setAlgorithm(alg):
    global algorithm
    algorithm = alg


def connected():
    pyroslib.publish("sensor/gyro/continuous", "calibrate,50")


def handleDistances(topic, message, groups):
    global historyDistancesDeg1, historyDistancesDeg2, historyDistances1, historyDistances2, historyDistanceTimes1, historyDistanceTimes2
    global distanceDeg1, distanceDeg2, distance1, distance2, avgDistance1, avgDistance2

    n = time.time()

    split = message.split(",")
    deg1 = -1
    val1 = -1
    deg2 = -1
    val2 = -1

    i = 0
    for s in split:
        kv = s.split(":")
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

    if historyDistancesDeg1 == deg1:
        if deg1 != -1:
            historyDistances1.append(val1)
            historyDistanceTimes1.append(n)
    elif historyDistancesDeg1 == deg2:
        if deg2 != -1:
            historyDistances1.append(val2)
            historyDistanceTimes1.append(n)
    else:
        historyDistances1 = []
        historyDistanceTimes1 = []
        historyDistancesDeg1 = deg1

    if historyDistancesDeg2 == deg1:
        if deg1 != -1:
            historyDistances2.append(val1)
            historyDistanceTimes2.append(n)
    elif historyDistancesDeg2 == deg2:
        if deg2 != -1:
            historyDistances2.append(val2)
            historyDistanceTimes2.append(n)
    else:
        historyDistances2 = []
        historyDistanceTimes2 = []
        historyDistancesDeg2 = deg2

    while len(historyDistanceTimes1) > 0 and historyDistanceTimes1[0] < n - DISTANCE_AVG_TIME:
        del historyDistances1[0]
        del historyDistanceTimes1[0]

    while len(historyDistanceTimes2) > 0 and historyDistanceTimes2[0] < n - DISTANCE_AVG_TIME:
        del historyDistances2[0]
        del historyDistanceTimes2[0]

    if len(historyDistances1) > 0:
        avgDistance1 = sum(historyDistances1) / len(historyDistances1)
    else:
        avgDistance1 = -1

    if len(historyDistances2) > 0:
        avgDistance2 = sum(historyDistances2) / len(historyDistances2)
    else:
        avgDistance2 = -1


def handleGyroData(topic, message, groups):
    global gyroAngle

    data = message.split(",")

    gyroChange = float(data[2])

    gyroAngle += gyroChange


def handleOverTheRainbow(topic, message, groups):
    global algorithm

    data = message.split(":")

    cmd = data[0]

    if cmd == "stop":
        setAlgorithm(stop)
    elif cmd == "alg1":
        setAlgorithm(algorithm1Start)
    elif cmd == "alg2":
        setAlgorithm(algorithm2Start)
    elif cmd == "alg3":
        setAlgorithm(algorithm3Start)
    elif cmd == "alg4":
        setAlgorithm(algorithm4Start)
    elif cmd == "alg5":
        setAlgorithm(algorithm5Start)
    elif cmd == "alg6":
        setAlgorithm(algorithm6Start)
    elif cmd == "alg7":
        setAlgorithm(algorithm7Start)
    elif cmd == "alg8":
        setAlgorithm(algorithm8Start)
    elif cmd == "alg9":
        setAlgorithm(algorithm9Start)
    elif cmd == "alg10":
        setAlgorithm(algorithm10Start)


def drive(angle=0):
    pyroslib.publish("move/drive", str(angle) + " " + str(FORWARD_SPEED))


def driveForward():
    pyroslib.publish("move/drive", "0 " + str(FORWARD_SPEED))


def driveBack():
    pyroslib.publish("move/drive", "0 " + str(-FORWARD_SPEED))


def rotateLeft():
    pyroslib.publish("move/rotate", str(-ROTATE_SPEED))


def rotateRight():
    pyroslib.publish("move/rotate", str(ROTATE_SPEED))


def stopDriving():
    pyroslib.publish("move", "0 0")
    pyroslib.publish("move/stop", "")


def doNothing():
    pass


def stop():
    stopDriving()
    print("Stopping all...")
    setAlgorithm(doNothing)
    print("Stopped!")


def algorithm1Start():
    print("started algorithm 1...")
    setAlgorithm(algorithm1Loop)


lastDrive = ""

def algorithm1Loop():
    global lastDrive
    # go to the corner
    stopAt = 120
    if avgDistance1 < stopAt and avgDistance2 < stopAt:
        stopDriving()
        setAlgorithm(stop)
        return
    elif abs(distance1 - distance2) > 30:
        if lastDrive != "30" and distance1 > distance2:
            drive(30)
            lastDrive = "30"
        elif lastDrive != "-30" and distance2 > distance1:
            drive(-30)
            drive(30)
            lastDrive = "-30"
    else:
        if lastDrive != "0":
            driveForward()
            lastDrive = "0"
    pass


def algorithm2Start():
    print("started algorithm 2...")
    setAlgorithm(algorithm1Loop)


def algorithm2Loop():
    pass


def algorithm3Start():
    print("started algorithm 3...")
    setAlgorithm(algorithm1Loop)


def algorithm3Loop():
    pass


def algorithm4Start():
    print("started algorithm 4...")
    setAlgorithm(algorithm1Loop)


def algorithm4Loop():
    pass


def algorithm5Start():
    print("started algorithm 5...")
    setAlgorithm(algorithm1Loop)


def algorithm5Loop():
    pass


def algorithm6Start():
    print("started algorithm 6...")
    setAlgorithm(algorithm1Loop)


def algorithm6Loop():
    pass


def algorithm7Start():
    print("started algorithm 7...")
    setAlgorithm(algorithm1Loop)


def algorithm7Loop():
    pass


def algorithm8Start():
    print("started algorithm 8...")
    setAlgorithm(algorithm1Loop)


def algorithm8Loop():
    pass


def algorithm9Start():
    print("started algorithm 9...")
    setAlgorithm(algorithm1Loop)


def algorithm9Loop():
    pass


def algorithm10Start():
    print("started algorithm 10...")
    setAlgorithm(algorithm1Loop)


def algorithm10Loop():
    pass


def mainLoop():
    global renewContinuous, digestTime

    if time.time() > renewContinuous:
        renewContinuous = time.time() + 1
        if readingDistanceContinuous:
            pyroslib.publish("sensor/distance/continuous", "continue")
        if readingGyroContinuous:
            pyroslib.publish("sensor/gyro/continuous", "continue")

    if algorithm is not None:
        algorithm()

    if False and time.time() > digestTime:
        pyroslib.publish("overtherainbow/distances", str(distanceDeg1) + ":" + str(distance1) + ";" + str(avgDistance1) + "," + str(distanceDeg2) + ":" + str(distance2) + ";" + str(avgDistance2))
        pyroslib.publish("overtherainbow/gyro", str(gyroAngle))


algorithm = doNothing


if __name__ == "__main__":
    try:
        print("Starting over-the-rainbow agent...")

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(STROBO_LIGHT_GPIO, GPIO.OUT)

        pyroslib.subscribe("sensor/distance", handleDistances)
        pyroslib.subscribe("sensor/gyro", handleGyroData)
        pyroslib.subscribe("overtherainbow/command", handleOverTheRainbow)

        pyroslib.init("over-the-rainbow-agent", unique=True, onConnected=connected)

        print("Started over-the-rainbow agent.")

        pyroslib.forever(0.02, mainLoop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
