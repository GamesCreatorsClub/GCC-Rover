
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
import pyros.pygamehelper
from PIL import Image


pygame.init()
bigFont = pygame.font.SysFont("arial", 32)
font = pygame.font.SysFont("arial", 24)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((1024, 800))

cameraImage = Image.new("L", [80, 64])

rawImage = pygame.Surface((80, 64), 24)
receivedProcessedImage = pygame.Surface((80, 64), 24)
whiteBalanceImage = pygame.Surface((80, 64), 24)
processedImage = pygame.Surface((80, 64), 24)

rawImageBig = pygame.Surface((320, 256), 24)
receivedProcessedImageBig = pygame.Surface((320, 256), 24)
whiteBalanceImageBig = pygame.Surface((320, 256), 24)
processedImageBig = pygame.Surface((320, 256), 24)


minAngle = 0
maxAngle = 0
midAngle = 0
forwardSpeed = 2

running = False
continuousMode = False
lights = False
resubscribe = time.time()
lastReceivedTime = time.time()
frameTime = ""
turnDistance = 0


def connected():
    pyros.publish("camera/processed/fetch", "")


def toPyImage(imageBytes):
    pilImage = Image.frombytes("L", (80, 64), imageBytes)
    return toPyImage2(pilImage)


def toPyImage2(pilImage):
    pilRGBImage = Image.new("RGB", pilImage.size)
    pilRGBImage.paste(pilImage)
    pyImageSmall = pygame.image.fromstring(pilRGBImage.tobytes("raw"), (80, 64), 'RGB')
    pyImageBig = pygame.transform.scale(pyImageSmall, (320, 256))
    return (pyImageSmall, pyImageBig, pilImage)


def handleWhiteBalance(topic, message, groups):
    global whiteBalanceImage, whiteBalanceImageBig

    images = toPyImage(message)
    whiteBalanceImage = images[0]
    whiteBalanceImageBig = images[1]
    print("  Converted images for white balance.")


def handleCameraRaw(topic, message, groups):
    global rawImage, rawImageBig

    images = toPyImage(message)
    rawImage = images[0]
    rawImageBig = images[1]
    print("  Converted images for raw.")


def handleCameraProcessed(topic, message, groups):
    global receivedProcessedImage, receivedProcessedImageBig, processedImage, processedImageBig, cameraImage
    global frameTime, lastReceivedTime

    images = toPyImage(message)
    receivedProcessedImage = images[0]
    receivedProcessedImageBig = images[1]

    images = toPyImage(message)
    processedImage = images[0]
    processedImageBig = images[1]
    cameraImage = images[2]
    print("  Converted images for processed.")

    processImage()

    now = time.time()
    if now - lastReceivedTime > 5:
        frameTime = ">5s"
    else:
        frameTime = str(round(now - lastReceivedTime, 2))

    lastReceivedTime = now

    if running:
        goOneStep()


def handleFeedbackMessage(topic, message, groups):
    global feedback, foundSpeed

    feedback = message
    if message.startswith("done-move "):
        split = message.split(" ")
        foundSpeed = int(float(split[1]))

    if not continuousMode:
        pyros.publish("camera/processed/fetch", "")


def processImage():
    global processedImageBig, processedImage, minAngle, maxAngle, midAngle, turnDistance

    r = 28

    ha = math.atan2(0.5, r + 0.5) * 180 / math.pi
    ha *= 2

    print("Angle is " + str(ha))
    a = -90

    p1 = 255
    p2 = 0

    minAngle = 90
    maxAngle = -90
    lastMinAngle = 90
    lastMaxAngle = -90

    c = 0
    while a <= 90:
        a += ha
        ra = a * math.pi / 180 + math.pi

        x = int(r * math.cos(ra) + 40)
        y = int(r * math.sin(ra) + 32)

        p = cameraImage.getpixel((x, y))
        if p > 127:
            processedImage.set_at((x, y), (0, 255, 0))
        else:
            processedImage.set_at((x, y), (255, 0, 0))
            if a > maxAngle:
                maxAngle = a
            if a < minAngle:
                minAngle = a

        c += 1

    midAngle = (maxAngle + minAngle) / 2


    r = 30

    a = midAngle

    ap = 90 - a

    apr = ap * math.pi / 180.0

    turnDistance = r / (2.0 * math.cos(apr))

    print("D = " + str(turnDistance) + ", apr = " + str(apr))

    processedImageBig = pygame.transform.scale(processedImage, (320, 256))

    # images = toPyImage2(cameraImage)
    # processedImage = images[0]
    # processedImageBig = images[1]
    print("Scanned " + str(c) + " points, midAngle=" + str(midAngle) + ", minAngle=" + str(minAngle) + ", maxAngle=" + str(maxAngle))


