
#
# Copyright 2016-2018 Games Creators Club
#
# MIT License
#

import math
import time
import traceback

import numpy

import pyroslib
import cv2
import PIL
import PIL.Image
# import scipy
# import scipy.spatial

DEBUG_LEVEL_OFF = 0
DEBUG_LEVEL_INFO = 1
DEBUG_LEVEL_DEBUG = 2
DEBUG_LEVEL_ALL = 3
DEBUG_LEVEL = DEBUG_LEVEL_ALL

remotDebug = True

FORWARD_SPEED = 30
MINIMUM_FORWARD_SPEED = 20
MAX_FORWARD_SPEED = 60
MAX_FORWARD_DELTA = 50
MAX_ROTATE_SPEED = 50
MIN_ROTATE_SPEED = 14

MAX_ANGLE = 45
TURN_SPEED = 50

STOP_DISTANCE = 80
SIDE_DISTANCE = 120
CORNER_STOP_DISTANCE = 150
STEERING_DISTANCE = 400

MIN_RADUIS = 8
MIN_AREA = MIN_RADUIS * MIN_RADUIS * math.pi * 0.7
MAX_AREA = 13000.0

SPEEDS_ROVER_2 = [-20, -20, -20, -15, -10, -9, 9, 10, 12, 15, 20, 30, 30]
SPEEDS_ROVER_4 = [-20, -20, -20, -15, -14, -14, 30, 30, 35, 40, 35, 40, 40]
SPEEDS = SPEEDS_ROVER_4
SPEEDS_OFFSET = 6

DISTANCE_AVG_TIME = 0.5

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

gyroAngle = 0
gyroDeltaAngle = 0
gyroStartAngle = 0
gyroIntegral = 0
EPSILON_ANGLE = 2

readingDistanceContinuous = True
readingGyroContinuous = True
renewContinuous = time.time()
digestTime = time.time()

size = (320, 256)

stopCountdown = 0


def doNothing():
    pass


lastProcessed = time.time()
algorithm = doNothing
algorithmIndex = 0
algorithmsList = []
doDistance = doNothing
doGyro = doNothing

KGAIN_INDEX = 0
KpI = 1
KiI = 2
KdI = 3

ERROR_INDEX = 0
PREVIOUS_ERROR_INDEX = 1
INTEGRAL_INDEX = 2
DERIVATIVE_INDEX = 3
DELTA_TIME_INDEX = 4

lastDistanceReceivedTime = time.time()
deltaTime = 0
lastGyroReceivedTime = time.time()
gyroDeltaTime = 0

forwardIntegral = 0

forwardGains = [1, 0.8, 0.6, 0.2]
sideGains = [1.1, 0.8, 0.3, 0.05]
gyroGains = [1.8, 0.8, 1, 0.2]

KA = 15

ACTION_NONE = 0
ACTION_TURN = 1
ACTION_DRIVE = 2

sideAngleAccum = 0
lastAngle = 0
lastForwardSpeed = 0
lastForwardDelta = 0
accumSideDeltas = []
sideAngleAccums = []
accumForwardDeltas = []
ACCUM_SIDE_DETALS_SIZE = 4

foundColours = ""
cvResults = None


def log(level, what):
    if level <= DEBUG_LEVEL:
        print(what)


def logArgs(*msg):
    tnow = time.time()
    dt = str((tnow - distanceTimestamp) * 1000) + "ms"

    logMsg = formatArgR("", int(tnow * 1000) % 100000, 7) + " " + " ".join(msg)
    log(DEBUG_LEVEL_DEBUG, logMsg)


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


def connected():
    pyroslib.publish("sensor/gyro/continuous", "calibrate,50")

    pyroslib.publish("camera/processed/fetch", "")
    pyroslib.publish("camera/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")


def handleDistances(topic, message, groups):
    global historyDistancesDeg1, historyDistancesDeg2, historyDistances1, historyDistances2, historyDistanceTimes1, historyDistanceTimes2
    global distanceDeg1, distanceDeg2, distance1, distance2, avgDistance1, avgDistance2, distanceTimestamp, deltaDistance1, deltaDistance2
    global deltaTime, lastDistanceReceivedTime

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


