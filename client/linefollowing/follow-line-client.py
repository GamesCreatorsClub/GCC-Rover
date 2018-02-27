
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
import pyros.gccui
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

screen = pyros.gccui.initAll((1024, 800), True)
font = pyros.gccui.font
bigFont = pyros.gccui.bigFont
smallFont = pyros.gccui.smallFont

cameraImage = Image.new("L", [80, 64])

rawImage = pygame.Surface((80, 64), 24)
receivedProcessedImage = pygame.Surface((80, 64), 24)
whiteBalanceImage = pygame.Surface((80, 64), 24)


rawImageBig = pygame.Surface((320, 256), 24)
receivedProcessedImageBig = pygame.Surface((320, 256), 24)
whiteBalanceImageBig = pygame.Surface((320, 256), 24)


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


def connected():
    pyros.publish("camera/processed/fetch", "")
    pyros.agent.init(pyros.client, "turning/follow-line-agent.py")
    print("Sent agent")


def toPyImage(imageBytes):
    pilImage = Image.frombytes("L", (80, 64), imageBytes)

    pilRGBImage = Image.new("RGB", pilImage.size)
    pilRGBImage.paste(pilImage)
    return toPyImage3(pilRGBImage)


def toPyImage3(pilRGBImage):
    pyImageSmall = pygame.image.fromstring(pilRGBImage.tobytes("raw"), (80, 64), 'RGB')
    pyImageBig = pygame.transform.scale(pyImageSmall, (320, 256))
    return pyImageSmall, pyImageBig


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
    global receivedProcessedImage, receivedProcessedImageBig

    images = toPyImage(message)
    receivedProcessedImage = images[0]
    receivedProcessedImageBig = images[1]


def handleAgentProcessed(topic, message, groups):
    global processedImages, processedBigImages
    global frameTime, lastReceivedTime
    global imgNo

    pilRGBImage = Image.frombytes("RGB", (80, 64), message)
    images = toPyImage3(pilRGBImage)

    processedImage = images[0]
    processedImageBig = images[1]

    processedImageBig.blit(smallFont.render("LR: " + str(feedback["left"]) + "/" + str(feedback["right"]), 1, GREY), (0, 0))
    # processedImageBig.blit(smallFont.render("A: " + str(feedback["angle"]), 1, GREY), (0, 0))
    processedImageBig.blit(smallFont.render("T: " + str(feedback["turnDistance"]), 1, GREY), (220, 0))
    processedImageBig.blit(smallFont.render("#: " + str(imgNo), 1, GREY), (0, 230))
    processedImageBig.blit(smallFont.render(feedback["action"], 1, GREY), (180, 230))
    processedImageBig.blit(smallFont.render("T: " + feedback["frameTime"], 1, GREY), (180, 210))

    imgNo += 1

    angle = float(feedback["angle"])

    pa = (angle + 180) * math.pi / 180

    lx = 100 * math.cos(pa) + 160
    ly = 100 * math.sin(pa) + 128

    pygame.draw.line(processedImageBig, (127, 127, 127), (160, 128), (lx, ly))

    processedImages.append(processedImage)
    processedBigImages.append(processedImageBig)

    if len(processedImages) > MAX_PICTURES:
        del processedImages[0]
        del processedBigImages[0]

    now1 = time.time()
    if now1 - lastReceivedTime > 5:
        frameTime = ">5s"
    else:
        frameTime = str(round(now1 - lastReceivedTime, 2))

    lastReceivedTime = now1


def handleFeedback(topic, message, groups):
    global feedback

    pairs = message.split(",")
    for pair in pairs:
        keyValue = pair.split(":")
        feedback[keyValue[0]] = keyValue[1]


def toggleStart():
    global imgNo, processedImages, processedBigImages, running

    running = not running
    if running:
        pyros.publish("followLine/speed", str(forwardSpeed))
        pyros.publish("followLine/command", "start")
        imgNo = 0
        del processedImages[:]
        del processedBigImages[:]
    else:
        pyros.publish("move/stop", "")
        pyros.publish("followLine/command", "stop")


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


