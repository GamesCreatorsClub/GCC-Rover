
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import sys
import math
import pygame
import pyros
import pyros.gcc
import pyros.gccui
import pyros.pygamehelper

SCALE = 2
WHITE = (255, 255, 255)

screen = pyros.gccui.initAll((600, 600), True)
font = pyros.gccui.font

received = False

distances = {}


def parseDistances(p):
    distances.clear()
    for pair in p.split(","):
        split = pair.split(":")
        try:
            distances[float(split[0])] = float(split[1])
        except:
            pass


def handleSensorDistance(topic, message, groups):
    global received # , angle

    print("** distance = " + message)
    parseDistances(message)
    received = True
    print([d for d in distances])

    angle = 0
    largestDist = 0
    for d in distances:
        if distances[d] > largestDist:
            angle = float(d)
            largestDist = distances[d]
    print(" LARGEST DISTANCE = angle: " + str(angle) + " | distance: " + str(largestDist))


def drawObstacles():
    angles = list(distances.keys())
    angles.sort()
    colour = 255
    for a in angles:
        d2 = distances[a]
        cAngleRadians = math.pi * (180 - a) / 180

        A = (int(300 + d2 / SCALE * math.sin(cAngleRadians)),
             int(300 + d2 / SCALE * math.cos(cAngleRadians)))

        pygame.draw.circle(screen, (colour, colour, 255), A, 10, 1)
        colour -= 20

def drawRadar():

    prevAngle = None
    angles = list(distances.keys())
    angles.sort()

    colour = 255
    for a in angles:
        if prevAngle is not None:

            d1 = distances[prevAngle]
            d2 = distances[a]

            pAngleRadians = math.pi * (180 - prevAngle) / 180
            cAngleRadians = math.pi * (180 - a) / 180

            x1 = 300 + d1 / SCALE * math.sin(pAngleRadians)
            y1 = 300 + d1 / SCALE * math.cos(pAngleRadians)

            x2 = 300 + d2 / SCALE * math.sin(cAngleRadians)
            y2 = 300 + d2 / SCALE * math.cos(cAngleRadians)

            pygame.draw.line(screen, (colour, colour, 255), (x1, y1), (x2, y2))

        colour -= 20
        prevAngle = a


def onKeyDown(key):
    global angle

    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif key == pygame.K_s:
        pyros.publish("sensor/distance/scan", "scan")
        print("** asked for distance")
    elif key == pygame.K_r:
        pyros.publish("sensor/distance/read", str(angle))
        print("** asked for distance")
    elif key == pygame.K_o:
        angle -= 11.25
        if angle < -90:
            angle = -90
    elif key == pygame.K_p:
        angle += 11.25
        if angle > 90:
            angle = 90
    else:
        pyros.gcc.handleConnectKeyDown(key)


def onKeyUp(key):
    if pyros.gcc.handleConnectKeyUp(key):
        pass



angle = 0

pyros.subscribe("sensor/distance", handleSensorDistance)
pyros.init("radar-client-#", unique=True, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)
    pyros.gccui.background(True)

    screen.blit(font.render("Angle (o, p): " + str(angle), 1, WHITE), (10, 80))

    distanceStr = "---"
    v = 0
    for a in distances:
        distanceStr = str(distances[a])
        screen.blit(font.render("Distance (r, s): " + str(distanceStr), 1, WHITE), (300, 80+v*20))
        v+=1

    drawRadar()
    drawObstacles()

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()