def handleOverTheRainbow(topic, message, groups):
    global algorithm, algorithmsList

    data = message.split(":")

    cmd = data[0]

    if cmd == "stop":
        algorithmsList[:] = []
        stop()
    elif cmd == "alg1":
        setAlgorithm(findCorner)
    elif cmd == "alg2":
        setAlgorithm(followLeftWall)
    elif cmd == "alg3":
        setAlgorithm(followRightWall)
    elif cmd == "alg4":
        setAlgorithm(findColours)
    elif cmd == "alg5":
        setAlgorithm(findColoursFast)
    elif cmd == "alg6":
        setAlgorithm(rotateRight90)
    elif cmd == "alg7":
        setAlgorithm(rotateLeft135)
    elif cmd == "alg8":
        setAlgorithm(rotateRight135)
    elif cmd == "alg9":
        setAlgorithm(rotate180)
    elif cmd == "alg10":
        setAlgorithm(moveBack)


def normalise(value, maxValue):
    if value > maxValue:
        value = maxValue
    if value < -maxValue:
        value = -maxValue

    return value / maxValue


def sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0


def resetPid(pidValues):
    pidValues[ERROR_INDEX] = 0
    pidValues[PREVIOUS_ERROR_INDEX] = 0
    pidValues[DERIVATIVE_INDEX] = 0
    pidValues[INTEGRAL_INDEX] = 0
    pidValues[DELTA_TIME_INDEX] = 0


def pid(error, pidValues, gains, dt):
    pidValues[ERROR_INDEX] = error
    integral = pidValues[INTEGRAL_INDEX]
    previous_error = pidValues[PREVIOUS_ERROR_INDEX]

    integral = integral + error * dt
    derivative = (error - previous_error) / dt
    output = gains[KpI] * error + gains[KiI] * integral + gains[KdI] * derivative

    pidValues[PREVIOUS_ERROR_INDEX] = error
    pidValues[INTEGRAL_INDEX] = integral
    pidValues[DERIVATIVE_INDEX] = derivative
    pidValues[DELTA_TIME_INDEX] = dt

    return output * gains[KGAIN_INDEX]


def calculateSpeed(speed):
    speedIndex = int(speed * SPEEDS_OFFSET + SPEEDS_OFFSET)
    speed = SPEEDS[speedIndex]
    return speed


def steer(steerDistance=0, speed=FORWARD_SPEED):
    pyroslib.publish("move/steer", str(int(steerDistance)) + " " + str(int(speed)))


def drive(angle=0, speed=FORWARD_SPEED):
    pyroslib.publish("move/drive", str(int(angle)) + " " + str(int(speed)))


def driveForward(speed=FORWARD_SPEED):
    pyroslib.publish("move/drive", "0 " + str(speed))


def driveBack(speed=FORWARD_SPEED):
    pyroslib.publish("move/drive", "0 " + str(-speed))


def rotateLeft(speed):
    pyroslib.publish("move/rotate", str(-speed))


def rotateRight(speed):
    pyroslib.publish("move/rotate", str(int(speed)))


def rotate(speed):
    pyroslib.publish("move/rotate", str(int(speed)))


def requestDistanceAtAngle(angle):
    pyroslib.publish("sensor/distance/deg", str(angle))


countDown = 0
drive_speed = 0


def brake():
    global countDown

    countDown -= 1

    if countDown < -50:
        stop()
    elif countDown < 0:
        stopDriving()
        log(DEBUG_LEVEL_ALL, "Stopped for " + str(countDown))
    else:
        log(DEBUG_LEVEL_ALL, "Breaking for " + str(countDown))
        driveBack(50)


def stopDriving():
    pyroslib.publish("move", "0 0")
    pyroslib.publish("move/stop", "")


def stop():
    global algorithmIndex, algorithmsList, doDistance, doGyro

    doDistance = doNothing
    doGyro = doNothing

    # log(DEBUG_LEVEL_ALL, "stopping")
    stopDriving()
    algorithmIndex += 1
    if algorithmIndex < len(algorithmsList):
        log(DEBUG_LEVEL_ALL, "setting algorithm to index " + str(algorithmIndex) + " out of " + str(len(algorithmsList)))
        setAlgorithm(algorithmsList[algorithmIndex])
    else:
        log(DEBUG_LEVEL_ALL, "Stopping all...")
        setAlgorithm(doNothing)
        algorithmsList[:] = algorithmsList
        log(DEBUG_LEVEL_INFO, "Stopped!")


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


def findCorner():
    global stopCountdown, doDistance, forwardIntegral

    log(DEBUG_LEVEL_DEBUG, "Finding corner")
    requestDistanceAtAngle("45")

    setAlgorithm(doNothing)
    stopCountdown = 0
    forwardIntegral = 0
    doDistance = findCornerDistanceHandler


