
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

screen = pyros.gccui.initAll(screen_size, True)


cameraImage = Image.new("L", [80, 64])

rawImage = pygame.Surface((80, 64), 24)
rawImageBig = pygame.Surface((320, 256), 24)
lastImage = None

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

result = {}

distanceDeg1 = -1
distanceDeg2 = -1
distance1 = -1
distance2 = -1
avgDistance1 = -1
avgDistance2 = -1

gyroAngle = 0


def connected():
    print("Starting agent... ", end="")
    pyros.agent.init(pyros.client, "over-the-rainbow-agent.py")
    print("Done.")

    pyros.publish("camera/processed/fetch", "")
    pyros.publish("camera/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")


def toPILImage(imageBytes):
    pilImage = Image.frombytes("RGB", size, imageBytes)
    return pilImage


def toPyImage(pilImage):
    pyImage = pygame.image.fromstring(pilImage.tobytes("raw"), size, "RGB")
    return pyImage


def handleDistances(topic, message, groups):
    global distanceDeg1, distanceDeg2, distance1, distance2, avgDistance1, avgDistance2

    c = 0
    split1 = message.split(",")
    for s1 in split1:
        split2 = s1.split(":")
        if len(split2) == 2:
            deg = int(split2[0])
            split3 = split2[1].split(";")
            if len(split3) == 2:
                dis = float(split3[0])
                avg = float(split3[1])

                if c == 0:
                    distanceDeg1 = deg
                    distance1 = dis
                    avgDistance1 = avg
                elif c == 1:
                    distanceDeg2 = deg
                    distance2 = dis
                    avgDistance2 = avg
        c += 1


def handleGyro(topic, message, groups):
    global gyroAngle

    gyroAngle = float(message)


def handleImageDetails(topic, message, groups):
    global rawImage, rawImageBig, lastImage

    results = []

    for line in message.split("\n"):
        split = line.split(",")
        if len(split) == 3:
            result = int(split[0]), int(split[1]), split[2].lower()
            results.append(result)

    print("Got details " + str(results))

    for result in results:
        if "red" == result[2]:
            drawTarget(lastImage, result, pyros.gccui.RED, "red")
        if "green" == result[2]:
            drawTarget(lastImage, result, pyros.gccui.GREEN, "green")
        if "yellow" == result[2]:
            drawTarget(lastImage, result, pyros.gccui.YELLOW, "yellow")
        if "blue" == result[2]:
            drawTarget(lastImage, result, pyros.gccui.BLUE, "blue")

    if lastImage is not None:
        rawImage = pygame.transform.scale(lastImage, (80, 64))
        rawImageBig = pygame.transform.scale(lastImage, (320, 256))

        if record:
            if len(processedImages) > 0:
                processedImages[len(processedImages) - 1] = rawImage
                processedBigImages[len(processedImages) - 1] = rawImageBig


def handleCameraRaw(topic, message, groups):
    global rawImage, rawImageBig, lastProcessed, localFPS, lastImage

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
    lastImage = image

    # if "red" in result:
    #     drawTarget(image, result["red"], pyros.gccui.RED, "red")
    # if "green" in result:
    #     drawTarget(image, result["green"], pyros.gccui.GREEN, "green")
    # if "yellow" in result:
    #     drawTarget(image, result["yellow"], pyros.gccui.YELLOW, "yellow")
    # if "blue" in result:
    #     drawTarget(image, result["blue"], pyros.gccui.BLUE, "blue")
    #
    rawImage = pygame.transform.scale(lastImage, (80, 64))
    rawImageBig = pygame.transform.scale(lastImage, (320, 256))

    if record:
        processedImages.append(rawImage)
        processedBigImages.append(rawImageBig)
    #
    # if sequence and not continuous:
    #     pyros.publish("camera/raw/fetch", "")


def processImage(image):
    global result

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

    result = {}

    if len(red_pixels) > 20:
        centre = calculateCentre(red_pixels)
        result["red"] = centre

        drawSpot(image, centre[0], centre[1], (255, 64, 64), "red")

    if len(green_pixels) > 20:
        centre = calculateCentre(green_pixels)
        result["green"] = centre

        drawSpot(image, centre[0], centre[1], (64, 255, 64), "green")

    if len(blue_pixels) > 20:
        centre = calculateCentre(blue_pixels)
        result["blue"] = centre

        drawSpot(image, centre[0], centre[1], (64, 64, 255), "blue")

    if len(yellow_pixels) > 20:
        centre = calculateCentre(yellow_pixels)
        result["yellow"] = centre

        drawSpot(image, centre[0], centre[1], (255, 255, 64), "yellow")

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


