#!/usr/bin/python3

import time
import os
import io
import traceback
import pyroslib
from PIL import Image, ImageEnhance
from picamera import PiCamera

#
# camera service
#
# This service is fetching picture from camera...
#

DEBUG = True
CONTINUOUS_MODE_TIMEOUT = 5  # 5 seconds before giving up on sending accel data out
MAX_TIMEOUT = 0.05  # 0.02 is 50 times a second so this is 50% longer


whiteBalance = Image.new("L", (80, 64))

camera = PiCamera()
camera.resolution = (80, 64)
stream = io.BytesIO()

doReadSensor = False
continuousMode = False
lastTimeRead = 0
lastTimeReceivedRequestForContMode = 0

rawL = None
rawRGB = None


def log(msg):
    if DEBUG:
        print(msg)


def capture():
    global rawL, rawRGB

    stream.seek(0)
    camera.capture(stream, "png")
    stream.seek(0)
    rawRGB = Image.open(stream)
    rawL = rawRGB.convert("L")
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
        pixel < minPix
    return pixel


def applyWhiteBalance(img, wb):
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
    start = time.time()
    log("    Capturing image...")
    captured = capture()
    log("    Captured image. Lasted " + str(time.time() - start) + "s")

    start2 = time.time()
    img = applyWhiteBalance(captured, whiteBalance)
    log("    Processed white balance. Lasted " + str(time.time() - start2) + "s")

    start2 = time.time()
    contrast = ImageEnhance.Contrast(img)
    finalImg = contrast.enhance(10)
    log("    Processed contrast. Lasted " + str(time.time() - start2) + "s")

    start2 = time.time()
    finalImg = blackAndWhite(finalImg)
    log("    Set to black and white. Lasted " + str(time.time() - start2) + "s")

    start2 = time.time()
    message = finalImg.tobytes("raw")
    log("    Converted to bytes. Lasted " + str(time.time() - start2) + "s")

    start2 = time.time()
    pyroslib.publish("camera/processed", message)
    log("    Published. Lasted " + str(time.time() - start2) + "s")

    print("  Sent processed image. Total time " + str(time.time() - start) + "s")


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
    global doReadSensor, continuousMode, lastTimeReceivedRequestForContMode

    if message.startswith("stop"):
        continuousMode = False
        doReadSensor = False
        camera.stop_preview()
        print("  Stopped continuous mode...")

    else:
        if not continuousMode:
            continuousMode = True
            doReadSensor = True
            camera.start_preview()
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

        pyroslib.forever(0.5, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
