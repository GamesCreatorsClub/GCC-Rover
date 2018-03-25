
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

stroboTime = -1
nextTime = time.time()
state = False


FORWARD_SPEED = 30
MINIMUM_FORWARD_SPEED = 20
TURN_SPEED = 50
ROTATE_SPEED = 60

SPEEDS_ROVER_2 = [-20, -20, -20, -15, -10, -9, 9, 10, 12, 15, 20, 30, 30]
SPEEDS_ROVER_4 = [-20, -20, -20, -15, -14, -14, 30, 30, 35, 40, 35, 40, 40]
SPEEDS = SPEEDS_ROVER_2
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
EPSILON_ANGLE = 2

readingDistanceContinuous = True
readingGyroContinuous = True
renewContinuous = time.time()
digestTime = time.time()

size = (320, 256)

lastProcessed = time.time()


def setAlgorithm(alg):
    global algorithm
    algorithm = alg


def connected():
    pyroslib.publish("sensor/gyro/continuous", "calibrate,50")

    pyroslib.publish("camera/processed/fetch", "")
    pyroslib.publish("camera/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")


def handleDistances(topic, message, groups):
    global historyDistancesDeg1, historyDistancesDeg2, historyDistances1, historyDistances2, historyDistanceTimes1, historyDistanceTimes2
    global distanceDeg1, distanceDeg2, distance1, distance2, avgDistance1, avgDistance2, distanceTimestamp, deltaDistance1, deltaDistance2

    n = time.time()

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
        avgDistance1 = 0

    if len(historyDistances2) > 0:
        avgDistance2 = sum(historyDistances2) / len(historyDistances2)
    else:
        avgDistance2 = 0

    if len(historyDistances1) > 1:
        deltaDistance1 = distance1 - historyDistances1[len(historyDistances1) - 2]
    else:
        deltaDistance1 = 0

    if len(historyDistances2) > 1:
        deltaDistance2 = distance2 - historyDistances2[len(historyDistances2) - 2]
    else:
        deltaDistance2 = 0


def handleGyroData(topic, message, groups):
    global gyroAngle, gyroDeltaAngle

    data = message.split(",")

    gyroChange = float(data[2])

    gyroDeltaAngle = gyroChange

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


def calculateSpeed(speed):
    speedIndex = int(speed * SPEEDS_OFFSET + SPEEDS_OFFSET)
    speed = SPEEDS[speedIndex]
    return speed

def steer(distance=0, speed=FORWARD_SPEED):
    pyroslib.publish("move/steer", str(distance) + " " + str(speed))


def drive(angle=0, speed=FORWARD_SPEED):
    pyroslib.publish("move/drive", str(angle) + " " + str(speed))


def driveForward(speed=FORWARD_SPEED):
    pyroslib.publish("move/drive", "0 " + str(speed))


def driveBack(speed=FORWARD_SPEED):
    pyroslib.publish("move/drive", "0 " + str(-speed))


def rotateLeft(speed):
    pyroslib.publish("move/rotate", str(-speed))


def rotateRight(speed):
    pyroslib.publish("move/rotate", str(speed))


def requestDistanceAtAngle(angle):
    pyroslib.publish("sensor/distance/deg", str(angle))


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


countDown = 0
drive_speed = 0


def log(msg):
    tnow = time.time()
    deltaTime = str((tnow - distanceTimestamp) * 1000) + "ms"
    print(str(str(int(tnow * 1000) % 10000000)) + ": D:" + deltaTime + " 1:" + str(distance1) + " 2:" + str(distance2) + " d1:" + str(deltaDistance1) + " d2:" + str(deltaDistance2) + " " + msg)


def algorithm1Start():
    global drive_speed
    log("started algorithm 1...")
    drive_speed = FORWARD_SPEED
    setAlgorithm(algorithm1Loop)


def algorithm1Loop():
    global countDown, drive_speed
    # go to the corner
    stopAt = 130
    slowAt = 180
    if avgDistance1 + deltaDistance1 * 4 < slowAt or avgDistance2 + deltaDistance2 * 4 < slowAt:
        drive_speed = MINIMUM_FORWARD_SPEED
        log("Slowing down")
    else:
        drive_speed = FORWARD_SPEED
        log("Speeding up")

    if distance1 + deltaDistance1 * 4 < stopAt and distance2 + deltaDistance2 * 4 < stopAt:
        log("Need to brake")
        countDown = 15
        setAlgorithm(brake)
        return
    elif abs(distance1 - distance2) > 10:
        if distance1 > distance2:
            log("Left")
            drive(30, drive_speed)
        else:
            log("Right")
            drive(-30, drive_speed)
        # if lastDrive != "30" and distance1 > distance2:
        #     drive(30)
        #     lastDrive = "30"
        # elif lastDrive != "-30" and distance2 > distance1:
        #     drive(-30)
        #     lastDrive = "-30"
    else:
        log("Forward")
        driveForward(drive_speed)