def findCornerDistanceHandler():
    global stopCountdown, forwardIntegral

    def log1(*msg):
        logArgs(*((formatArgL("  dt", round(deltaTime, 3), 5),
                   formatArgR("  ld", distance1, 5), formatArgR("  fdd", deltaDistance1, 5),
                   formatArgR("  rd", distance2, 5), formatArgR("  sdd", deltaDistance2, 5)) + msg))

    dt = deltaTime
    forwardDistance = distance1 + distance2
    forwardDelta = - math.sqrt(deltaDistance1 * deltaDistance1 + deltaDistance2 * deltaDistance2)

    if abs(forwardDelta) < 20:
        forwardIntegral += forwardDelta
    else:
        forwardIntegral = 0

    if stopCountdown > 0:
        log1(formatArgR("s", round(0, 1), 4), formatArgR("a", round(0, 1), 3))
        drive(0, 0)
        stopCountdown -= 1
        if stopCountdown == 0:
            stop()

    elif distance1 * distance1 + distance2 * distance2 < CORNER_STOP_DISTANCE * CORNER_STOP_DISTANCE:
        # stop()
        stopCountdown = 3

    else:
        forwardError = math.sqrt(distance1 * distance1 + distance2 * distance2) - CORNER_STOP_DISTANCE

        forwardSpeed = forwardGains[KGAIN_INDEX] * (forwardError * forwardGains[KpI] - forwardIntegral * forwardGains[KiI] + (forwardDelta / dt) * forwardGains[KdI])
        forwardSpeed = normalise(forwardSpeed, MAX_FORWARD_SPEED) * MAX_FORWARD_SPEED

        if abs(distance1 - distance2) > 1:  # and distance1 < 380 and distance2 < 380:
            angle = int(math.log10(abs(distance1 - distance2)) * KA) * sign(distance1 - distance2)
        else:
            angle = 0

        drive(angle, forwardSpeed)
        log1(" CORN ", formatArgR("s", round(forwardSpeed, 1), 6), formatArgR("a", round(angle, 1), 5), formatArgR("e", round(forwardError), 5), formatArgR("i", round(forwardIntegral, 1), 6), formatArgR("fwd", round(forwardDelta), 6))


