
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
import pyros.agent
import pyros.pygamehelper


MAX_PING_TIMEOUT = 1

STEER_GAIN = 3
STEER_MAX_CONTROL = 30
INTEGRAL_FADE_OUT = 1

P_GAIN = 0.70
I_GAIN = 0.30
D_GAIN = 0.00

pygame.init()
bigFont = pygame.font.SysFont("apple casual", 32)
veryBigFont = pygame.font.SysFont("apple casual", 300)

frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600, 600))
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

    if key == pygame.K_ESCAPE:
        pyros.publish("straight", "stop")
        pyros.loop(0.7)
        print("Leaving")
        sys.exit(0)
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
        pyros.gcc.handleConnectKeys(key)
    return


def onKeyUp(key):
    global shift

    if key == pygame.KMOD_SHIFT:
        shift = False

    return


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

    screen.fill((0, 0, 0))

    if pyros.isConnected():
        text = bigFont.render("Connected to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (128, 255, 128))
    else:
        text = bigFont.render("Connecting to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (255, 128, 128))

    screen.blit(text, (0, 0))

    text = bigFont.render("Steer Gain: " + str(round(steerGain, 1)), 1, (255, 128, 128))
    screen.blit(text, (0, 20))

    text = bigFont.render("p: " + str(round(pGain, 1)), 1, (255, 128, 128))
    screen.blit(text, (200, 20))

    text = bigFont.render("i: " + str(round(iGain, 1)), 1, (255, 128, 128))
    screen.blit(text, (300, 20))

    text = bigFont.render("d: " + str(round(dGain, 1)), 1, (255, 128, 128))
    screen.blit(text, (400, 20))

    text = bigFont.render("Esc: exit    Enter: start    Space: stop", 1, (255, 255, 255))
    screen.blit(text, (20, 540))

    loc = arrow_image.get_rect().center
    rot_arrow_image = pygame.transform.rotate(arrow_image, -gyroAngle)
    rot_arrow_image.get_rect().center = loc

    screen.blit(rot_arrow_image, (150, 150))

    pygame.display.flip()
    frameclock.tick(30)

    if time.time() - pingLastTime > MAX_PING_TIMEOUT:
        pyros.publish("straight/ping", "")
        pingLastTime = time.time()
