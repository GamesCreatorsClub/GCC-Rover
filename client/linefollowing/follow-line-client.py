
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
receivedProcessedImage = pygame.Surface((80, 64), 24)
whiteBalanceImage = pygame.Surface((80, 64), 24)


rawImageBig = pygame.Surface((320, 256), 24)
receivedProcessedImageBig = pygame.Surface((320, 256), 24)
whiteBalanceImageBig = pygame.Surface((320, 256), 24)


processedImages = []
processedBigImages = []

forwardSpeed = 5
action = ""

running = False

lights = False
resubscribe = time.time()
lastReceivedTime = time.time()
frameTime = ""

receivedFrameTime = ""
angle = 0
turnDistance = 0

imgNo = 0

ptr = -1


def connected():
    pyros.publish("camera/processed/fetch", "")
    pyros.agent.init(pyros.client, "follow-line-agent.py")
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

    t = smallFont.render("A: " + str(angle), 1, GREY)
    processedImageBig.blit(t, (0, 0))

    t = smallFont.render("T: " + str(turnDistance), 1, GREY)
    processedImageBig.blit(t, (220, 0))

    t = smallFont.render("#: " + str(imgNo), 1, GREY)
    processedImageBig.blit(t, (0, 230))

    t = smallFont.render(action, 1, GREY)
    processedImageBig.blit(t, (180, 230))

    t = smallFont.render("T: " + receivedFrameTime, 1, GREY)
    processedImageBig.blit(t, (180, 210))

    imgNo += 1

    pa = (angle + 180) * math.pi / 180

    lx = 100 * math.cos(pa) + 160
    ly = 100 * math.sin(pa) + 128

    pygame.draw.line(processedImageBig, (127, 127, 127), (160, 128), (lx, ly))

    processedImages.append(processedImage)
    processedBigImages.append(processedImageBig)

    if len(processedImages) > MAX_PICTURES:
        del processedImages[0]
        del processedBigImages[0]

    now = time.time()
    if now - lastReceivedTime > 5:
        frameTime = ">5s"
    else:
        frameTime = str(round(now - lastReceivedTime, 2))

    lastReceivedTime = now


def handleAngle(topic, message, groups):
    global angle

    angle = float(message)


def handleAction(topic, message, groups):
    global action

    action = message


def handleTurnDistance(topic, message, groups):
    global turnDistance

    turnDistance = float(message)


def handleFrameTime(topic, message, groups):
    global receivedFrameTime

    receivedFrameTime = message


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

    if key == pygame.K_ESCAPE:
        sys.exit()
    elif key == pygame.K_w:
        print("  fetching white balance picture...")
        pyros.publish("camera/whitebalance/fetch", "")
    elif key == pygame.K_r:
        print("  fetching white balance picture...")
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
    elif key == pygame.K_g:
        goOneStep()
    elif key == pygame.K_LEFT:
        if ptr == -1:
            ptr = len(processedImages) - 2
        else:
            ptr -= 1
    elif key == pygame.K_RIGHT:
        ptr += 1
        if ptr >= len(processedImages) - 1:
            ptr -= 1
    elif key == pygame.K_RETURN:
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
    elif key == pygame.K_LEFTBRACKET:
        forwardSpeed -= 1
        if forwardSpeed < 0:
            forwardSpeed = 0
        pyros.publish("followLine/speed", str(forwardSpeed))
    elif key == pygame.K_RIGHTBRACKET:
        forwardSpeed += 1
        pyros.publish("followLine/speed", str(forwardSpeed))
    elif key == pygame.K_SPACE:
        pyros.publish("move/stop", "")
        pyros.publish("followLine/command", "stop")
        running = False
    else:
        pyros.gcc.handleConnectKeys(key)


def onKeyUp(key):
    return


pyros.subscribeBinary("camera/whitebalance", handleWhiteBalance)
pyros.subscribeBinary("camera/raw", handleCameraRaw)
pyros.subscribeBinary("camera/processed", handleCameraProcessed)
pyros.subscribeBinary("followLine/processed", handleAgentProcessed)
pyros.subscribe("followLine/angle", handleAngle)
pyros.subscribe("followLine/turnDistance", handleTurnDistance)
pyros.subscribe("followLine/action", handleAction)
pyros.subscribe("followLine/frameTime", handleFrameTime)
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

    text = font.render("Selected: " + str(ptr), 1, (255, 255, 255))
    screen.blit(text, (400, 50))

    text = font.render("Frame time: " + str(frameTime), 1, (255, 255, 255))
    screen.blit(text, (400, 80))

    text = font.render("Angle: " + str(round(angle, 2)), 1, (255, 255, 255))
    screen.blit(text, (400, 110))

    text = font.render("Speed: " + str(forwardSpeed), 1, (255, 255, 255))
    screen.blit(text, (750, 50))

    text = font.render("Running: " + str(running), 1, (255, 255, 255))
    screen.blit(text, (750, 80))

    text = font.render("Turn dist: " + str(round(turnDistance, 2)), 1, (255, 255, 255))
    screen.blit(text, (750, 110))

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

    pygame.display.flip()
    frameclock.tick(30)

    now = time.time()

    if now - pingLastTime > MAX_PING_TIMEOUT:
        pyros.publish("followLine/ping", "")
        pingLastTime = now