def followSide(forwardDistance, forwardDelta, sideDistance, sideDelta, direction, dt):
    global stopCountdown, lastAngle
    global forwardIntegral, lastForwardSpeed, lastForwardDelta
    global accumSideDeltas, sideAngleAccums, accumForwardDeltas

    def log1(*msg):
        logArgs(*((formatArgL("  dt", round(dt, 3), 5),
                   formatArgR("  fd", forwardDistance, 5), formatArgR("  fdd", forwardDelta, 5),
                   formatArgR("  sd", sideDistance, 5), formatArgR("  sdd", sideDelta, 5)) + msg))

    if stopCountdown > 0:
        log1(formatArgR("s", round(0, 1), 4), formatArgR("a", round(0, 1), 3))
        drive(0, 0)
        stopCountdown -= 1
        if stopCountdown == 0:
            stop()

    elif forwardDistance < STOP_DISTANCE:
        # stop()
        stopCountdown = 3
        log1("Stopping!")
    else:
        if forwardDistance > 1000:
            forwardDelta = - MAX_FORWARD_DELTA

        if abs(forwardDelta) > MAX_FORWARD_DELTA:
            forwardDelta = sign(forwardDelta) * MAX_FORWARD_DELTA

        # if forwardDistance > 1000:
        #     forwardDelta = - int(MAX_FORWARD_SPEED / 2)
        #
        # if abs(forwardDelta) > (MAX_FORWARD_SPEED / 2) * 1.5:
        #     forwardDelta = sign(forwardDelta) * int(MAX_FORWARD_SPEED / 2)
        #
        # if abs(forwardDelta) < 0.1:
        #     forwardDelta = -int(MAX_FORWARD_SPEED / 2)

        if abs(forwardDelta) < 20:
            forwardIntegral += forwardDelta
        else:
            forwardIntegral = 0

        forwardError = forwardDistance - STOP_DISTANCE

        forwardSpeed = forwardGains[KGAIN_INDEX] * (forwardError * forwardGains[KpI] + forwardIntegral * forwardGains[KiI] + (forwardDelta / dt) * forwardGains[KdI])
        forwardSpeed = normalise(forwardSpeed, MAX_FORWARD_SPEED) * MAX_FORWARD_SPEED

        angle = sideGains[KGAIN_INDEX] * ((sideDistance - SIDE_DISTANCE) * sideGains[KpI] + (sideDelta / dt) * sideGains[KdI])
        angle = - direction * normalise(angle, MAX_ANGLE) * MAX_ANGLE

        accumSideDeltas.append(sideDelta)
        while len(accumSideDeltas) > ACCUM_SIDE_DETALS_SIZE:
            del accumSideDeltas[0]

        accumSideDelta = sum(accumSideDeltas) / len(accumSideDeltas)

        accumForwardDeltas.append(forwardDelta)
        while len(accumForwardDeltas) > ACCUM_SIDE_DETALS_SIZE:
            del accumForwardDeltas[0]

        accumForwardDelta = sum(accumForwardDeltas) / len(accumForwardDeltas)

        if len(sideAngleAccums) > 0:
            sideAngleAccum = sum(sideAngleAccums) / len(sideAngleAccums)
        else:
            sideAngleAccum = 0

        if len(sideAngleAccums) > 2 and (sign(sideAngleAccum) != sign(accumSideDelta) or abs(accumSideDelta) < 5) and abs(sideAngleAccum) > 9:
            nextAction = ACTION_TURN
            sideAngleAccums = []
        else:
            sideAngleAccums.append(angle)
            while len(sideAngleAccums) > ACCUM_SIDE_DETALS_SIZE:
                del sideAngleAccums[0]
            nextAction = ACTION_DRIVE

        if nextAction == ACTION_DRIVE:
            log1(" DRIV ", formatArgR("i", round(forwardIntegral, 1), 6), formatArgR("s", round(forwardSpeed, 1), 6), formatArgR("a", round(angle, 1), 5), formatArgR("saa", round(sideAngleAccum), 6))
            drive(angle, forwardSpeed)
        else:
            turnDirection = 1
            dmsg = "turn to wall td:" + str(turnDirection)
            if sideAngleAccum < 0:
                turnDirection = -turnDirection
                dmsg = "turn away the wall td:" + str(turnDirection)

            if forwardSpeed < MINIMUM_FORWARD_SPEED:
                forwardSpeed = MINIMUM_FORWARD_SPEED

            forwardSpeed = (forwardSpeed + lastForwardSpeed) / 2

            angleR = sideAngleAccum / 180

            fudgeFactor = 0.5

            steerDistance = fudgeFactor * turnDirection * abs(accumForwardDelta) / abs(angleR)

            log1(" TURN ", formatArgR("s", round(forwardSpeed, 1), 6), formatArgR("sd", round(steerDistance, 1), 6), formatArgR("saa", round(sideAngleAccum), 6), formatArgR("asd", round(accumSideDelta), 6), formatArgR("fwd", round(forwardDelta), 6), dmsg)
            steer(steerDistance, forwardSpeed)

            accumSideDeltas = []
            accumForwardDeltas = []

        lastForwardSpeed = forwardSpeed
        lastForwardDelta = forwardDelta
        lastSideDelta = sideDelta


def setupFollowSide():
    global stopCountdown, sideAngleAccum, sideAngleAccumCnt, forwardIntegral, lastForwardSpeed, lastForwardDelta
    global accumSideDeltas, sideAngleAccums, accumForwardDeltas

    setAlgorithm(doNothing)
    forwardIntegral = 0
    stopCountdown = 0
    sideAngleAccum = 0
    sideAngleAccumCnt = 0
    lastForwardSpeed = 0
    lastForwardDelta = 0
    accumSideDeltas = []
    sideAngleAccums = []
    accumForwardDeltas = []


def followLeftWall():
    global doDistance

    def followSideHandleDistance():
        followSide(distance1, deltaDistance1, distance2, deltaDistance2, 1, deltaTime)

    log(DEBUG_LEVEL_DEBUG, "Following left wall")
    requestDistanceAtAngle("0")
    setupFollowSide()
    doDistance = followSideHandleDistance


# follow right wall
def followRightWall():
    global doDistance

    def followSideHandleDistance():
        followSide(distance2, deltaDistance2, distance1, deltaDistance1, -1, deltaTime)

    log(DEBUG_LEVEL_DEBUG, "Following right wall")
    setupFollowSide()
    requestDistanceAtAngle("90")
    doDistance = followSideHandleDistance


