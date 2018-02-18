
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import sys
import time
import math
import pygame
import pyros
import pyros.gcc
import pyros.agent
import pyros.pygamehelper
from PIL import Image


MAX_PING_TIMEOUT = 1
MAX_PICTURES = 400
pingLastTime = 0


screen_size = (1024, 800)

pyros.gccui.initAll(screen_size, True)


cameraImage = Image.new("L", [80, 64])

rawImage = pygame.Surface((80, 64), 24)

rawImageBig = pygame.Surface((320, 256), 24)


processedImages = []
processedBigImages = []

forwardSpeed = 5

running = False

lights = False
resubscribe = time.time()
lastReceivedTime = time.time()
frameTime = ""

receivedFrameTime = ""

feedback = {
    "angle": "",
    "turnDistance": "",
    "action": "",
    "left": "",
    "right": ""
}

imgNo = 0

ptr = -1
size = (320, 256)

record = False
sequence = False
continuous = False

localFPS = 0
lastProcessed = time.time()
renewContinuous = time.time()


def connected():
    pyros.publish("camera/processed/fetch", "")
    pyros.publish("camera/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")


def toPILImage(imageBytes):
    pilImage = Image.frombytes("RGB", size, imageBytes)
    return pilImage


def toPyImage(pilImage):
    pyImage = pygame.image.fromstring(pilImage.tobytes("raw"), size, "RGB")
    return pyImage


def handleCameraRaw(topic, message, groups):
    global rawImage, rawImageBig, lastProcessed, localFPS

    now = time.time()
    delta = now - lastProcessed
    lastProcessed = now

    if delta < 5:
        localFPS = "%.2f" % round(1 / delta, 2)
    else:
        localFPS = "-"

    pilImage = toPILImage(message)

    processedPilImage = processImage(pilImage)

    image = toPyImage(processedPilImage)

    rawImage = pygame.transform.scale(image, (80, 64))
    rawImageBig = pygame.transform.scale(image, (320, 256))

    if record:
        processedImages.append(rawImage)
        processedBigImages.append(rawImageBig)

    if sequence and not continuous:
        pyros.publish("camera/raw/fetch", "")


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

    if len(red_pixels) > 20:
        centre = calculateCentre(red_pixels)

        drawSpot(image, centre[0], centre[1], (255, 64, 64))

    elif len(green_pixels) > 20:
        centre = calculateCentre(green_pixels)

        drawSpot(image, centre[0], centre[1], (64, 255, 64))

    elif len(blue_pixels) > 20:
        centre = calculateCentre(blue_pixels)

        drawSpot(image, centre[0], centre[1], (64, 64, 255))

    elif len(yellow_pixels) > 20:
        centre = calculateCentre(yellow_pixels)

        drawSpot(image, centre[0], centre[1], (255, 255, 64))

    processedImage = image
    return processedImage


def isRed(p):
    return p[0] > 128 and distance(p[0], p[1]) > 1.2 and distance(p[0], p[1]) > 1.2 and 0.8 < distance(p[1], p[2]) < 1.2


def isGreen(p):
    return p[1] > 128 and distance(p[1], p[0]) > 1.2 and distance(p[1], p[2]) > 1.2 and 0.8 < distance(p[0], p[2]) < 1.2


def isBlue(p):
    return p[2] > 128 and distance(p[2], p[0]) > 1.2 and distance(p[2], p[1]) > 1.2 and 0.8 < distance(p[0], p[1]) < 1.2


def isYellow(p):
    return p[0] > 128 and p[1] > 128 and 0.8 < distance(p[0], p[1]) < 1.2 and distance(p[0], p[2]) > 1.2 and distance(p[1], p[2]) > 1.2


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


def drawSpot(image, cx, cy, color):
    for x in range(cx - 30, cx + 30):
        if x >= 0 and x < 320:
            if cy > 0:
                image.putpixel((x, cy - 1), (255, 255, 255))
            image.putpixel((x, cy), color)
            if cy < 256 - 1:
                image.putpixel((x, cy + 1), (255, 255, 255))
    for y in range(cy - 30, cy + 30):
        if y >= 0 and y < 256:
            if cx > 0:
                image.putpixel((cx - 1, y), (255, 255, 255))
            image.putpixel((cx, y), color)
            if cx < 320 - 1:
                image.putpixel((cx + 1, y), (255, 255, 255))


def toggleStart():
    global imgNo, processedImages, processedBigImages, running

    pass


def stop():
    global running
    pyros.publish("move/stop", "")
    pyros.publish("followLine/command", "stop")
    running = False


def clear():
    global imgNo, processedImages, processedBigImages

    imgNo = 0
    del processedImages[:]
    del processedBigImages[:]


def onKeyDown(key):
    global lights, forwardSpeed, running, ptr, imgNo
    global sequence, record, continuous
    global processedImages, processedBigImages

    if key == pygame.K_ESCAPE:
        sys.exit()
    elif key == pygame.K_f:
        print("  fetching picture...")
        pyros.publish("camera/raw/fetch", "")
    elif key == pygame.K_s:
        sequence = not sequence
    elif key == pygame.K_r:
        record = not record
    elif key == pygame.K_c:
        continuous = not continuous
        if continuous:
            print("  fetching continuous pictures...")
            pyros.publish("camera/continuous", "")
        else:
            print("  stopping continuous pictures...")
            pyros.publish("camera/continuous", "stop")
    elif key == pygame.K_x:
        clear()
    elif key == pygame.K_RETURN:
        toggleStart()
    elif key == pygame.K_SPACE:
        stop()
    elif key == pygame.K_LEFT:
        if ptr == -1:
            ptr = len(processedImages) - 2
        else:
            ptr -= 1
    elif key == pygame.K_RIGHT:
        ptr += 1
        if ptr >= len(processedImages) - 1:
            ptr = -1
    else:
        pyros.gcc.handleConnectKeys(key)


def onKeyUp(key):
    return


pyros.subscribeBinary("camera/raw", handleCameraRaw)

pyros.init("camera-display-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.VIDEORESIZE:
            pyros.gccui.screenResized(event.size)

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    if continuous and time.time() > renewContinuous:
        pyros.publish("camera/continuous", "")
        renewContinuous = time.time() + 1

    pyros.loop(0.03)

    pyros.gccui.background()
    pyros.gcc.drawConnection()

    hpos = 40
    hpos = pyros.gccui.drawKeyValue("Local FPS", str(localFPS), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Recording", str(record), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Sequence", str(sequence), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Continuous", str(continuous), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Selected", str(ptr) + " of " + str(len(processedImages)), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Running", str(running), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Turn dist", str(feedback["turnDistance"]), 8, hpos)

    pyros.gccui.drawSmall("r-toggle record, f - fetch, s-sequence, LEFT/RIGHT-scroll, SPACE-stop, RETURN-start, l-lights, x- clear", (0, pyros.gccui.screen.get_height() - pyros.gccui.smallFont.get_height()))

    pyros.gccui.drawImage(rawImage, (200, 50), 10)
    pyros.gccui.drawImage(rawImageBig, (688, 50), 10)

    if ptr >= 0:
        if ptr > len(processedImages) - 1:
            ptr = len(processedImages) - 1
        i = ptr
    else:
        i = len(processedImages) - 1

    x = 1024 - 320 - 16
    while i >= 0 and x >= 0:
        pyros.gccui.drawImage(processedBigImages[i], (x, 420))
        x -= 341
        i -= 1

    pyros.gccui.frameEnd()

    now = time.time()