def brake():
    global countDown

    countDown -= 1

    if countDown < -50:
        setAlgorithm(stop)
    elif countDown < 0:
        stopDriving()
        log("Stopped for " + str(countDown))
    else:
        log("Breaking for " + str(countDown))
        driveBack(50)


def followSide(forwardDistance, forwardDelta, sideDistance, sideDelta, direction):
    distanceControl = STOP_DISTANCE * 4

    if forwardDistance < STOP_DISTANCE:
        stop()
        setAlgorithm(stop)
    else:
        outputForward = (forwardDistance - STOP_DISTANCE) * KP + forwardDelta * KD

        outputForward = normalise(outputForward, distanceControl)

        speed = calculateSpeed(outputForward)
        speedIndex = 0

        if sideDistance > 90 or abs(sideDelta) < 2:
            outputSide = (sideDistance - SIDE_DISTANCE) * KP + sideDelta * KD
            outputSide = -normalise(outputSide, SIDE_DISTANCE)

            angle = outputSide * 80 * direction
            if abs(angle) > 50:
                log("TURN1 d:" + str(round(outputForward, 2)) + " i:" + str(speedIndex) + " s:" + str(speed) + " sd:" + str(angle))
                steer(angle * 10, speed)
            else:
                log("STRAIGHT d:" + str(round(outputForward, 2)) + " i:" + str(speedIndex) + " s:" + str(speed) + " a:" + str(angle))
                drive(angle, speed)
        else:
            steerDistance = -direction * int(math.log10(abs(sideDelta)) * STEERING_DISTANCE) * sign(sideDelta)

            log("TURN2 d:" + str(round(outputForward, 2)) + " i:" + str(speedIndex) + " s:" + str(speed) + " sd:" + str(steerDistance))
            steer(steerDistance, speed)


def algorithm2Start():
    print("started algorithm 2...")
    requestDistanceAtAngle("0")
    setAlgorithm(algorithm2Loop)


def algorithm2Loop():
    distanceControl = STOP_DISTANCE * KC

    followSide(distance1, deltaDistance1, distance2, deltaDistance2, 1)
    #
    # if distance1 < STOP_DISTANCE:
    #     stop()
    #     setAlgorithm(stop)
    # else:
    #     outputForward = (distance1 - STOP_DISTANCE) * KP + deltaDistance1 * KD
    #
    #     outputForward = normalise(outputForward, distanceControl)
    #
    #     speedIndex = int(outputForward * SPEEDS_OFFSET + SPEEDS_OFFSET)
    #     speed = SPEEDS[speedIndex]
    #
    #     if deltaDistance2 < 10:
    #         outputSide = (distance2 - SIDE_DISTANCE) * KP + deltaDistance2 * KD
    #         outputSide = -normalise(outputSide, SIDE_DISTANCE)
    #
    #         angle = outputSide * 20
    #
    #         log("STRAIGHT d:" + str(round(outputForward, 2)) + " i:" + str(speedIndex) + " s:" + str(speed) + " a:" + str(angle))
    #         drive(angle, speed)
    #     else:
    #         distance = -int(math.log10(abs(deltaDistance2)) * 400) * sign(deltaDistance2)
    #
    #         log("TURN d:" + str(round(outputForward, 2)) + " i:" + str(speedIndex) + " s:" + str(speed) + " sd:" + str(distance))
    #         steer(distance, speed)


def algorithm3Start():
    print("started algorithm 3...")
    requestDistanceAtAngle("90")
    driveForward(FORWARD_SPEED)
    setAlgorithm(algorithm3Loop)


def algorithm3Loop():
    distanceControl = STOP_DISTANCE * KC

    followSide(distance2, deltaDistance2, distance1, deltaDistance1, -1)


def algorithm4Start():
    driveForward(FORWARD_SPEED)
    print("started algorithm 4...")
    driveForward()
    setAlgorithm(algorithm4Loop)


def algorithm4Loop():
    if distance1 - deltaDistance1 < STOP_DISTANCE:
        stopDriving()
        setAlgorithm(stop)
    else:
        output = (distance1 - STOP_DISTANCE) / STOP_DISTANCE * 0.7 - deltaDistance1 * 0.3
        if output > 1:
            output = 1

        speedIndex = int(output * SPEEDS_OFFSET * 2)
        speed = SPEEDS[speedIndex]
        log("d:" + str(round(output, 2)) + " i:" + str(speedIndex) + " s:" + str(speed))
        drive(0, speed)