# corner
def findColours():
    global foundColours, algorithmIndex, algorithmsList, askedCamera

    log(DEBUG_LEVEL_DEBUG, "Finding colours")

    askedCamera = 0
    foundColours = ""
    algorithmIndex = 0
    algorithmsList[:] = []

    algorithmsList.append(rotateLeft45)
    algorithmsList.append(findColoursLoop)

    setAlgorithm(algorithmsList[0])


# corner
def findColoursFast():
    global foundColours, algorithmIndex, algorithmsList, askedCamera

    log(DEBUG_LEVEL_DEBUG, "Finding colours")

    askedCamera = 0
    foundColours = ""
    algorithmIndex = 0
    algorithmsList[:] = []

    algorithmsList.append(findColoursLoop)

    setAlgorithm(algorithmsList[0])


def findColoursLoop():
    global foundColours, askedCamera, cvResults

    def colourToLetter(colour):
        if "red" == colour:
            return "R"
        elif "green" == colour:
            return "G"
        elif "yellow" == colour:
            return "Y"
        else:
            return "B"

    def move90Deg():
        global algorithmIndex, algorithmsList, askedCamera

        askedCamera = 0
        setAlgorithms(rotateLeft90, findColoursLoop)
        log(DEBUG_LEVEL_DEBUG, "Moving another 90 deg...")

    def move90DegReverse():
        global algorithmIndex, algorithmsList, askedCamera

        askedCamera = 0
        setAlgorithms(rotateRight90, findColoursLoop)
        log(DEBUG_LEVEL_DEBUG, "Moving reverse -90 deg...")

    def move180Deg():
        global algorithmIndex, algorithmsList, askedCamera

        askedCamera = 0
        setAlgorithms(rotate180, findColoursLoop)
        log(DEBUG_LEVEL_DEBUG, "Moving another 180 deg...")

    def moveLast90Deg():
        global algorithmIndex, algorithmsList, askedCamera

        askedCamera = 0
        setAlgorithms(rotateLeft90, foundColoursGoFurther)
        log(DEBUG_LEVEL_DEBUG, "Moving last 90 deg...")

    def moveLast90DegReverse():
        global algorithmIndex, algorithmsList, askedCamera

        askedCamera = 0
        setAlgorithms(rotateRight90, foundColoursGoFurther)
        log(DEBUG_LEVEL_DEBUG, "Moving last 90 deg...")

    def moveLast180Deg():
        global algorithmIndex, algorithmsList, askedCamera

        askedCamera = 0
        setAlgorithms(rotate180, foundColoursGoFurther)
        log(DEBUG_LEVEL_DEBUG, "Moving last 90 deg...")

    if askedCamera == 0:
        log(DEBUG_LEVEL_DEBUG, "Asked camera first time")
        cvResults = None
        pyroslib.publish("camera/raw/fetch", "")
        askedCamera = 1

    elif cvResults is not None:
        log(DEBUG_LEVEL_ALL, "Got results...")
        if 1 <= askedCamera < 4:
            if len(cvResults) == 1 and cvResults[0][2] != "red" and cvResults[0][2] != "yellow":
                foundColours = colourToLetter(cvResults[0][2]) + foundColours
                log(DEBUG_LEVEL_DEBUG, "Got one non red result " + foundColours)
                move90Deg()
            else:
                log(DEBUG_LEVEL_ALL, "Asked camera " + str(askedCamera) + ". Got " + str(len(cvResults)) + " results: " + str(cvResults))
                pyroslib.publish("camera/raw/fetch", "")
                askedCamera += 1
        else:
            if len(cvResults) == 1:
                foundColours = colourToLetter(cvResults[0][2]) + foundColours
                log(DEBUG_LEVEL_DEBUG, "Got one result after " + str(askedCamera) + " times: " + foundColours)
            else:
                f = "X"
                i = 0
                while i < len(cvResults) and f == "X" or f == "R":
                    f = colourToLetter(cvResults[i][2])
                    i = i + 1

                foundColours = f + foundColours
                log(DEBUG_LEVEL_DEBUG, "Cannot determine result so gone with " + f + " total: " + foundColours + " results: " + str(cvResults))

            move90Deg()
        cvResults = None
    else:
        pass

    if "R" not in foundColours and "X" not in foundColours and len(foundColours) == 3:
        log(DEBUG_LEVEL_DEBUG, "Found colours: " + str(foundColours) + " stopping!")
        foundColours = "R" + foundColours
        moveLast90Deg()

    elif len(foundColours) >= 4:
        moveToRed = False
        if "X" in foundColours:
            if foundColours.count("X") == 1:
                if "R" not in foundColours:
                    foundColours = foundColours.replace("X", "R")
                elif "G" not in foundColours:
                    foundColours = foundColours.replace("X", "G")
                elif "Y" not in foundColours:
                    foundColours = foundColours.replace("X", "Y")
                elif "B" not in foundColours:
                    foundColours = foundColours.replace("X", "B")
                moveToRed = True
            else:
                c = 0
                while foundColours[0] != "X":
                    foundColours = foundColours[3] + foundColours[0:3]
                    c += 1

                if c == 0:
                    askedCamera = 1
                    pyroslib.publish("camera/raw/fetch", "")
                elif c == 1:
                    log(DEBUG_LEVEL_DEBUG, "Undetermined colour moving 90 deg")
                    move90Deg()
                elif c == 2:
                    log(DEBUG_LEVEL_DEBUG, "Undetermined colour moving 180 deg")
                    move180Deg()
                elif c == 3:
                    log(DEBUG_LEVEL_DEBUG, "Undetermined colour moving -90 deg")
                    move90DegReverse()

        else:
            log(DEBUG_LEVEL_DEBUG, "Found colours: " + str(foundColours) + " stopping!")
            moveToRed = True

        if moveToRed:
            c = 0
            while foundColours[0] != "R":
                foundColours = foundColours[3] + foundColours[0:3]
                c += 1

            if c == 0:
                setAlgorithms(foundColoursGoFurther)
                log(DEBUG_LEVEL_DEBUG, "Next step colours: " + str(foundColours) + "")
                setAlgorithms(foundColoursGoFurther)
            elif c == 1:
                log(DEBUG_LEVEL_DEBUG, "Next step colours: " + str(foundColours) + " last 90 deg")
                moveLast90Deg()
            elif c == 2:
                log(DEBUG_LEVEL_DEBUG, "Next step colours: " + str(foundColours) + " last 180 deg")
                moveLast180Deg()
            elif c == 3:
                log(DEBUG_LEVEL_DEBUG, "Next step colours: " + str(foundColours) + " last -90 deg")
                moveLast90DegReverse()


