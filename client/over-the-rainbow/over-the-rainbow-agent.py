
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

DEBUG = True

FORWARD_SPEED = 30
MINIMUM_FORWARD_SPEED = 20
MAX_FORWARD_SPEED = 60
MAX_ROTATE_SPEED = 60
MIN_ROTATE_SPEED = 10

MAX_ANGLE = 45
TURN_SPEED = 50

STOP_DISTANCE = 80
SIDE_DISTANCE = 120
CORNER_STOP_DISTANCE = 150
STEERING_DISTANCE = 400


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

forwardGains = [1, 0.75, 0.3, 0.25]
forwardPid = [0, 0, 0, 0, 0]
forwardIntegral = 0

sideGains = [1.1, 0.8, 0.3, 0.05]
sidePid = [0, 0, 0, 0, 0]

gyroGains = [1.1, 0.8, 0.4, 0.05]
gyroPid = [0, 0, 0, 0, 0]

KA = 10

ACTION_NONE = 0
ACTION_TURN = 1
ACTION_DRIVE = 2

lastActionTime = 0
sideAngleAccum = 0
lastAngle = 0


def setAlgorithm(alg):
    global algorithm
    algorithm = alg


def connected():
    pyroslib.publish("sensor/gyro/continuous", "calibrate,50")

    pyroslib.publish("camera/processed/fetch", "")
    pyroslib.publish("camera/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")


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


def handleDistances(topic, message, groups):
    global historyDistancesDeg1, historyDistancesDeg2, historyDistances1, historyDistances2, historyDistanceTimes1, historyDistanceTimes2
    global distanceDeg1, distanceDeg2, distance1, distance2, avgDistance1, avgDistance2, distanceTimestamp, deltaDistance1, deltaDistance2
    global deltaTime, lastDistanceReceivedTime

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
        setAlgorithm(algorithm4Start)
    elif cmd == "alg5":
        setAlgorithm(rotateLeft90)
    elif cmd == "alg6":
        setAlgorithm(rotateRight90)
    elif cmd == "alg7":
        setAlgorithm(rotateLeft135)
    elif cmd == "alg8":
        setAlgorithm(rotateRight135)
    elif cmd == "alg9":
        setAlgorithm(algorithm9Start)
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
        log("Stopped for " + str(countDown))
    else:
        log("Breaking for " + str(countDown))
        driveBack(50)


def stopDriving():
    pyroslib.publish("move", "0 0")
    pyroslib.publish("move/stop", "")


def stop():
    global algorithmIndex, algorithmsList, doDistance, doGyro

    doDistance = doNothing
    doGyro = doNothing

    # print("stopping")
    stopDriving()
    algorithmIndex += 1
    if algorithmIndex < len(algorithmsList):
        print("setting algorithm to index " + str(algorithmIndex) + " out of " + str(len(algorithmsList)))
        setAlgorithm(algorithmsList[algorithmIndex])
    else:
        print("Stopping all...")
        setAlgorithm(doNothing)
        algorithmsList[:] = algorithmsList
        print("Stopped!")


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


def log(*msg):
    tnow = time.time()
    dt = str((tnow - distanceTimestamp) * 1000) + "ms"

    logMsg = formatArgR("", int(tnow * 1000) % 100000, 7) + " " + " ".join(msg)
    print(logMsg)


def findCorner():
    global stopCountdown, lastActionTime, doDistance, forwardIntegral

    print("1: Find corner")
    requestDistanceAtAngle("45")

    setAlgorithm(doNothing)
    resetPid(forwardPid)
    stopCountdown = 0
    forwardIntegral = 0
    doDistance = findCorderDistanceHandler