def goOneStep():
    if -20 < midAngle < 20:
        goForward()
    elif -45 < midAngle < 45:
        pyros.publish("move/stop", "")
        pyros.loop(0.5)
        print("Steering arond " + str(-turnDistance))
        pyros.publish("move/steer", str(int(-turnDistance)) + " " + str(forwardSpeed))
        pyros.loop(0.5)
    else:
        print("Turning to " + str(midAngle))
        pyros.publish("move/turn", str(round(midAngle, 1)))
        # pyros.loop(0.5)


def goForward():
    print("** Going forward " + str(forwardSpeed))
    pyros.publish("move/drive", "0 " + str(forwardSpeed))
    pyros.loop(0.5)
    pyros.publish("move/stop", "")
    pyros.loop(1)
    pyros.publish("camera/processed/fetch", "")


def onKeyDown(key):
    global continuousMode, lights, forwardSpeed, running

    if key == pygame.K_ESCAPE:
        sys.exit()
    elif key == pygame.K_w:
        print("  fetching white balance picture...")
        pyros.publish("camera/whitebalance/fetch", "")
    elif key == pygame.K_r:
        print("  fetching white balance picture...")
        pyros.publish("camera/raw/fetch", "")
    elif key == pygame.K_p:
        print("  fetching white balance picture...")
        pyros.publish("camera/processed/fetch", "")
    elif key == pygame.K_s:
        print("  storing whitebalance image...")
        pyros.publish("camera/whitebalance/store", "")
        pyros.publish("camera/whitebalance/fetch", "")
    elif key == pygame.K_l:
        if lights:
            print("  switching off lights")
            pyros.publish("lights/camera", "off")
            lights = False
        else:
            print("  switching on lights")
            pyros.publish("lights/camera", "on")
            lights = True
    elif key == pygame.K_c:
        continuousMode = not continuousMode
    elif key == pygame.K_g:
        goOneStep()
    elif key == pygame.K_RETURN:
        running = not running
        if running:
            goOneStep()
    elif key == pygame.K_f:
        goForward()
    elif key == pygame.K_m:
        processImage()
    elif key == pygame.K_LEFTBRACKET:
        forwardSpeed -= 1
        if forwardSpeed < 0:
            forwardSpeed = 0
    elif key == pygame.K_RIGHTBRACKET:
        forwardSpeed += 1
    elif key == pygame.K_SPACE:
        pyros.publish("move/stop", "")
        running = False
    else:
        pyros.gcc.handleConnectKeys(key)


def onKeyUp(key):
    return


pyros.subscribeBinary("camera/whitebalance", handleWhiteBalance)
pyros.subscribeBinary("camera/raw", handleCameraRaw)
pyros.subscribeBinary("camera/processed", handleCameraProcessed)
pyros.subscribe("move/feedback", handleFeedbackMessage)
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
        text = bigFont.render("Connected to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (128, 255, 128))
    else:
        text = bigFont.render("Connecting to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (255, 128, 128))

    screen.blit(text, (0, 0))

    text = font.render("Continuous : " + str(continuousMode), 1, (255, 255, 255))
    screen.blit(text, (400, 50))

    text = font.render("Frame time: " + str(frameTime), 1, (255, 255, 255))
    screen.blit(text, (400, 80))

    text = font.render("Mid angle: " + str(round(midAngle, 2)), 1, (255, 255, 255))
    screen.blit(text, (400, 110))

    text = font.render("Speed: " + str(forwardSpeed), 1, (255, 255, 255))
    screen.blit(text, (750, 50))

    text = font.render("Running: " + str(running), 1, (255, 255, 255))
    screen.blit(text, (750, 80))

    text = font.render("Turn around dist: " + str(round(turnDistance, 2)), 1, (255, 255, 255))
    screen.blit(text, (750, 110))


    screen.blit(rawImage, (10, 50))
    screen.blit(whiteBalanceImage, (110, 50))
    screen.blit(receivedProcessedImage, (210, 50))

    screen.blit(rawImageBig, (10, 150))
    screen.blit(whiteBalanceImageBig, (362, 150))
    screen.blit(receivedProcessedImageBig, (724, 150))

    screen.blit(processedImageBig, (724, 420))

    pygame.display.flip()
    frameclock.tick(30)

    if continuousMode and time.time() - resubscribe > 2:
        resubscribe = time.time()
        if pyros.isConnected():
            pyros.publish("camera/continuous", "on")