def foundColoursGoFurther():
    log(DEBUG_LEVEL_DEBUG, "Final result is " + foundColours)
    allTogether(foundColours)


def rotateForAngle(angle):
    global gyroAngle, gyroStartAngle, doGyro, gyroIntegral

    def log1(*msg):
        logArgs(*((formatArgL("  dt", round(gyroDeltaTime, 3), 5),
                formatArgR("  ga", gyroAngle, 5), formatArgR("  gda", gyroDeltaAngle, 5)) + msg))

    def handleGyroRorate():
        global gyroAngle, gyroStartAngle, stopCountdown, gyroIntegral

        stopped = False

        if abs(gyroAngle - angle) < EPSILON_ANGLE:
            if stopCountdown == 0:
                stopCountdown = 20
            else:
                stopCountdown -= 1
                if stopCountdown == 0:
                    stop()
                    stopped = True

        if not stopped:
            gyroError = gyroAngle - angle

            if abs(gyroDeltaAngle) < 2.5:
                gyroIntegral += gyroError
                if gyroIntegral > MAX_ROTATE_SPEED * 2 / (gyroGains[KiI] * gyroDeltaTime):
                    gyroIntegral = MAX_ROTATE_SPEED * 2 / (gyroGains[KiI] * gyroDeltaTime)
            else:
                gyroIntegral = 0

            speed = - gyroGains[KGAIN_INDEX] * (gyroError * gyroGains[KpI] + gyroIntegral * gyroDeltaTime * gyroGains[KiI] + (gyroDeltaAngle / gyroDeltaTime) * gyroGains[KdI])
            speed = normalise(speed, MAX_ROTATE_SPEED) * MAX_ROTATE_SPEED

            log1(formatArgR("i", round(gyroIntegral, 1), 5), formatArgR("s", round(speed, 1), 5))
            rotate(speed)

    log(DEBUG_LEVEL_DEBUG, "Rotating for " + str(angle))
    gyroAngle = 0
    gyroIntegral = 0
    gyroStartAngle = 0
    setAlgorithm(doNothing)
    doGyro = handleGyroRorate


def rotateRight4():
    rotateForAngle(45)


def rotateLeft45():
    rotateForAngle(-45)


def rotateRight90():
    rotateForAngle(90)


def rotateLeft90():
    rotateForAngle(-90)


def rotateRight135():
    rotateForAngle(135)


def rotateLeft135():
    rotateForAngle(-135)


def rotate180():
    rotateForAngle(180)