def drawTarget(image, centre, colour, text):
    x = centre[0] - 20
    if x < 0:
        x = 0

    y = centre[1] - 20
    if y < 0:
        y = 0

    w = 80 - 1
    h = 80 - 1

    tl = 13
    tl1 = 12

    # pygame.draw.rect(image, pyros.gccui.WHITE, pygame.Rect(x + 2, y + 2, w - 2, h - 2), 1)

    pygame.draw.line(image, pyros.gccui.WHITE, (x, y), (x + tl, y))
    pygame.draw.line(image, pyros.gccui.WHITE, (x, y), (x, y + tl))
    pygame.draw.line(image, colour, (x + 1, y + 1), (x + 1, y + tl1))
    pygame.draw.line(image, colour, (x + 1, y + 1), (x + tl1, y + 1))

    pygame.draw.line(image, pyros.gccui.WHITE, (x, y + h), (x + tl, y + h))
    pygame.draw.line(image, pyros.gccui.WHITE, (x, y + h), (x, y + h - tl))
    pygame.draw.line(image, colour, (x + 1, y + h - 1), (x + 1, y  + h - tl1))
    pygame.draw.line(image, colour, (x + 1, y + h - 1), (x + tl1, y + h - 1))

    pygame.draw.line(image, pyros.gccui.WHITE, (x + w, y), (x + w - tl, y))
    pygame.draw.line(image, pyros.gccui.WHITE, (x + w, y), (x + w, y + tl))
    pygame.draw.line(image, colour, (x + w - 1, y + 1), (x + w - 1, y + tl1))
    pygame.draw.line(image, colour, (x + w - 1, y + 1), (x + w - tl1, y + 1))

    pygame.draw.line(image, pyros.gccui.WHITE, (x + w, y + h), (x + w - tl, y + h))
    pygame.draw.line(image, pyros.gccui.WHITE, (x + w , y + h), (x + w, y + h - tl))
    pygame.draw.line(image, colour, (x + w - 1, y + h - 1), (x + w - 1, y + h - tl1))
    pygame.draw.line(image, colour, (x + w - 1, y + h - 1), (x + w - tl1, y + h - 1))

    tdist = 30

    left = False
    if x > tdist:
        tx = x - tdist
        lx = x - 2
        left = True
    elif x + w < image.get_width() - tdist:
        tx = x + w + tdist
        lx = x + w + 2
    else:
        tx = centre[0]
        lx = centre[0]

    if y > tdist:
        ty = y - tdist
        ly = y - 2
    elif y + h < image.get_height() - tdist:
        ty = y + h + tdist
        ly = y + h + 2
    else:
        ty = centre[0]
        ly = centre[0]

    pyros.gccui.font.set_bold(True)
    tw = pyros.gccui.font.size(text)[1]

    pygame.draw.line(image, pyros.gccui.WHITE, (lx, ly), (tx, ty))
    if left:
        pygame.draw.line(image, pyros.gccui.WHITE, (tx - tw - 5, ty), (tx, ty))
        image.blit(pyros.gccui.font.render(text, 1, colour), (tx - tw, ty - 25))
    else:
        pygame.draw.line(image, pyros.gccui.WHITE, (tx + tw + 5, ty), (tx, ty))
        image.blit(pyros.gccui.font.render(text, 1, colour), (tx, ty - 25))
    pyros.gccui.font.set_bold(False)


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


def toggleStart():
    global imgNo, processedImages, processedBigImages, running

    pass


def stop():
    global running
    pyros.publish("move/stop", "")
    pyros.publish("overtherainbow/command", "stop")
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

    if pyros.gcc.handleConnectKeyDown(key):
        pass
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
    elif key == pygame.K_1:
        pyros.publish("overtherainbow/command", "alg1")
    elif key == pygame.K_2:
        pyros.publish("overtherainbow/command", "alg2")
    elif key == pygame.K_3:
        pyros.publish("overtherainbow/command", "alg3")
    elif key == pygame.K_4:
        pyros.publish("overtherainbow/command", "alg4")
    elif key == pygame.K_5:
        pyros.publish("overtherainbow/command", "alg5")
    elif key == pygame.K_6:
        pyros.publish("overtherainbow/command", "alg6")
    elif key == pygame.K_7:
        pyros.publish("overtherainbow/command", "alg7")
    elif key == pygame.K_8:
        pyros.publish("overtherainbow/command", "alg8")
    elif key == pygame.K_9:
        pyros.publish("overtherainbow/command", "alg9")
    elif key == pygame.K_0:
        pyros.publish("overtherainbow/command", "alg10")

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
pyros.subscribe("overtherainbow/distances", handleDistances)
pyros.subscribe("overtherainbow/gyro", handleGyro)
pyros.subscribe("overtherainbow/imagedetails", handleImageDetails)

pyros.init("over-the-rainbow-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.VIDEORESIZE:
            pyros.gccui.screenResized(event.size)

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)
    pyros.agent.keepAgents()

    pyros.gccui.background(True)

    avgDistance1String = str(format(avgDistance1, '.2f'))
    avgDistance2String = str(format(avgDistance2, '.2f'))

    hpos = 40
    hpos = pyros.gccui.drawKeyValue("Local FPS", str(localFPS), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Recording", str(record), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Sequence", str(sequence), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Continuous", str(continuous), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Selected", str(ptr) + " of " + str(len(processedImages)), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Running", str(running), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Turn dist", str(feedback["turnDistance"]), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Dist @ " + str(distanceDeg1), str(distance1) + ", avg: " + avgDistance1String, 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Dist @ " + str(distanceDeg2), str(distance2) + ", avg: " + avgDistance2String, 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Gyro", str(round(gyroAngle, 1)), 8, hpos)

    # if len(historyDistances[0]):
    #     mn = min(historyDistances[0])
    #     mx = max(historyDistances[0])
    #     pyros.gccui.drawGraph((200, 50), (81, 65), historyDistances[0], mn, mx, 80, stick = 10)
    #
    # if len(historyDistances[1]):
    #     mn = min(historyDistances[1])
    #     mx = max(historyDistances[1])
    #     pyros.gccui.drawGraph((320, 50), (81, 65), historyDistances[1], mn, mx, 80, stick = 10)

    pyros.gccui.drawSmallText("r-toggle record, f - fetch, s-sequence, LEFT/RIGHT-scroll, SPACE-stop, RETURN-start, l-lights, d-distances, x- clear", (8, screen.get_height() - pyros.gccui.smallFont.get_height()))

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

