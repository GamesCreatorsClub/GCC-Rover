
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
readingDistance = False
distanceDeg = 45
distanceDegs = ["0", "45", "90"]
distances = {}
historyDistances = [[], []]
historyDistancesTiming = [[], []]

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


def handleDistances(topic, message, groups):
    global distances

    n = time.time()

    historyDistancesTiming.append(n)

    distances = {}
    split = message.split(",")
    i = 0
    for s in split:
        kv = s.split(":")
        deg = int(float(kv[0]))
        val = int(float(kv[1]))
        distances[deg] = val
        if i < 2:
            if len(historyDistancesTiming[i]) > 0:
                while len(historyDistancesTiming[i]) > 0 and historyDistancesTiming[i][0] + 2.0 < n:
                    del historyDistancesTiming[i][0]
                    del historyDistances[i][0]

            historyDistances[i].append(val)
            historyDistancesTiming[i].append(n)

        i += 1


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
    global sequence, record, continuous, readingDistance
    global processedImages, processedBigImages

    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif key == pygame.K_f:
        print("  fetching picture...")
        pyros.publish("camera/raw/fetch", "")
    elif key == pygame.K_s:
        sequence = not sequence
    elif key == pygame.K_r:
        record = not record
    elif key == pygame.K_d:
        readingDistance = not readingDistance
        if readingDistance:
            pyros.publish("sensor/distance/deg", str(distanceDeg))
            pyros.publish("sensor/distance/continuous", "start")
        else:
            pyros.publish("sensor/distance/continuous", "stop")
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


def onKeyUp(key):
    pyros.gcc.handleConnectKeyUp(key)
    return


def swap(array):
    v = array[0]
    array[0] = array[1]
    array[1] = v


pyros.subscribeBinary("camera/raw", handleCameraRaw)
pyros.subscribe("sensor/distance", handleDistances)

pyros.init("camera-display-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.VIDEORESIZE:
            pyros.gccui.screenResized(event.size)

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    distanceValues = ["-", "-"]
    distanceDegs = [-100, -100]
    distanceDegStrs = [" right", " left"]

    i = 0
    for d in distances:
        distanceDegs[i] = d
        distanceDegStrs[i] = " @ " + str(int(d))
        mn = min(historyDistances[i])
        mx = max(historyDistances[i])
        av = int(sum(historyDistances[i]) / len(historyDistances[i]))

        totalTime = time.time() - historyDistancesTiming[i][0]
        fps = round(len(historyDistancesTiming[i]) / totalTime, 2)
        if fps > 0.5:
            fps = str(fps)
        else:
            fps = "-"

        distanceValues[i] = str(distances[d]) + " a:" + str(av) + " m:" + str(mn) + " x:" + str(mx) + " e:" + str(abs(mn - mx)) + " s:" + str(len(historyDistances[i])) + " fps: " + fps
        i += 1

    # if distanceDegs[1] > distanceDegs[0]:
    #     swap(distanceValues)
    #     swap(distanceDegs)
    #     swap(distanceDegStrs)

    if time.time() > renewContinuous:
        renewContinuous = time.time() + 1
        if continuous:
            pyros.publish("camera/continuous", "")

        if readingDistance:
            pyros.publish("sensor/distance/continuous", "continue")

    pyros.loop(0.03)

    pyros.gccui.background(True)

    hpos = 40
    hpos = pyros.gccui.drawKeyValue("Local FPS", str(localFPS), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Recording", str(record), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Sequence", str(sequence), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Continuous", str(continuous), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Selected", str(ptr) + " of " + str(len(processedImages)), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Running", str(running), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Turn dist", str(feedback["turnDistance"]), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Distances", str(readingDistance), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Dist" + distanceDegStrs[0], str(distanceValues[0]), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Dist" + distanceDegStrs[1], str(distanceValues[1]), 8, hpos)

    if len(historyDistances[0]):
        mn = min(historyDistances[0])
        mx = max(historyDistances[0])
        pyros.gccui.drawGraph((200, 50), (81, 65), historyDistances[0], mn, mx, 80, stick = 10)

    if len(historyDistances[1]):
        mn = min(historyDistances[1])
        mx = max(historyDistances[1])
        pyros.gccui.drawGraph((320, 50), (81, 65), historyDistances[1], mn, mx, 80, stick = 10)

    pyros.gccui.drawSmallText("r-toggle record, f - fetch, s-sequence, LEFT/RIGHT-scroll, SPACE-stop, RETURN-start, l-lights, d-distances, x- clear", (8, pyros.gccui.screen.get_height() - pyros.gccui.smallFont.get_height()))

    pyros.gccui.drawImage(rawImage, (500, 50), 10)
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
        x -= 336
        i -= 1

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()

    now = time.time()

