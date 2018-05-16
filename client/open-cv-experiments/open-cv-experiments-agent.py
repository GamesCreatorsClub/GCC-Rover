
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

    blurred = cv2.GaussianBlur(image, (5, 5), 0)

    hsv = cv2.cvtColor(blurred, cv2.COLOR_RGB2HSV)
    hueChannel, satChannel, valChannel = cv2.split(hsv)

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(hueChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    log(DEBUG_LEVEL_ALL, "Published hue channel image")

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(satChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    log(DEBUG_LEVEL_ALL, "Published saturation channel image")

    pyroslib.publish("overtherainbow/processed", PIL.Image.fromarray(cv2.cvtColor(valChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
    log(DEBUG_LEVEL_ALL, "Published value channel image")

    results = []

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
