
#
# Copyright 2016-2018 Games Creators Club
#
# MIT License
#

import math
import time
import traceback

import numpy

import cv2
import PIL
import PIL.Image
from PIL import Image
from PIL import ImageDraw

import pyroslib
import pyroslib.logging

from pyroslib.logging import log, LOG_LEVEL_INFO

stopped = True

remotDebug = True

size = (80, 64)


lastProcessed = time.time()


foundColours = {"red": None, "blue": None, "yellow": None, "green": None}
cvResults = None


def connected():
    pyroslib.publish("camera/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")
    pyroslib.publish("camera/wheels/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")
    pyroslib.publish("camera/camera1/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")
    pyroslib.publish("camera/camera2/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")


def handleOverTheRainbow(topic, message, groups):
    data = message.split(" ")

    cmd = data[0]
    log(LOG_LEVEL_INFO, "Got comamnd " + str(cmd))

    if cmd == "stop":
        stop()
    elif cmd == "scan":
        scan()


def stop():
    global stopped
    stopped = True
    log(LOG_LEVEL_INFO, "Stopped!")


def scan():
    global stopped
    stopped = False
    log(LOG_LEVEL_INFO, "Started scanning...")
    foundColours["red"] = None
    foundColours["blue"] = None
    foundColours["yellow"] = None
    foundColours["green"] = None

    pyroslib.publish("camera/raw/fetch", "")
    pyroslib.publish("camera/wheels/raw/fetch", "")
    pyroslib.publish("camera/camera1/raw/fetch", "")
    pyroslib.publish("camera/camera2/raw/fetch", "")


def handleCameraRawData(topic, message, source):
    global lastProcessed, stopped

    def foundToString():
        return " ".join([k + ":" + ("" if v is None else v) for k, v in foundColours.items()])

    now = time.time()
    delta = now - lastProcessed
    lastProcessed = now

    pilImage = toPILImage(message)
    openCVImage = numpy.array(pilImage)

    result, value = processImageCV(openCVImage)

    log(LOG_LEVEL_INFO, "For " + str(source) + " got " + ("None" if result is None else str(result)) + " for value " + str(value))

    if result is not None:
        foundColours[result] = source

    missing_colour = ""
    finished = True
    for colour in foundColours:
        if foundColours[colour] is None:
            finished = False
            missing_colour = colour

    if not finished:
        log(LOG_LEVEL_INFO, "So far " + foundToString() + " but not finished yet as at least " + missing_colour + " is still missing.")
        if not stopped:
            pyroslib.publish(topic + "/fetch", "")
        pyroslib.publish("nebula/imagedetails", "working: " + foundToString())
    else:
        log(LOG_LEVEL_INFO, "So far " + foundToString() + " and finishing...")
        stopped = True
        pyroslib.publish("nebula/imagedetails", "found: " + foundToString())


def handleCameraRaw(topic, message, groups):
    handleCameraRawData(topic, message, "main")


def handleCameraWheelsRaw(topic, message, groups):
    handleCameraRawData(topic, message, "wheels")


def handleCamera1Raw(topic, message, groups):
    handleCameraRawData(topic, message, "camera1")


def handleCamera2Raw(topic, message, groups):
    handleCameraRawData(topic, message, "camera2")


def toPILImage(imageBytes):
    pilImage = PIL.Image.frombytes("RGB", size, imageBytes)
    return pilImage


def processImageCV(image):
    global cvResults

    def findColourNameHSV(hChannel, contour):

        mask = numpy.zeros(hChannel.shape[:2], dtype="uint8")
        cv2.drawContours(mask, [contour], -1, 255, -1)
        mask = cv2.erode(mask, None, iterations=2)

        maskAnd = hChannel.copy()
        cv2.bitwise_and(hChannel, mask, maskAnd)

        pyroslib.publish("nebula/processed", PIL.Image.fromarray(cv2.cvtColor(maskAnd, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
        log(LOG_LEVEL_INFO, "Published mask ")

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
            return None, value

    blurred = cv2.GaussianBlur(image, (5, 5), 0)

    hsv = cv2.cvtColor(blurred, cv2.COLOR_RGB2HSV)
    hueChannel, satChannel, valChannel = cv2.split(hsv)

    # pyroslib.publish("nebula/processed", PIL.Image.fromarray(cv2.cvtColor(hueChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    # log(LOG_LEVEL_INFO, "Published hue channel image")
    #
    # pyroslib.publish("nebula/processed", PIL.Image.fromarray(cv2.cvtColor(valChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    # log(LOG_LEVEL_INFO, "Published value channel image")
    #
    # pyroslib.publish("nebula/processed", PIL.Image.fromarray(cv2.cvtColor(satChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    # log(LOG_LEVEL_INFO, "Published saturation channel image")

    countours = [numpy.array([[25, 20], [55, 20], [55, 44], [25, 44]], dtype=numpy.int32)]
    c = countours[0]
    result, value = findColourNameHSV(hueChannel, c)

    if result is not None:

        def sendResult(colour):
            # pil = PIL.Image.fromarray(cv2.cvtColor(hueChannel, cv2.COLOR_GRAY2RGB))
            pil = PIL.Image.fromarray(image)

            draw = ImageDraw.Draw(pil)
            draw.rectangle(((25, 20), (55, 44)), outline=colour)
            pyroslib.publish("nebula/processed", pil.tobytes("raw"))

        if result == "red":
            sendResult("#f00")
            log(LOG_LEVEL_INFO, "Published hue red image")
        elif result == "yellow":
            sendResult("#ff0")
            log(LOG_LEVEL_INFO, "Published hue yellow image")
        elif result == "green":
            sendResult("#0f0")
            log(LOG_LEVEL_INFO, "Published hue green image")
        elif result == "blue":
            sendResult("#00f")
            log(LOG_LEVEL_INFO, "Published hue blue image")
    else:
        cv2.drawContours(hueChannel, countours, -1, (255, 255, 255), 2)

        pyroslib.publish("nebula/processed", PIL.Image.fromarray(cv2.cvtColor(hueChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
        log(LOG_LEVEL_INFO, "Published unrecognised hue image")

    return result, value


def mainLoop():
    thisTime = time.time()


if __name__ == "__main__":
    try:
        print("Starting over-the-rainbow agent...")

        pyroslib.subscribe("nebula/command", handleOverTheRainbow)

        pyroslib.subscribeBinary("camera/raw", handleCameraRaw)
        pyroslib.subscribeBinary("camera/wheels/raw", handleCameraWheelsRaw)
        pyroslib.subscribeBinary("camera/camera1/raw", handleCamera1Raw)
        pyroslib.subscribeBinary("camera/camera2/raw", handleCamera2Raw)

        pyroslib.init("over-the-rainbow-agent", unique=True, onConnected=connected)

        print("Started over-the-rainbow agent.")

        pyroslib.forever(0.02, mainLoop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