def allTogether(stringOfFourLetters):
    global algorithmIndex, algorithmsList

    if stringOfFourLetters == "RYGB":
        setAlgorithms(findCorner, rotateLeft135, followRightWall, rotateLeft135, findCorner, rotateRight135, followLeftWall)
    elif stringOfFourLetters == "RGBY":
        setAlgorithms(findCorner, rotate180, findCorner, rotateRight135, followLeftWall, rotateRight135, findCorner)
    elif stringOfFourLetters == "RBYG":
        setAlgorithms(findCorner, rotateRight135, followLeftWall, rotateRight90, followLeftWall, rotateRight90, followLeftWall)
    elif stringOfFourLetters == "RYBG":
        setAlgorithms(findCorner, rotate180, findCorner, rotateLeft135, followRightWall, rotateLeft135, findCorner)
    elif stringOfFourLetters == "RGYB":
        setAlgorithms(findCorner, rotateLeft135, followRightWall, rotateLeft90, followRightWall, rotateLeft90, followRightWall)
    elif stringOfFourLetters == "RBGY":
        setAlgorithms(findCorner, rotateRight135, followLeftWall, rotateRight135, findCorner, rotateLeft135, followRightWall)
    else:
        stop()


def algorithm9Start():
    global drive_speed

    log(DEBUG_LEVEL_DEBUG, "started algorithm 9...")
    requestDistanceAtAngle("45")
    drive_speed = FORWARD_SPEED
    # setAlgorithm(algorithm9Loop)
    allTogether("BGRY")


def algorithm9Loop():
    pass


def moveBack():
    global countDown
    log(DEBUG_LEVEL_DEBUG, "started algorithm 10...")
    countDown = 50
    driveBack(MAX_FORWARD_SPEED)
    setAlgorithm(moveBackLoop)


def moveBackLoop():
    global countDown
    countDown -= 1
    if countDown <= 0:
        stop()


def handleCameraRaw(topic, message, groups):
    global lastProcessed, localFPS

    now = time.time()
    delta = now - lastProcessed
    lastProcessed = now

    if delta < 5:
        localFPS = "%.2f" % round(1 / delta, 2)
    else:
        localFPS = "-"

    pilImage = toPILImage(message)
    openCVImage = numpy.array(pilImage)
    # result = processImage(pilImage)

    results = processImageCV(openCVImage)
    message = ""

    for result in results:
        message = message + str(int(result[0])) + "," + str(int(result[1])) + "," + str(result[2]) + "," + str(int(result[3]))
        if len(result) > 4:
            message = message + "," + str(result[4])
        message = message + "\n"

    if len(message) > 0:
        message = message[:-1]

    log(DEBUG_LEVEL_DEBUG, "Image details: " + message)

    pyroslib.publish("overtherainbow/imagedetails", message)


def toPILImage(imageBytes):
    pilImage = PIL.Image.frombytes("RGB", size, imageBytes)
    return pilImage