start_angle = 0
previous_error = 0

AKP = 0.7
AKD = 0.3


def rotateForAngleRight(a):
    global previous_error
    if gyroAngle < start_angle + (a - EPSILON_ANGLE):
        error = gyroAngle - (start_angle + a)
        deltaError = error - previous_error
        previous_error = error

        # deltaError = gyroDeltaAngle
        control = error * AKP + deltaError * AKD

        control = normalise(control, a)

        speed = calculateSpeed(-control)
        rotateRight(speed)
    else:
        stop()
        setAlgorithm(stop)


def rotateForAngleLeft(a):
    global previous_error
    if gyroAngle > start_angle - (a - EPSILON_ANGLE):

        error = gyroAngle - (start_angle - a)
        deltaError = previous_error - error
        previous_error = error

        # deltaError = gyroDeltaAngle
        control = error * AKP + deltaError * AKD

        control = normalise(control, a)

        speed = calculateSpeed(control)

        rotateLeft(speed)
    else:
        stop()
        setAlgorithm(stop)

def algorithm5Start():
    global start_angle, previous_error
    previous_error = 0

    print("started algorithm 5...")
    setAlgorithm(algorithm5Loop)
    start_angle = gyroAngle


def algorithm5Loop():
    rotateForAngleLeft(90)


def algorithm6Start():
    global start_angle
    print("started algorithm 6...")
    setAlgorithm(algorithm6Loop)
    start_angle = gyroAngle


def algorithm6Loop():
    rotateForAngleRight(86)


def algorithm7Start():
    global start_angle, previous_error
    previous_error = 0

    print("started algorithm 7...")
    setAlgorithm(algorithm7Loop)
    start_angle = gyroAngle


def algorithm7Loop():
    rotateForAngleLeft(135)


def algorithm8Start():
    global start_angle
    print("started algorithm 8...")
    setAlgorithm(algorithm8Loop)
    start_angle = gyroAngle


def algorithm8Loop():
    rotateForAngleRight(135)


KP = 0.8
KI = 0.0
KD = 0.2
KC = 2
KA = 20
STOP_DISTANCE = 120
SIDE_DISTANCE = 120
STEERING_DISTANCE = 400

previous_error = 0
integral = 0


def algorithm9Start():
    global drive_speed

    print("started algorithm 9...")
    requestDistanceAtAngle("45")
    drive_speed = FORWARD_SPEED
    setAlgorithm(algorithm9Loop)


def algorithm9Loop():
    global countDown, drive_speed

    distanceControl = STOP_DISTANCE * KC

    if distance1 + distance2 < STOP_DISTANCE * 2:
        stop()
        setAlgorithm(stop)
    else:

        if abs(distance1 - distance2) > 1 and distance1 < 380 and distance2 < 380:
            angle = int(math.log10(abs(distance1 - distance2)) * KA) * sign(distance1 - distance2)
        else:
            angle = 0

        output = (distance1 + distance2 - STOP_DISTANCE * 2) * KP + (deltaDistance1 + deltaDistance2) * KD

        output = normalise(output, distanceControl)

        speedIndex = int(output * SPEEDS_OFFSET + SPEEDS_OFFSET)
        speed = SPEEDS[speedIndex]
        log("d:" + str(round(output, 2)) + " i:" + str(speedIndex) + " s:" + str(speed) + " a:" + str(angle))
        drive(angle, speed)


def algorithm10Start():
    global countDown
    print("started algorithm 10...")
    countDown = 50
    driveBack(FORWARD_SPEED)
    setAlgorithm(algorithm10Loop)


def algorithm10Loop():
    global countDown
    countDown -= 1
    if countDown <= 0:
        setAlgorithm(stop)


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


colorNames = ["red", "green", "blue", "yellow"]
labColours = numpy.zeros((4, 1, 3), dtype="uint8")
labColours[0] = (255, 0, 0)
labColours[1] = (0, 255, 0)
labColours[2] = (0, 0, 255)
labColours[3] = (255, 255, 0)
labColours = cv2.cvtColor(labColours, cv2.COLOR_RGB2LAB)

print("Lab colours")
for labColour in labColours:
    print(str(labColour))