def prepare():
    pyros.publish("followLine/command", "prepare")


def goOneStep():
    pyros.publish("followLine/command", "oneStep")


def goForward():
    print("** Going forward " + str(forwardSpeed))
    pyros.publish("move/drive", "0 " + str(forwardSpeed))
    pyros.loop(0.5)
    pyros.publish("move/stop", "")
    pyros.loop(1)
    pyros.publish("camera/processed/fetch", "")


def onKeyDown(key):
    global lights, forwardSpeed, running, ptr, imgNo
    global processedImages, processedBigImages

    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif key == pygame.K_ESCAPE:
        sys.exit()
    elif key == pygame.K_w:
        print("  fetching white balance picture...")
        pyros.publish("camera/whitebalance/fetch", "")
    elif key == pygame.K_r:
        print("  fetching raw picture...")
        pyros.publish("camera/raw/fetch", "")
    elif key == pygame.K_p:
        print("  fetching processed picture...")
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
    elif key == pygame.K_LEFT:
        if ptr == -1:
            ptr = len(processedImages) - 2
        else:
            ptr -= 1
    elif key == pygame.K_RIGHT:
        ptr += 1
        if ptr >= len(processedImages) - 1:
            ptr = -1
    elif key == pygame.K_LEFTBRACKET:
        forwardSpeed -= 1
        if forwardSpeed < 0:
            forwardSpeed = 0
        pyros.publish("followLine/speed", str(forwardSpeed))
    elif key == pygame.K_RIGHTBRACKET:
        forwardSpeed += 1
        pyros.publish("followLine/speed", str(forwardSpeed))
    elif key == pygame.K_c:
        clear()
    elif key == pygame.K_n:
        prepare()
    elif key == pygame.K_g:
        goOneStep()
    elif key == pygame.K_RETURN:
        toggleStart()
    elif key == pygame.K_SPACE:
        stop()


def onKeyUp(key):
    if pyros.gcc.handleConnectKeyUp(key):
        pass


pyros.subscribeBinary("camera/whitebalance", handleWhiteBalance)
pyros.subscribeBinary("camera/raw", handleCameraRaw)
pyros.subscribeBinary("camera/processed", handleCameraProcessed)
pyros.subscribeBinary("followLine/processed", handleAgentProcessed)
pyros.subscribe("followLine/feedback", handleFeedback)
pyros.init("camera-display-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)
    pyros.gccui.background(True)

    screen.blit(font.render("Selected: " + str(ptr) + " of " + str(len(processedImages)), 1, WHITE), (400, 50))
    screen.blit(font.render("Frame time: " + str(frameTime), 1, WHITE), (400, 80))
    screen.blit(font.render("Angle: " + str(feedback["angle"]), 1, WHITE), (400, 110))
    screen.blit(font.render("Speed: " + str(forwardSpeed), 1, WHITE), (750, 50))
    screen.blit(font.render("Running: " + str(running), 1, WHITE), (750, 80))
    screen.blit(font.render("Turn dist: " + str(feedback["turnDistance"]), 1, WHITE), (750, 110))

    screen.blit(smallFont.render("[/]-speed, s-fetch and store wb, LEFT/RIGHT-scroll, g-one step, n-prepare", 1, WHITE), (10, 750))
    screen.blit(smallFont.render("SPACE-stop, RETURN-start, p-processed img, w-whitebalace img, r-raw img, l-lights", 1, WHITE), (10, 770))

    screen.blit(rawImage, (10, 50))
    screen.blit(whiteBalanceImage, (110, 50))
    screen.blit(receivedProcessedImage, (210, 50))

    screen.blit(rawImageBig, (10, 150))
    screen.blit(whiteBalanceImageBig, (362, 150))
    screen.blit(receivedProcessedImageBig, (724, 150))

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

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()

    now = time.time()

    if now - pingLastTime > MAX_PING_TIMEOUT:
        pyros.publish("followLine/ping", "")
        pingLastTime = now