def processImageCV(image):
    global cvResults

    def findColourNameHSV(hChannel, contour):

        mask = numpy.zeros(hChannel.shape[:2], dtype="uint8")
        cv2.drawContours(mask, [contour], -1, 255, -1)
        mask = cv2.erode(mask, None, iterations=2)
        # mean = cv2.mean(hChannel, mask=mask)

        maskAnd = hChannel.copy()
        cv2.bitwise_and(hChannel, mask, maskAnd)

        pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(maskAnd, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
        log(DEBUG_LEVEL_ALL, "Published mask ")

        # mean = mean[0]
        #
        hist = cv2.calcHist([hChannel], [0], mask, [255], [0, 255], False)

        value = numpy.argmax(hist)
        # histMax = hist[histMaxIndex]
        #
        # log(DEBUG_LEVEL_ALL, "Got mean as " + str(mean) + " max hist " + str(histMaxIndex))

        # value = histMaxIndex

        # initialize the minimum distance found thus far
        # red < 36 > 330 - 18/165
        # yellow >= 45 <= 70 - 22/35
        # green >= 86 <= 155 - 43/176
        # blue >= 180 <= 276 - 90/138
        if value < 19 or value > 145:
            return "red", value
        elif 19 <= value <= 34:
            return "yellow", value
        elif 40 <= value <= 76:
            return "green", value
        elif 90 <= value <= 138:
            return "blue", value
        else:
            return "", value

    def sanitiseContours(cnts):

        for i in range(len(cnts) - 1, -1, -1):
            center, radius = cv2.minEnclosingCircle(cnts[i])
            area = cv2.contourArea(cnts[i])
            if radius < MIN_RADUIS or area < MIN_AREA or area > MAX_AREA or center[1] >= 128:
                # log(DEBUG_LEVEL_ALL, "Deleting contour " + str(i) + " raduis " + str(radius) + " area " + str(area))
                del cnts[i]
            else:
                # log(DEBUG_LEVEL_ALL, "Keeping contour " + str(i) + " raduis " + str(radius) + " area " + str(area))
                pass

    def adaptiveFindContours(sChannel, vChannel):
        gray = sChannel.copy()
        cv2.addWeighted(sChannel, 0.4, vChannel, 0.6, 0, gray)

        lastMax = 256
        lastMin = 0
        threshLimit = 225
        # threshLimit = 128

        iteration = 0

        while True:
            thresh = cv2.threshold(gray, threshLimit, 255, cv2.THRESH_BINARY)[1]
            iteration += 1

            # find contours in the thresholded image
            cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = cnts[1]

            initialCntNum = len(cnts)
            sanitiseContours(cnts)

            pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
            # log(DEBUG_LEVEL_ALL, "Published gray image")

            if iteration % 1 == 0:
                log(DEBUG_LEVEL_ALL, "... iteration " + str(iteration) + " min/current/max " + str(lastMin) + "/" + str(threshLimit) + "/" + str(lastMax) + " orig/sanitised " + str(initialCntNum) + "/" + str(len(cnts)))

            if 0 < len(cnts) < 6:
                log(DEBUG_LEVEL_ALL, "Found good number of areas after " + str(iteration) + " iterations, contours " + str(len(cnts)))
                return cnts, thresh

            if threshLimit < 30 or threshLimit > 225 or lastMax - lastMin < 4:
                log(DEBUG_LEVEL_ALL, "Failed to find good number of areas after " + str(iteration) + " iterations")
                return cnts, thresh

            threshLimit -= 25

    blurred = cv2.GaussianBlur(image, (5, 5), 0)

    hsv = cv2.cvtColor(blurred, cv2.COLOR_RGB2HSV)
    hueChannel, satChannel, valChannel = cv2.split(hsv)

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(hueChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    log(DEBUG_LEVEL_ALL, "Published hue channel image")

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(valChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    log(DEBUG_LEVEL_ALL, "Published value channel image")

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(satChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    log(DEBUG_LEVEL_ALL, "Published saturation channel image")

    countours, threshold = adaptiveFindContours(satChannel, valChannel)

    treshback = cv2.cvtColor(threshold, cv2.COLOR_GRAY2RGB)
    cv2.drawContours(treshback, countours, -1, (0, 255, 0), 2)

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(threshold, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    log(DEBUG_LEVEL_ALL, "Published gray image")

    pil = PIL.Image.fromarray(treshback)
    pyroslib.publish("overtherainbow/processed", pil.tobytes("raw"))
    log(DEBUG_LEVEL_ALL, "Published threshold image")

    results = []

    log(DEBUG_LEVEL_ALL, "Have " + str(len(countours)) + " contours")
    for c in countours:

        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.04 * peri, True)

        cntrCenter, cntrRadius = cv2.minEnclosingCircle(c)

        colourName, extraInfo = findColourNameHSV(hueChannel, c)

        if len(colourName) > 0:
            results.append((cntrCenter[0], cntrCenter[1], colourName, cntrRadius, str(extraInfo)))

    cvResults = results

    return results


def mainLoop():
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
        pyroslib.publish("overtherainbow/distances", str(distanceDeg1) + ":" + str(distance1) + ";" + str(avgDistance1) + "," + str(distanceDeg2) + ":" + str(distance2) + ";" + str(avgDistance2))
        pyroslib.publish("overtherainbow/gyro", str(gyroAngle))
        digestTime = thisTime + 0.1


algorithm = doNothing


if __name__ == "__main__":
    try:
        print("Starting over-the-rainbow agent...")

        pyroslib.subscribe("sensor/distance", handleDistances)
        pyroslib.subscribe("sensor/gyro", handleGyroData)
        pyroslib.subscribe("overtherainbow/command", handleOverTheRainbow)
        pyroslib.subscribeBinary("camera/raw", handleCameraRaw)

        pyroslib.init("over-the-rainbow-agent", unique=True, onConnected=connected)

        print("Started over-the-rainbow agent.")

        pyroslib.forever(0.02, mainLoop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