def findCorderDistanceHandler():
    global stopCountdown, forwardIntegral

    def log1(*msg):
        log(*((formatArgL("  dt", round(deltaTime, 3), 5),
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

        forwardSpeed = forwardGains[KGAIN_INDEX] * (forwardError * forwardGains[KpI] + (forwardDelta / dt) * forwardGains[KdI])
        forwardSpeed = normalise(forwardSpeed, MAX_FORWARD_SPEED) * MAX_FORWARD_SPEED

        if abs(distance1 - distance2) > 1:  # and distance1 < 380 and distance2 < 380:
            angle = int(math.log10(abs(distance1 - distance2)) * KA) * sign(distance1 - distance2)
        else:
            angle = 0

        drive(angle, forwardSpeed)
        log1(" CORN ", formatArgR("s", round(forwardSpeed, 1), 6), formatArgR("a", round(angle, 1), 5), formatArgR("e", round(forwardError), 5), formatArgR("i", round(forwardIntegral, 1), 6), formatArgR("fwd", round(forwardDelta), 6))


def followSide(forwardDistance, forwardDelta, sideDistance, sideDelta, direction, dt):
    global stopCountdown, lastActionTime, sideAngleAccum, lastAngle, forwardIntegral

    def log1(*msg):
        log(*((formatArgL("  dt", round(dt, 3), 5),
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

    else:
        if abs(forwardDelta) < 20:
            forwardIntegral += forwardDelta
        else:
            forwardIntegral = 0

        forwardError = forwardDistance - STOP_DISTANCE

        forwardSpeed = forwardGains[KGAIN_INDEX] * (forwardError * forwardGains[KpI] + forwardIntegral * forwardGains[KiI] + (forwardDelta / dt) * forwardGains[KdI])
        forwardSpeed = normalise(forwardSpeed, MAX_FORWARD_SPEED) * MAX_FORWARD_SPEED

        angle = sideGains[KGAIN_INDEX] * ((sideDistance - SIDE_DISTANCE) * sideGains[KpI] + (sideDelta / dt) * sideGains[KdI])
        angle = - direction * normalise(angle, MAX_ANGLE) * MAX_ANGLE

        lastActionTime -= deltaTime

        saa = sideAngleAccum
        if lastActionTime < 0:
            if abs(sideAngleAccum) > 12.5 and forwardSpeed > 0:
                nextAction = ACTION_TURN
            else:
                nextAction = ACTION_DRIVE

            lastActionTime = 0.5
            sideAngleAccum = 0
        else:
            nextAction = ACTION_DRIVE
            sideAngleAccum += angle

        angle = (sideDistance - SIDE_DISTANCE) * sideGains[KpI] + (sideDelta / dt) * sideGains[KdI]
        angle = - direction * normalise(angle, MAX_ANGLE) * MAX_ANGLE
        lastAngle = angle

        if nextAction == ACTION_DRIVE:
            log1(" DRIV ", formatArgR("i", round(forwardIntegral, 1), 6), formatArgR("s", round(forwardSpeed, 1), 6), formatArgR("a", round(angle, 1), 5), formatArgR("saa", round(saa), 6))
            drive(angle, forwardSpeed)
        else:
            if forwardDelta == 0:
                forwardDelta = -50  # moving forward
            elif forwardDelta < -60:
                forwardDelta = -50  # jump 1

            angleR = angle / 180

            steerDistance = -1 * forwardDelta / angleR

            log1(" TURN ", formatArgR("s", round(forwardSpeed, 1), 6), formatArgR("sd", round(steerDistance, 1), 5), formatArgR("saa", round(saa), 6), formatArgR("fwd", round(forwardDelta), 6))
            steer(steerDistance, forwardSpeed)


def setupFollowSide():
    global stopCountdown, sideAngleAccum, lastActionTime, forwardIntegral

    setAlgorithm(doNothing)
    resetPid(forwardPid)
    resetPid(sidePid)
    forwardIntegral = 0
    stopCountdown = 0
    sideAngleAccum = 0
    lastActionTime = 0.5


def followLeftWall():
    global doDistance

    def followSideHandleDistance():
        followSide(distance1, deltaDistance1, distance2, deltaDistance2, 1, deltaTime)

    print("2: Following left wall")
    requestDistanceAtAngle("0")
    setupFollowSide()
    doDistance = followSideHandleDistance


# follow right wall
def followRightWall():
    global doDistance

    def followSideHandleDistance():
        followSide(distance2, deltaDistance2, distance1, deltaDistance1, -1, deltaTime)

    print("2: Following right wall")
    setupFollowSide()
    requestDistanceAtAngle("90")
    doDistance = followSideHandleDistance


# corner
def algorithm4Start():
    driveForward(FORWARD_SPEED)
    print("started algorithm 4...")
    driveForward()
    setAlgorithm(algorithm4Loop)


def algorithm4Loop():
    if distance1 - deltaDistance1 < STOP_DISTANCE:
        stopDriving()
        stop()
    else:
        output = (distance1 - STOP_DISTANCE) / STOP_DISTANCE * 0.7 - deltaDistance1 * 0.3
        if output > 1:
            output = 1

        speedIndex = int(output * SPEEDS_OFFSET * 2)
        speed = SPEEDS[speedIndex]
        log("d:" + str(round(output, 2)) + " i:" + str(speedIndex) + " s:" + str(speed))
        drive(0, speed)


def rotateForAngle(angle):
    global gyroAngle, gyroStartAngle, doGyro, gyroIntegral

    def log1(*msg):
        log(*((formatArgL("  dt", round(gyroDeltaTime, 3), 5),
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

        if not stopped:
            gyroError = gyroAngle - angle

            if abs(gyroDeltaAngle) < 4:
                gyroIntegral += gyroError
            else:
                gyroIntegral = 0

            speed = - gyroGains[KGAIN_INDEX] * (gyroError * gyroGains[KpI] + gyroIntegral * gyroDeltaTime * gyroGains[KiI] + (gyroDeltaAngle / gyroDeltaTime) * gyroGains[KdI])
            speed = normalise(speed, MAX_ROTATE_SPEED) * MAX_ROTATE_SPEED

            log1(formatArgR("i", round(gyroIntegral, 1), 5), formatArgR("s", round(speed, 1), 5))
            rotate(speed)

            # if speed < MIN_ROTATE_SPEED:
            #     speed = MIN_ROTATE_SPEED

            # if stopCountdown > 0:
            #     log1(formatArgR("s", round(0, 1), 4), formatArgR("a", round(0, 1), 3))
            #     drive(0, 0)
            #     stopCountdown -= 1
            #     if stopCountdown == 0:
            #         stop()
            # else:
            #     log1(formatArgR("i", round(gyroIntegral, 1), 5), formatArgR("s", round(speed, 1), 5))
            #     rotate(speed)


    print("Rotating for " + str(angle))
    gyroAngle = 0
    gyroIntegral = 0
    gyroStartAngle = 0
    setAlgorithm(doNothing)
    resetPid(gyroPid)
    doGyro = handleGyroRorate


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

    algorithmIndex = 0
    algorithmsList[:] = []

    # algorithmsList.append(right90)
    # algorithmsList.append(right135)

    algorithmsList.append(findCorner)
    algorithmsList.append(rotateRight135)
    algorithmsList.append(followLeftWall)
    algorithmsList.append(rotateRight135)
    algorithmsList.append(findCorner)
    algorithmsList.append(rotateLeft135)
    algorithmsList.append(followRightWall())

    setAlgorithm(algorithmsList[0])


def algorithm9Start():
    global drive_speed

    print("started algorithm 9...")
    requestDistanceAtAngle("45")
    drive_speed = FORWARD_SPEED
    # setAlgorithm(algorithm9Loop)
    allTogether("BGRY")


def algorithm9Loop():
    pass


def moveBack():
    global countDown
    print("started algorithm 10...")
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

    print(message)

    pyroslib.publish("overtherainbow/imagedetails", message)

    # if sequence and not continuous:
    #     pyroslib.publish("camera/raw/fetch", "")


def toPILImage(imageBytes):
    pilImage = PIL.Image.frombytes("RGB", size, imageBytes)
    return pilImage


def processImageCV(image):

    def smooth(ar):
        p = ar[0]
        for i in range(0, len(ar) - 1):
            n = ar[i + 1]
            np = ar[i]
            ar[i] = p + n / 2
            p = np

    def findThreshold(ar, start, cutOff):
        newArray = []
        for a in ar:
            newArray.append(a[0])

        ar = newArray

        print("Array is " + str(ar))

        sigma = sum(ar)
        total = len(ar)
        average = sigma / total
        print("Average value is " + str(average) + " total " + str(total) + " sigma " + str(sigma))

        smooth(ar)

        limit = start
        while limit < len(ar) and ar[limit] > average * cutOff:
            limit += 1

        return limit

    def findColourNameHSV(hChannel, contour):
        # construct a mask for the contour, then compute the
        # average L*a*b* value for the masked region
        # mask = hChannel.copy()
        mask = numpy.zeros(hChannel.shape[:2], dtype="uint8")
        cv2.drawContours(mask, [contour], -1, 255, -1)
        mask = cv2.erode(mask, None, iterations=2)
        mean = cv2.mean(hChannel, mask=mask)

        maskAnd = hChannel.copy()
        cv2.bitwise_and(hChannel, mask, maskAnd)

        pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(maskAnd, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
        print("Published mask ")

        mean = mean[0]

        hist = cv2.calcHist([hChannel], [0], mask, [255], [0, 255], False)

        histMaxIndex = numpy.argmax(hist)
        # histMax = hist[histMaxIndex]

        print("Got mean as " + str(mean) + " max hist " + str(histMaxIndex))

        value = histMaxIndex

        # initialize the minimum distance found thus far
        # red < 36 > 330 - 18/165
        # yellow >= 45 <= 70 - 22/35
        # green >= 86 <= 155 - 43/176
        # blue >= 180 <= 276 - 90/138
        if value < 22 or value > 145:
            return "red", value
        elif 22 <= value <= 35:
            return "yellow", value
        elif 43 <= value <= 76:
            return "green", value
        elif 90 <= value <= 138:
            return "blue", value
        else:
            return "", value

    def sanitiseContours(cnts):
        MIN_RADUIS = 10
        MIN_AREA = MIN_RADUIS * MIN_RADUIS * math.pi * 0.7

        MAX_AREA = 13000.0

        for i in range(len(cnts) - 1, -1, -1):
            center, radius = cv2.minEnclosingCircle(cnts[i])
            area = cv2.contourArea(cnts[i])
            if radius < MIN_RADUIS or area < MIN_AREA or area > MAX_AREA or center[1] >= 128:
                # print("Deleting contour " + str(i) + " raduis " + str(radius) + " area " + str(area))
                del cnts[i]
            else:
                # print("Keeping contour " + str(i) + " raduis " + str(radius) + " area " + str(area))
                pass

    def findContours(sChannel, vChannel):
        gray = sChannel.copy()
        cv2.addWeighted(sChannel, 0.4, vChannel, 0.6, 0, gray)

        threshHist = cv2.calcHist([gray], [0], None, [256], [0, 256], False)
        threshLimit = findThreshold(threshHist, 60, 0.2)
        print("Calculated threshold " + str(threshLimit))

        # threshLimit = 180

        # thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        thresh = cv2.threshold(gray, threshLimit, 255, cv2.THRESH_BINARY)[1]
        # thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 81, 0)

        # find contours in the thresholded image
        cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[1]

        sanitiseContours(cnts)

        return cnts, thresh

    def adaptiveFindContours(sChannel, vChannel):
        gray = sChannel.copy()
        cv2.addWeighted(sChannel, 0.4, vChannel, 0.6, 0, gray)

        lastMax = 256
        lastMin = 0
        threshLimit = 128

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
            # print("Published gray image")

            if iteration % 1 == 0:
                print("... iteration " + str(iteration) + " min/current/max " + str(lastMin) + "/" + str(threshLimit) + "/" + str(lastMax) + " orig/sanitised " + str(initialCntNum) + "/" + str(len(cnts)))

            if 0 < len(cnts) < 6:
                print("Found good number of areas after " + str(iteration) + " iterations, contours " + str(len(cnts)))
                return cnts, thresh

            if threshLimit < 30 or threshLimit > 220 or lastMax - lastMin < 4:
                print("Failed to find good number of areas after " + str(iteration) + " iterations")
                return cnts, thresh

            if len(cnts) == 0:
                lastMax = threshLimit
                threshLimit = (lastMax + lastMin) / 2
            else:
                lastMin = threshLimit
                threshLimit = (lastMax + lastMin) / 2

    # ratio = image.shape[0] / float(resized.shape[0])

    # blur the resized image slightly, then convert it to both
    # grayscale and the L*a*b* color spaces
    blurred = cv2.GaussianBlur(image, (5, 5), 0)
    # gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
    # lab = cv2.cvtColor(blurred, cv2.COLOR_RGB2LAB)

    hsv = cv2.cvtColor(blurred, cv2.COLOR_RGB2HSV)
    hueChannel, satChannel, valChannel = cv2.split(hsv)

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(hueChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    print("Published hue channel image")

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(valChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    print("Published value channel image")

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(satChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    print("Published saturation channel image")

    countours, threshold = adaptiveFindContours(satChannel, valChannel)

    treshback = cv2.cvtColor(threshold, cv2.COLOR_GRAY2RGB)
    cv2.drawContours(treshback, countours, -1, (0, 255, 0), 2)

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(threshold, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    print("Published gray image")

    pil = PIL.Image.fromarray(treshback)
    pyroslib.publish("overtherainbow/processed", pil.tobytes("raw"))
    print("Published threshold image")

    results = []

    print("Have " + str(len(countours)) + " contours")
    for c in countours:
        # initialize the shape detector and color labeler
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.04 * peri, True)
        # if len(approx) > 5:
        #     # circle
        #

        cntrCenter, cntrRadius = cv2.minEnclosingCircle(c)

        # colourName, extraInfo = findColourNameLAB(lab, c)
        colourName, extraInfo = findColourNameHSV(hueChannel, c)

        if len(colourName) > 0:
            results.append((cntrCenter[0], cntrCenter[1], colourName, cntrRadius, str(extraInfo)))

    return results


def processImage(image):

    red_pixels = []
    green_pixels = []
    blue_pixels = []
    yellow_pixels = []

    for y in range(0, 256):
        for x in range(0, 320):
            p = image.getpixel((x, y))
            if isRed(p):
                red_pixels.append((x, y))
            if isGreen(p):
                green_pixels.append((x, y))
            if isBlue(p):
                blue_pixels.append((x, y))
            if isYellow(p):
                yellow_pixels.append((x, y))

    results = []

    if len(red_pixels) > 20:
        centre = calculateCentre(red_pixels)
        results.append((centre[0], centre[1], "red", 5))

        drawSpot(image, centre[0], centre[1], (255, 64, 64), "red")

    if len(green_pixels) > 20:
        centre = calculateCentre(green_pixels)
        results.append((centre[0], centre[1], "green", 5))

        drawSpot(image, centre[0], centre[1], (64, 255, 64), "green")

    if len(blue_pixels) > 20:
        centre = calculateCentre(blue_pixels)
        results.append((centre[0], centre[1], "blue", 5))

        drawSpot(image, centre[0], centre[1], (64, 64, 255), "blue")

    if len(yellow_pixels) > 20:
        centre = calculateCentre(yellow_pixels)
        results.append((centre[0], centre[1], "yellow", 5))

        drawSpot(image, centre[0], centre[1], (255, 255, 64), "yellow")

    return results


def isRed(p):
    return p[0] > 64 and distance(p[0], p[1]) > 1.2 and distance(p[0], p[1]) > 1.2 and 0.8 < distance(p[1], p[2]) < 1.2


def isGreen(p):
    return p[1] > 64 and distance(p[1], p[0]) > 1.2 and distance(p[1], p[2]) > 1.2 and 0.8 < distance(p[0], p[2]) < 1.2


def isBlue(p):
    return p[2] > 64 and distance(p[2], p[0]) > 1.2 and distance(p[2], p[1]) > 1.2 and 0.8 < distance(p[0], p[1]) < 1.2


def isYellow(p):
    return p[0] > 64 and p[1] > 128 and 0.8 < distance(p[0], p[1]) < 1.2 and distance(p[0], p[2]) > 1.2 and distance(p[1], p[2]) > 1.2


def distance(x, y):
    if y != 0:
        return x / y
    else:
        return x / 256


def calculateCentre(pixels):
    cx = 0
    cy = 0
    for p in pixels:
        cx = cx + p[0]
        cy = cy + p[1]

    cx = int(cx / len(pixels))
    cy = int(cy / len(pixels))
    return cx, cy


def drawSpot(image, cx, cy, colour, text):
    # if False:
    #     for x in range(cx - 30, cx + 30):
    #         if x >= 0 and x < 320:
    #             if cy > 0:
    #                 image.putpixel((x, cy - 1), (255, 255, 255))
    #             image.putpixel((x, cy), colour)
    #             if cy < 256 - 1:
    #                 image.putpixel((x, cy + 1), (255, 255, 255))
    #     for y in range(cy - 30, cy + 30):
    #         if y >= 0 and y < 256:
    #             if cx > 0:
    #                 image.putpixel((cx - 1, y), (255, 255, 255))
    #             image.putpixel((cx, y), colour)
    #             if cx < 320 - 1:
    #                 image.putpixel((cx + 1, y), (255, 255, 255))
    pass


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
