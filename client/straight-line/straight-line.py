
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import sys
import pygame
import time
import pyros
import pyros.gcc
import pyros.gccui
import pyros.agent
import pyros.pygamehelper


MAX_PING_TIMEOUT = 1

STEER_GAIN = 3
STEER_MAX_CONTROL = 30
INTEGRAL_FADE_OUT = 1

P_GAIN = 0.70
I_GAIN = 0.30
D_GAIN = 0.00

screen = pyros.gccui.initAll((600, 600), True)
font = pyros.gccui.font
bigFont = pyros.gccui.bigFont
veryBigFont = pygame.font.SysFont("apple casual", 300)

arrow_image = pygame.image.load("arrow.png")

pingLastTime = 0

gyroAngle = 0
steerGain = 3
pGain = 0.7
iGain = 0.3
dGain = 0.0

shift = False


def connected():
    pyros.agent.init(pyros.client, "straight-line-agent.py")
    print("Sent agent")


def handleGyroData(topic, message, groups):
    global gyroAngle

    data = message.split(",")
    gyroAngle += float(data[2])


def updateGain():
    pyros.publish("straight/steerGain", str(round(steerGain, 2)))
    pyros.publish("straight/pGain", str(round(pGain, 2)))
    pyros.publish("straight/iGain", str(round(iGain, 2)))
    pyros.publish("straight/dGain", str(round(dGain, 2)))


def onKeyDown(key):
    global shift, steerGain, pGain, iGain, dGain

    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif key == pygame.K_ESCAPE:
        pyros.publish("straight", "stop")
        pyros.loop(0.7)
        print("Leaving")
    elif key == pygame.K_RETURN:
        pyros.publish("straight", "forward")
        print("Started")
    elif key == pygame.K_DOWN or key == pygame.K_SPACE:
        pyros.publish("straight", "stop")
        print("Stopped")
    elif key == pygame.KMOD_SHIFT:
        shift = True
    elif key == pygame.K_LEFTBRACKET:
        steerGain -= 0.1
        updateGain()
    elif key == pygame.K_RIGHTBRACKET:
        steerGain += 0.1
    elif key == pygame.K_p:
        if shift:
            pGain += 0.1
            iGain -= 0.05
            dGain -= 0.05
        else:
            pGain -= 0.1
            iGain += 0.05
            dGain += 0.05
        updateGain()
    elif key == pygame.K_i:
        if shift:
            pGain -= 0.05
            iGain += 0.1
            dGain -= 0.05
        else:
            pGain += 0.05
            iGain -= 0.1
            dGain += 0.05
        updateGain()
    elif key == pygame.K_d:
        if shift:
            pGain -= 0.05
            iGain -= 0.05
            dGain += 0.1
        else:
            pGain += 0.05
            iGain += 0.05
            dGain -= 0.1
        updateGain()

    else:
        pyros.gcc.handleConnectKeyDown(key)
    return


def onKeyUp(key):
    global shift

    if pyros.gcc.handleConnectKeyUp(key):
        pass
    elif key == pygame.KMOD_SHIFT:
        shift = False


t = 0

pyros.subscribe("sensor/gyro", handleGyroData)
pyros.publish("straight", "calibrate")
pyros.init("straight-line-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)


while True:
    t += 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pyros.publish("straight", "stop")
            pyros.loop(0.7)
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)
    pyros.gccui.background(True)

    text = bigFont.render("Steer Gain: " + str(round(steerGain, 1)), 1, (255, 128, 128))
    screen.blit(text, (10, 30))

    text = bigFont.render("p: " + str(round(pGain, 1)), 1, (255, 128, 128))
    screen.blit(text, (200, 30))

    text = bigFont.render("i: " + str(round(iGain, 1)), 1, (255, 128, 128))
    screen.blit(text, (300, 30))

    text = bigFont.render("d: " + str(round(dGain, 1)), 1, (255, 128, 128))
    screen.blit(text, (400, 30))

    text = bigFont.render("Esc: exit    Enter: start    Space: stop", 1, (255, 255, 255))
    screen.blit(text, (20, 540))

    loc = arrow_image.get_rect().center
    rot_arrow_image = pygame.transform.rotate(arrow_image, -gyroAngle)
    rot_arrow_image.get_rect().center = loc

    screen.blit(rot_arrow_image, (150, 150))

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()

    if time.time() - pingLastTime > MAX_PING_TIMEOUT:
        pyros.publish("straight/ping", "")
        pingLastTime = time.time()
