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


IDLE = 0
UP = 1
DOWN = 2
RESET = 3

DIRECTIONS = ["IDLE", "UP", "DOWN", "RESET"]

status = "Idle"

S1_FRONT = 60
S1_MID = 161
S1_BACK = 260

S2_DOWN = 175
S2_MID = 140
S2_UP = 74

direction = RESET
stage = 0
s1_pos = S1_MID
s2_pos = S2_MID
timer = 0
didReset = False


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


def loadStorage():
    storagelib.subscribeWithPrototype("camera", {
        "elev": {
            "up": S2_UP,
            "mid": S2_MID,
            "down": S2_DOWN
        },
        "rudd": {
            "front": S1_FRONT,
            "mid": S1_MID,
            "back": S1_BACK
        }
    })
    storagelib.waitForData()

    print("  Storage details loaded.")


def capture():
    global continuousIterator

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


def handleLift(topic, message, groups):
    global direction, stage
    if DEBUG:
        print(message)

    if message == "reset":
        reset()
        direction = RESET
    elif message == "resetdown":
        resetDown()
        direction = IDLE
    elif message == "stop":
        direction = IDLE
    else:
        if didReset:
            if message == "up":
                if direction != RESET:
                    direction = UP
                    stage = 0
            elif message == "down":
                if direction != RESET:
                    direction = DOWN
                    stage = 0
        else:
            print("Cannot move until reset!")


def handlePan(topic, message, groups):
    global direction, stage, s1_pos
    if DEBUG:
        print(message)

    if message == "reset":
        reset()
        direction = RESET
    elif message == "resetdown":
        resetDown()
        direction = IDLE
    elif message == "stop":
        direction = IDLE
    else:
        if didReset:
            if message == "left":
                s1_pos += 1
                pyroslib.publish("servo/11", str(s1_pos))
            elif message == "right":
                s1_pos -= 1
                pyroslib.publish("servo/11", str(s1_pos))
        else:
            print("Cannot move until reset!")


def handleTilt(topic, message, groups):
    global direction, stage, s2_pos
    if DEBUG:
        print(message)

    if message == "reset":
        reset()
        direction = RESET
    elif message == "resetdown":
        resetDown()
        direction = IDLE
    elif message == "stop":
        direction = IDLE
    else:
        if didReset:
            if message == "up":
                s2_pos += 1
                pyroslib.publish("servo/10", str(s2_pos))
            elif message == "down":
                s2_pos -= 1
                pyroslib.publish("servo/10", str(s2_pos))
        else:
            print("Cannot move until reset!")


def resetDown():
    global direction, stage, s1_pos, s2_pos, timer, didReset

    elevation_down = int(storagelib.storageMap["camera"]["elev"]["down"])
    rudder_front = int(storagelib.storageMap["camera"]["rudd"]["front"])

    direction = IDLE
    stage = 0
    s1_pos = rudder_front
    s2_pos = elevation_down
    timer = 0
    didReset = True


def reset():
    global direction, stage, s1_pos, s2_pos, timer

    elevation_mid = int(storagelib.storageMap["camera"]["elev"]["mid"])
    rudder_mid = int(storagelib.storageMap["camera"]["rudd"]["mid"])

    direction = IDLE
    stage = 0
    s1_pos = rudder_mid
    s2_pos = elevation_mid
    timer = 0


def driveCamera():
    global direction, stage, s1_pos, s2_pos, status, timer, didReset

    elevation_up = int(storagelib.storageMap["camera"]["elev"]["up"])
    elevation_down = int(storagelib.storageMap["camera"]["elev"]["down"])
    elevation_mid = int(storagelib.storageMap["camera"]["elev"]["mid"])

    rudder_front = int(storagelib.storageMap["camera"]["rudd"]["front"])
    rudder_back = int(storagelib.storageMap["camera"]["rudd"]["back"])
    rudder_mid = int(storagelib.storageMap["camera"]["rudd"]["mid"])

    if direction == IDLE:
        status = DIRECTIONS[direction] + " s:" + str(stage) + " p:" + str(s1_pos) + " " + str(s2_pos)

    elif direction == RESET:
        status = DIRECTIONS[direction] + " s:" + str(stage) + " timer:" + str(timer)
        if stage == 0:
            if timer % 10 == 0:
                pyroslib.publish("servo/11", str(rudder_mid))
            elif timer % 10 > 1:
                pyroslib.publish("servo/11", "0")
        if stage == 1:
            if timer % 10 == 0:
                pyroslib.publish("servo/10", str(elevation_mid))
            elif timer % 10 > 1:
                pyroslib.publish("servo/10", "0")

        timer += 1
        if timer > 200:
            if stage == 0:
                stage = 1
                timer = 0
            else:
                didReset = True
                direction = IDLE
                pyroslib.publish("camera/lift", "done reset")

    elif direction == UP:
        status = DIRECTIONS[direction] + " s:" + str(stage) + " p:" + str(s1_pos) + " " + str(s2_pos)
        if stage == 0:
            if s1_pos == rudder_mid:
                stage = 1
            else:
                pyroslib.publish("servo/11", str(s1_pos))
                s1_pos += 1

        if stage == 1:
            if s2_pos == elevation_up:
                stage = 2
            else:
                pyroslib.publish("servo/10", str(s2_pos))
                s2_pos -= 1

        if stage == 2:
            if s1_pos == rudder_front:
                stage = 3
                pyroslib.publish("camera/lift", "done up")
            else:
                pyroslib.publish("servo/11", str(s1_pos))
                s1_pos -= 1

    elif direction == DOWN:
        status = DIRECTIONS[direction] + " s:" + str(stage) + " p:" + str(s1_pos) + " " + str(s2_pos)
        if stage == 0:
            if s1_pos == rudder_mid:
                stage = 1
            else:
                pyroslib.publish("servo/11", str(s1_pos))
                s1_pos += 1

        if stage == 1:
            if s2_pos == elevation_down:
                stage = 2
            else:
                pyroslib.publish("servo/10", str(s2_pos))
                s2_pos += 1

        if stage == 2:
            if s1_pos == rudder_front:
                stage = 3
                pyroslib.publish("camera/lift", "done down")
            else:
                pyroslib.publish("servo/11", str(s1_pos))
                s1_pos -= 1

    if DEBUG:
        print(status)


def loop():
    global doReadSensor, lastTimeRead, continuousMode
    driveCamera()
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

        pyroslib.subscribe("camera/raw/fetch", handleRaw)
        pyroslib.subscribe("camera/processed/fetch", handleFetchProcessed)
        pyroslib.subscribe("camera/whitebalance/fetch", fetchWhiteBalance)
        pyroslib.subscribe("camera/whitebalance/store", storeWhiteBalance)
        pyroslib.subscribe("camera/continuous", handleContinuousMode)
        pyroslib.subscribe("camera/format", handleFormat)
        pyroslib.subscribe("camera/lift", handleLift)
        pyroslib.subscribe("camera/pan", handlePan)
        pyroslib.subscribe("camera/tilt", handleTilt)
        pyroslib.init("camera-service")

        print("  Loading storage details...")
        loadStorage()

        print("Started camera service.")

        resetDown()

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
