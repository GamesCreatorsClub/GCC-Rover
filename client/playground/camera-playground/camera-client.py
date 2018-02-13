
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


GREY = (160, 160, 160)
WHITE = (255, 255, 255)
GREEN = (128, 255, 128)
RED = (255, 128, 128)

MAX_PING_TIMEOUT = 1
MAX_PICTURES = 400
pingLastTime = 0

pygame.init()
bigFont = pygame.font.SysFont("arial", 32)
font = pygame.font.SysFont("arial", 24)
smallFont = pygame.font.SysFont("arial", 16)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((1024, 800))

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
    global rawImage, rawImageBig

    pilImage = toPILImage(message)

    processedPilImage = processImage(pilImage)

    image = toPyImage(processedPilImage)

    rawImage = pygame.transform.scale(image, (80, 64))
    rawImageBig = pygame.transform.scale(image, (320, 256))

    processedImages.append(rawImage)
    processedBigImages.append(rawImageBig)


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
    global processedImages, processedBigImages

    if key == pygame.K_ESCAPE:
        sys.exit()
    elif key == pygame.K_r:
        print("  fetching raw picture...")
        pyros.publish("camera/raw/fetch", "")
    elif key == pygame.K_s:
        print("  fetching continuous pictures...")
        pyros.publish("camera/continuous", "")
    elif key == pygame.K_c:
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

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)

    screen.fill((0, 0, 0))

    if pyros.isConnected():
        screen.blit(bigFont.render("Connected to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, GREEN), (0, 0))
    else:
        screen.blit(bigFont.render("Connecting to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, RED), (0, 0))

    screen.blit(font.render("Selected: " + str(ptr) + " of " + str(len(processedImages)), 1, WHITE), (400, 50))
    screen.blit(font.render("Frame time: " + str(frameTime), 1, WHITE), (400, 80))
    screen.blit(font.render("Angle: " + str(feedback["angle"]), 1, WHITE), (400, 110))
    screen.blit(font.render("Speed: " + str(forwardSpeed), 1, WHITE), (750, 50))
    screen.blit(font.render("Running: " + str(running), 1, WHITE), (750, 80))
    screen.blit(font.render("Turn dist: " + str(feedback["turnDistance"]), 1, WHITE), (750, 110))

    screen.blit(smallFont.render("[/]-speed, s-fetch and store wb, LEFT/RIGHT-scroll, g-one step, n-prepare", 1, WHITE), (0, 760))
    screen.blit(smallFont.render("SPACE-stop, RETURN-start, p-processed img, w-whitebalace img, r-raw img, l-lights", 1, WHITE), (0, 780))

    screen.blit(rawImage, (10, 50))

    screen.blit(rawImageBig, (10, 150))

    if ptr >= 0:
        if ptr > len(processedImages) - 1:
            ptr = len(processedImages) - 1
        i = ptr
    else:
        i = len(processedImages) - 1
    x = 724
    while i >= 0 and x >= 0:
        screen.blit(processedBigImages[i], (x, 420))
        x -= 362
        i -= 1

    pygame.display.flip()
    frameclock.tick(30)

    now = time.time()

