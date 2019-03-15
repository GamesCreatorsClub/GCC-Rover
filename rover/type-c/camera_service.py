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
import storagelib
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


continuousIterator = None

stream = io.BytesIO()
camera = None
continuousOutput = None

doReadSensor = False
continuousMode = False
lastTimeRead = 0
lastTimeReceivedRequestForContMode = 0

startTime = time.time()
lastTime = time.time()

imageFormat = 'BW'
size = (80, 64)
adjustedSize = (96, 64)
postProcess = False


def initCamera():
    global whiteBalance, camera, singleOutput, continuousOutput

    whiteBalance = Image.new("L", size)

    if camera is not None:
        print("  Closing existing camera.")
        camera.close()

    print("  Initialising camera, size " + str(size))
    camera = PiCamera(resolution=size, framerate=10)
    camera.resolution = size
    # camera.shutter_speed = 3000
    camera.iso = 800
    camera.hflip = False
    camera.vflip = False
    if pyroslib.getClusterId().startswith("camera"):
        camera.rotation = 90

    singleOutput = np.empty((adjustedSize[0], adjustedSize[1], 3), dtype=np.uint8)

    if imageFormat == 'HSV':
        continuousOutput = PiRGBArray(camera, size=adjustedSize)
    elif imageFormat == 'BW' or imageFormat == 'RGB':
        continuousOutput = PiRGBArray(camera, size=adjustedSize)


initCamera()


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
    global continuousIterator

    rawRGB = None

    if continuousMode:
        next(continuousIterator)
        logt("        capture")
        # print('Captured %dx%d image' % (
        #     continuousOutput.array.shape[1], continuousOutput.array.shape[0]))
        if imageFormat == 'RGB' or imageFormat == 'BW':
            rawRGB = Image.frombuffer('RGB', adjustedSize, continuousOutput.array, 'raw', 'RGB', 0, 1).crop((0, 0, size[0], size[1]))
            logt("        Image.open(stream)")
        elif imageFormat == 'HSV':
            rawRGB = Image.frombuffer('HSV', adjustedSize, continuousOutput.array, 'raw', 'HSV', 0, 1).crop((0, 0, size[0], size[1]))
            logt("        Image.open(stream)")
        continuousOutput.truncate(0)

    else:
        stream.seek(0)
        logt("        seek(0)")
        if imageFormat == 'RGB' or imageFormat == 'BW':
            camera.capture(singleOutput, "rgb", use_video_port=True)
            logt("        capture")
            rawRGB = Image.frombuffer('RGB', size, singleOutput, 'raw', 'RGB', 0, 1)
            logt("        Image.open(stream)")
        elif imageFormat == 'HSV':
            camera.capture(singleOutput, "hsv", use_video_port=True)
            logt("        capture")
            rawRGB = Image.frombuffer('HSV', size, singleOutput, 'raw', 'HSV', 0, 1)
            logt("        Image.open(stream)")

    if imageFormat == 'RGB':
        return rawRGB
    elif imageFormat == 'BW':
        rawL = rawRGB.convert("L")
        logt("        convert(L)")
        return rawL
    elif imageFormat == 'HSV':
        return None


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


def handleRaw(topic, payload, groups):
    log("  Asked to fetch raw image.")
    fetchRaw()


def handleFetchProcessed(topic, payload, groups):
    log("  Asked to fetch processed image.")
    fetchProcessed()


def fetchRaw():
    captured = capture()

    message = captured.tobytes("raw")
    if pyroslib.getClusterId() != "master":
        pyroslib.publish("camera/" + pyroslib.getClusterId() + "/raw", message)
    else:
        pyroslib.publish("camera/raw", message)
    # log("  Sent raw image.")


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
            if imageFormat == 'RGB' or imageFormat == 'BW':
                continuousIterator = camera.capture_continuous(continuousOutput, format="rgb", resize=adjustedSize, use_video_port=False, burst=True)
            elif imageFormat == 'HSV':
                continuousIterator = camera.capture_continuous(continuousOutput, format="hsv", resize=adjustedSize, use_video_port=False, burst=True)
            print("  Started continuous mode...")

        lastTimeReceivedRequestForContMode = time.time()


def handleFormat(topic, message, groups):
    global imageFormat, postProcess, size, adjustedSize

    split = message.split(" ")
    if len(split) > 0:
        imageFormat = split[0]
    if len(split) > 1:
        widthHeight = split[1].split(",")
        if len(widthHeight) > 1:
            size = (int(widthHeight[0]), int(widthHeight[1]))
            adjustedSize = (int(size[0] * 1.2), size[1])
    if len(split) > 2:
        postProcess = split[2].lower() in ["true", "t", "1", "yes"]

    print("  Got format " + imageFormat + " " + str(size[0]) + "," + str(size[1]) + " " + str(postProcess))

    initCamera()


def loop():
    global doReadSensor, lastTimeRead, continuousMode
    if doReadSensor:
        if postProcess:
            fetchProcessed()
        else:
            fetchRaw()
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

        pyroslib.init("camera-service", unique=True)

        if pyroslib.getClusterId() != "master":
            prefix = "camera/" + pyroslib.getClusterId() + "/"
            print("  Running as a slave - setting topic prefix to " + prefix)
        else:
            prefix = "camera/"
            print("  Running as master - setting topic prefix to " + prefix)

        pyroslib.subscribe(prefix + "raw/fetch", handleRaw)
        pyroslib.subscribe(prefix + "processed/fetch", handleFetchProcessed)
        pyroslib.subscribe(prefix + "whitebalance/fetch", fetchWhiteBalance)
        pyroslib.subscribe(prefix + "whitebalance/store", storeWhiteBalance)
        pyroslib.subscribe(prefix + "continuous", handleContinuousMode)
        pyroslib.subscribe(prefix + "format", handleFormat)

        print("Started camera service.")

        pyroslib.forever(0.05, loop, loop_sleep=0.04)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
