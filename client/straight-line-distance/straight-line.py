
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

STEER_GAIN = 0.5
STEER_MAX_CONTROL = 30
INTEGRAL_FADE_OUT = 1

P_GAIN = 0.70
I_GAIN = 0.25
D_GAIN = 0.05


screen = pyros.gccui.initAll((600, 600), True)
font = pyros.gccui.font
bigFont = pyros.gccui.bigFont
veryBigFont = pygame.font.SysFont("apple casual", 300)

arrow_image = pygame.image.load("arrow.png")

distanceDeg1 = -1
distanceDeg2 = -1
distance1 = -1
distance2 = -1
avgDistance1 = -1
avgDistance2 = -1

gyroAngle = 0

steerGain = STEER_GAIN
pGain = P_GAIN
iGain = I_GAIN
dGain = D_GAIN

shift = False


def connected():
    pyros.agent.init(pyros.client, "straight-line-agent.py")
    print("Sent agent")


def handleGyroData(topic, message, groups):
    global gyroAngle

    data = message.split(",")
    gyroAngle += float(data[2])


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


def updateGain():
    pyros.publish("straight/steerGain", str(round(steerGain, 2)))
    pyros.publish("straight/pGain", str(round(pGain, 2)))
    pyros.publish("straight/iGain", str(round(iGain, 2)))
    pyros.publish("straight/dGain", str(round(dGain, 2)))


def onKeyDown(key):
    global steerGain, pGain, iGain, dGain

    shift = pyros.gcc.lshift or pyros.gcc.rshift

    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif key == pygame.K_ESCAPE:
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
            dGain += 0.05
        else:
            pGain += 0.05
            iGain += 0.05
            dGain -= 0.05
        updateGain()

    return


def onKeyUp(key):

    pyros.gcc.handleConnectKeyUp(key)

    return


t = 0

pyros.subscribe("sensor/gyro", handleGyroData)
pyros.subscribe("straightline/distances", handleDistances)
pyros.publish("straight", "calibrate")
pyros.init("straight-line-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)

text = ""

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
    pyros.agent.keepAgents()

    text = bigFont.render("Steer Gain: " + str(round(steerGain, 1)), 1, (255, 128, 128))
    screen.blit(text, (50, 50))

    text = bigFont.render("p: " + str(round(pGain, 1)), 1, (255, 128, 128))
    screen.blit(text, (200, 50))

    text = bigFont.render("i: " + str(round(iGain, 1)), 1, (255, 128, 128))
    screen.blit(text, (300, 50))

    text = bigFont.render("d: " + str(round(dGain, 1)), 1, (255, 128, 128))
    screen.blit(text, (400, 50))

    avgDistance1String = str(format(avgDistance1, '.2f'))
    avgDistance2String = str(format(avgDistance2, '.2f'))

    text = bigFont.render("Dist @ " + str(distanceDeg1) + ": " + str(distance1) + ", avg: " + avgDistance1String, 1, (255, 128, 128))
    screen.blit(text, (50, 450))
    text = bigFont.render("Dist @ " + str(distanceDeg2) + ": " + str(distance2) + ", avg: " + avgDistance2String, 1, (255, 128, 128))
    screen.blit(text, (50, 490))

    text = bigFont.render("Gyro angle: " + str(round(gyroAngle, 2)), 1, (255, 128, 128))
    screen.blit(text, (400, 450))

    text = bigFont.render("Esc: exit    Enter: start    Space: stop", 1, (255, 255, 255))
    screen.blit(text, (20, 540))
    #
    # hpos = pyros.gccui.drawKeyValue("Dist @ " + str(distanceDeg1), str(distance1) + ", avg: " + avgDistance1String, 8, 400)
    # hpos = pyros.gccui.drawKeyValue("Dist @ " + str(distanceDeg2), str(distance2) + ", avg: " + avgDistance2String, 8, 400)

    loc = arrow_image.get_rect().center
    rot_arrow_image = pygame.transform.rotate(arrow_image, -gyroAngle)
    rot_arrow_image.get_rect().center = loc

    screen.blit(rot_arrow_image, (150, 150))

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()