def processImageCV(image):

    def eucleadianDistance(v1, v2):
        res = 0
        for index in range(0, len(v1)):
            d = v1[index] - v2[index]
            res = res + (d * d)

        try:
            return math.sqrt(res)
        except BaseException as e:
            print("Error : " + str(res) + " " + str(e))

    def findColourNameLAB(lab, c):
        # construct a mask for the contour, then compute the
        # average L*a*b* value for the masked region
        mask = numpy.zeros(lab.shape[:2], dtype="uint8")
        cv2.drawContours(mask, [c], -1, 255, -1)
        mask = cv2.erode(mask, None, iterations=2)
        mean = cv2.mean(lab, mask=mask)[:3]

        # initialize the minimum distance found thus far
        minDist = (numpy.inf, None)

        # loop over the known L*a*b* color values
        for (i, row) in enumerate(labColours):
            # compute the distance between the current L*a*b*
            # color value and the mean of the image
            # d = scipy.spatial.distance.euclidean(row[0], mean)
            d = eucleadianDistance(row[0], mean)

            # if the distance is smaller than the current distance,
            # then update the bookkeeping variable
            if d < minDist[0]:
                minDist = (d, i)

        # return the name of the color with the smallest distance
        return colorNames[minDist[1]], mean

    def findColourNameHSV(hChannel, c):
        # construct a mask for the contour, then compute the
        # average L*a*b* value for the masked region
        # mask = hChannel.copy()
        mask = numpy.zeros(hChannel.shape[:2], dtype="uint8")
        cv2.drawContours(mask, [c], -1, 255, -1)
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

    # ratio = image.shape[0] / float(resized.shape[0])

    # blur the resized image slightly, then convert it to both
    # grayscale and the L*a*b* color spaces
    blurred = cv2.GaussianBlur(image, (5, 5), 0)
    # gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
    lab = cv2.cvtColor(blurred, cv2.COLOR_RGB2LAB)

    hsv = cv2.cvtColor(blurred, cv2.COLOR_RGB2HSV)
    hChannel, sChannel, vChannel = cv2.split(hsv)

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(hChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    print("Published hue channel image")

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(vChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    print("Published value channel image")

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(sChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    print("Published saturation channel image")

    gray = sChannel.copy()
    cv2.addWeighted(sChannel, 0.2, vChannel, 0.8, 0, gray)

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    print("Published gray image")

    thresh = cv2.threshold(gray, 90, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    # thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2)

    # find contours in the thresholded image
    cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[1]

    MIN_RADUIS = 10
    MIN_AREA = MIN_RADUIS * MIN_RADUIS * math.pi * 0.7

    MAX_AREA = 13000.0

    for i in range(len(cnts) - 1, -1, -1):
        center, radius = cv2.minEnclosingCircle(cnts[i])
        area = cv2.contourArea(cnts[i])
        if radius < MIN_RADUIS or area < MIN_AREA or area > MAX_AREA or center[1] >= 128:
            print("Deleting contour " + str(i) + " raduis " + str(radius) + " area " + str(area))
            del cnts[i]
        else:
            print("Keeping contour " + str(i) + " raduis " + str(radius) + " area " + str(area))

    treshback = cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)
    cv2.drawContours(treshback, cnts, -1, (0, 255, 0), 2)

    pil = PIL.Image.fromarray(treshback)
    pyroslib.publish("overtherainbow/processed", pil.tobytes("raw"))
    print("Published pil image")

    results = []

    print("Have " + str(len(cnts)) + " contours")
    for c in cnts:
        # initialize the shape detector and color labeler
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.04 * peri, True)
        # if len(approx) > 5:
        #     # circle
        #

        center, radius = cv2.minEnclosingCircle(c)

        if radius > 10:
            # colourName, extraInfo = findColourNameLAB(lab, c)
            colourName, extraInfo = findColourNameHSV(hChannel, c)

            if len(colourName) > 0:
                results.append((center[0], center[1], colourName, radius, str(extraInfo)))

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
    if False:
        for x in range(cx - 30, cx + 30):
            if x >= 0 and x < 320:
                if cy > 0:
                    image.putpixel((x, cy - 1), (255, 255, 255))
                image.putpixel((x, cy), colour)
                if cy < 256 - 1:
                    image.putpixel((x, cy + 1), (255, 255, 255))
        for y in range(cy - 30, cy + 30):
            if y >= 0 and y < 256:
                if cx > 0:
                    image.putpixel((cx - 1, y), (255, 255, 255))
                image.putpixel((cx, y), colour)
                if cx < 320 - 1:
                    image.putpixel((cx + 1, y), (255, 255, 255))


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

    if time.time() > digestTime:
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
