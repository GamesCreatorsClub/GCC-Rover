
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


MIN_RADIUS = 35
MAX_RADIUS = 50
MIN_AREA = MIN_RADIUS * MIN_RADIUS * math.pi * 0.7 / 4.0
MAX_AREA = 13000.0

size = (320, 256)

lastProcessed = time.time()

cvResults = None


def log(level, what):
    if level <= DEBUG_LEVEL:
        print(what)


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
    pyroslib.publish("camera/processed/fetch", "")
    pyroslib.publish("camera/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")


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

    def isCircle(contour):
        def distance(p1, p2):
            return math.sqrt((p1[0] - p2[0]) * (p1[0] - p2[0]) + (p1[1] - p2[1]) * (p1[1] - p2[1]))

        # approx = cv2.approxPolyDP(contour, 0.2 * cv2.arcLength(contour, True), True)
        # if len(approx) < 8:
        #     return False

        # log(DEBUG_LEVEL_ALL, "approx " + str(approx) + " 0=" + str(approx[0][0][0]))
        log(DEBUG_LEVEL_ALL, "contour " + str(contour) + " 0=" + str(contour[0][0][0]))

        cntrCenter, cntrRadius = cv2.minEnclosingCircle(contour)

        good = 0

        for point in contour:
            d = distance(point[0], cntrCenter)
            if d < cntrRadius * 0.8 or d > cntrRadius * 1.2:
                # log(DEBUG_LEVEL_ALL, "d " + str(d) + " cntrRadius " + str(cntrRadius))
                # return False
                pass
            else:
                good +=1

        log(DEBUG_LEVEL_ALL,  "cntrRadius " + str(cntrRadius) + " len " + str(len(contour)) + " good " + str(good))
        return good >= len(contour) * 0.8

    def sanitiseContours(cnts):
        for i in range(len(cnts) - 1, -1, -1):
            center, radius = cv2.minEnclosingCircle(cnts[i])
            area = cv2.contourArea(cnts[i])
            # if radius < MIN_RADIUS or radius > MAX_RADIUS or area < MIN_AREA or area > MAX_AREA or center[1] >= 128:
            if radius < MIN_RADIUS or radius > MAX_RADIUS or area < MIN_AREA or area > MAX_AREA or not isCircle(cnts[i]):
                # log(DEBUG_LEVEL_ALL, "Deleting contour " + str(i) + " RADIUS " + str(radius) + " area " + str(area))
                del cnts[i]
            else:
                # log(DEBUG_LEVEL_ALL, "Keeping contour " + str(i) + " RADIUS " + str(radius) + " area " + str(area))
                pass

    def adaptiveFindContours(grey):

        lastMax = 256
        lastMin = 0
        threshLimit = 225
        # threshLimit = 128

        iteration = 0

        while True:
            thresh = cv2.threshold(grey, threshLimit, 255, cv2.THRESH_BINARY)[1]
            iteration += 1

            # find contours in the thresholded image
            cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = cnts[1]

            initialCntNum = len(cnts)
            sanitiseContours(cnts)

            pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
            # log(DEBUG_LEVEL_ALL, "Published grey image")

            if iteration % 1 == 0:
                log(DEBUG_LEVEL_ALL, "... iteration " + str(iteration) + " min/current/max " + str(lastMin) + "/" + str(threshLimit) + "/" + str(lastMax) + " orig/sanitised " + str(initialCntNum) + "/" + str(len(cnts)))

            if 0 < len(cnts) < 6:
                log(DEBUG_LEVEL_ALL, "Found good number of areas after " + str(iteration) + " iterations, contours " + str(len(cnts)))
                return cnts, thresh

            if threshLimit < 25 or threshLimit > 225 or lastMax - lastMin < 4:
                log(DEBUG_LEVEL_ALL, "Failed to find good number of areas after " + str(iteration) + " iterations")
                return cnts, thresh

            threshLimit -= 15

    blurred = cv2.GaussianBlur(image, (5, 5), 0)

    hsv = cv2.cvtColor(blurred, cv2.COLOR_RGB2HSV)
    hueChannel, satChannel, valChannel = cv2.split(hsv)

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(hueChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    log(DEBUG_LEVEL_ALL, "Published hue channel image")

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(satChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    log(DEBUG_LEVEL_ALL, "Published saturation channel image")

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(valChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    log(DEBUG_LEVEL_ALL, "Published value channel image")

    grey = satChannel.copy()
    # cv2.addWeighted(sChannel, 0.4, vChannel, 0.6, 0, grey)
    cv2.multiply(satChannel, valChannel, grey, 1.0 / 256.0)

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(grey, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    log(DEBUG_LEVEL_ALL, "Published grey image")

    sigma = 0.33
    median = numpy.median(grey)

    # apply automatic Canny edge detection using the computed median
    lower = int(max(0, (1.0 - sigma) * median))
    upper = int(min(255, (1.0 + sigma) * median))

    edges = cv2.Canny(grey, lower, upper)

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    log(DEBUG_LEVEL_ALL, "Published edges image")

    kernel = numpy.ones((3, 3), numpy.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=3)

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(dilated, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    log(DEBUG_LEVEL_ALL, "Published dilated image")

    countours, threshold = adaptiveFindContours(grey)

    treshback = cv2.cvtColor(threshold, cv2.COLOR_GRAY2RGB)
    cv2.drawContours(treshback, countours, -1, (0, 255, 0), 2)

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(threshold, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    log(DEBUG_LEVEL_ALL, "Published grey image")

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
    pass


if __name__ == "__main__":
    try:
        print("Starting open-cv-experiments agent...")

        pyroslib.subscribeBinary("camera/raw", handleCameraRaw)

        pyroslib.init("open-cv-experiments", unique=True, onConnected=connected)

        print("Started open-cv-experiments agent.")

        pyroslib.forever(0.02, mainLoop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
