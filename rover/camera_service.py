#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import time
import os
import io
import numpy as np
import traceback
import pyroslib
import PIL.ImageOps
import PIL.ImageMath
from PIL import Image, ImageEnhance
from picamera import PiCamera
from picamera.array import PiRGBArray

#
# camera service
#
# This service is fetching picture from camera...
#

DEBUG = False
CONTINUOUS_MODE_TIMEOUT = 5  # 5 seconds before giving up on sending accel data out
MAX_TIMEOUT = 0.05  # 0.02 is 50 times a second so this is 50% longer


whiteBalance = Image.new("L", (80, 64))

camera = PiCamera(resolution=(80, 64), framerate=10)
camera.resolution = (80, 64)
# camera.shutter_speed = 3000
camera.iso = 800
camera.hflip = False
camera.vflip = False

singleOutput = np.empty((96, 64, 3), dtype=np.uint8)
continuousOutput = PiRGBArray(camera, size=(96, 64))

continuousIterator = None

stream = io.BytesIO()

doReadSensor = False
continuousMode = False
lastTimeRead = 0
lastTimeReceivedRequestForContMode = 0

rawL = None
rawRGB = None
startTime = time.time()
lastTime = time.time()


def log(msg):
    if DEBUG:
        print(msg)


def logt(msg):
    global lastTime
    if DEBUG:
        now = time.time()
        print("{0!s:>10} {1} Lasted {2}s".format(str(round(now - startTime, 4)), msg, str(round(now - lastTime, 4))))
        lastTime = now


def capture():
    global rawL, rawRGB, continuousIterator

    if continuousMode:
        next(continuousIterator)
        logt("        capture")
        # print('Captured %dx%d image' % (
        #     continuousOutput.array.shape[1], continuousOutput.array.shape[0]))
        rawRGB = Image.frombuffer('RGB', (96, 64), continuousOutput.array, 'raw', 'RGB', 0, 1).crop((0, 0, 80, 64))
        logt("        Image.open(stream)")
        continuousOutput.truncate(0)

    else:
        stream.seek(0)
        logt("        seek(0)")
        camera.capture(singleOutput, "rgb", use_video_port=True)
        logt("        capture")
        rawRGB = Image.frombuffer('RGB', (80, 64), singleOutput, 'raw', 'RGB', 0, 1)
        logt("        Image.open(stream)")

    rawL = rawRGB.convert("L")
    logt("        convert(L)")
    return rawL


def minLevel(histogram, level):
    for i in range(0, len(histogram)):
        if histogram[i] > level:
            return i
    return 0


def maxLevel(histogram, level):
    for i in range(len(histogram) - 1, 0, -1):
        if histogram[i] > level:
            return i
    return len(histogram) - 1


def limit(pixel, minPix, maxPix):
    if pixel > maxPix:
        pixel = maxPix
    if pixel < minPix:
        pixel = minPix
    return pixel


def applyWhiteBalance(img, wb):
    # histogram = img.histogram()
    #
    # minP = minLevel(histogram, 20)
    # maxP = maxLevel(histogram, 20)
    iwb = PIL.ImageOps.invert(wb)
    imgAC = PIL.ImageOps.autocontrast(img)

    res = PIL.ImageMath.eval("a+b", a=imgAC, b=iwb)

    return res.convert("L")


def applyWhiteBalance2(img, wb):
    histogram = img.histogram()

    minP = minLevel(histogram, 20)
    maxP = maxLevel(histogram, 20)

    for y in range(0, 64):
        for x in range(0, 80):
            wbp = wb.getpixel((x, y))
            wbp = limit(wbp, minP, maxP)

            p = img.getpixel((x, y))
            offset = ((maxP - wbp) - minP)

            p += offset
            if p > 255:
                p = 255
            img.putpixel((x, y), p)

    return img


def blackAndWhite(img):
    for y in range(0, 64):
        for x in range(0, 80):
            p = img.getpixel((x, y))
            if p > 127:
                p = 255
            else:
                p = 0
            img.putpixel((x, y), p)

    return img


def fetchRaw(topic, payload, groups):
    captured = capture()

    log("  Asked to fetch raw image.")
    message = captured.tobytes("raw")
    pyroslib.publish("camera/raw", message)
    log("  Sent raw image.")


def handleFetchProcessed(topic, payload, groups):
    log("  Asked to fetch processed image.")
    fetchProcessed()


def fetchProcessed():
    global startTime, lastTime

    startTime = time.time()
    lastTime = startTime
    logt("    Capturing image...")
    captured = capture()
    logt("    Captured image.")

    img = applyWhiteBalance(captured, whiteBalance)
    logt("    Processed white balance.")

    contrast = ImageEnhance.Contrast(img)
    finalImg = contrast.enhance(10)
    logt("    Processed contrast.")

    finalImg = blackAndWhite(finalImg)
    logt("    Set to black and white.")

    message = finalImg.tobytes("raw")
    logt("    Converted to bytes.")

    pyroslib.publish("camera/processed", message)
    logt("    Published.")

    if DEBUG:
        print("  Sent processed image. Total time " + str(time.time() - startTime) + "s")


def fetchWhiteBalance(topic, payload, groups):
    print("  Asked to fetch white-balance image.")
    message = whiteBalance.tobytes("raw")
    pyroslib.publish("camera/whitebalance", message)
    print("  Sent white-balance image.")


def storeWhiteBalance(topic, payload, groups):
    global whiteBalance

    captured = capture()
    captured.save("white-balance.png", "PNG")
    whiteBalance = captured


def handleContinuousMode(topic, message, groups):
    global doReadSensor, continuousMode, lastTimeReceivedRequestForContMode, continuousIterator

    if message.startswith("stop"):
        continuousMode = False
        doReadSensor = False
        camera.stop_preview()
        print("  Stopped continuous mode...")

    else:
        if not continuousMode:
            continuousMode = True
            doReadSensor = True
            continuousOutput.truncate(0)
            continuousIterator = camera.capture_continuous(continuousOutput, format="rgb", resize=(96,64), use_video_port=False, burst=True)
            print("  Started continuous mode...")

        lastTimeReceivedRequestForContMode = time.time()


def loop():
    global doReadSensor, lastTimeRead, continuousMode

    if doReadSensor:
        fetchProcessed()
        if continuousMode:
            if time.time() - lastTimeReceivedRequestForContMode > CONTINUOUS_MODE_TIMEOUT:
                continuousMode = False
                camera.stop_preview()
                print("  Stopped continuous mode.")
        else:
            doReadSensor = False


if __name__ == "__main__":
    try:
        print("Starting camera service...")

        if os.path.exists("white-balance.png"):
            print("  Loading previously stored white-balance.png...")
            whiteBalance = Image.open("white-balance.png")
            whiteBalance = whiteBalance.convert('L')

        pyroslib.subscribe("camera/raw/fetch", fetchRaw)
        pyroslib.subscribe("camera/processed/fetch", handleFetchProcessed)
        pyroslib.subscribe("camera/whitebalance/fetch", fetchWhiteBalance)
        pyroslib.subscribe("camera/whitebalance/store", storeWhiteBalance)
        pyroslib.subscribe("camera/continuous", handleContinuousMode)
        pyroslib.init("camera-service")

        print("Started camera service.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
