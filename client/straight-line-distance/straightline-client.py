
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
import pyros.agent
import pyros.pygamehelper
import time
MAX_PING_TIMEOUT = 1

pingLastTime = 0
steerGain = 1

SCALE = 10
WHITE = (255, 255, 255)

screen = pyros.gccui.initAll((600, 600), True)
font = pyros.gccui.font
bigFont = pyros.gccui.bigFont

received = False

distances = {}
speed = 0

def connected():
    pyros.agent.init(pyros.client, "straight-line-agent.py")
    print("Sent agent")
    pingLastTime = time.time()

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

def updateGain():
    pyros.publish("straight/steerGain", str(round(steerGain, 2)))

def onKeyDown(key):
    global speed, steerGain

    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif key == pygame.K_ESCAPE:
        pyros.publish("straightline/speed", 0)
        pyros.loop(0.7)
        print("Leaving")
        sys.exit(0)
    elif key in (pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4):
        speed = str(key-pygame.K_0)
        pyros.publish("straightline/speed", speed)
        print("** sent speed "+ speed)
    elif key == pygame.K_SPACE:
        speed = str(0)
        pyros.publish("straightline/speed", speed)
        print("** asked to stop")
    elif key == pygame.K_LEFTBRACKET:
        steerGain -= 0.1
        updateGain()
    elif key == pygame.K_RIGHTBRACKET:
        steerGain += 0.1
        updateGain()
    else:
        pyros.gcc.handleConnectKeyDown(key)


def onKeyUp(key):
    if pyros.gcc.handleConnectKeyUp(key):
        pass

# def triggerRead():
#     global thd, angle
#     if thd:
#         thd.cancel()
    # print(time.time())
    # pyros.publish("sensor/distance/read", angle)
    # thd = threading.Timer(3.0, triggerRead)
    # thd.start()

angle = 45
pyros.subscribe("sensor/distance", handleSensorDistance)
pyros.init("straightline-client-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)

thd = None
# triggerRead()

try: # catch system exit if CMD-QUIT is used; so thread can be cancelled
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # pygame.quit()
                # thd.cancel()
                sys.exit()

        pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

        pyros.loop(0.03)
        pyros.gccui.background(True)

        screen.blit(font.render("Speed : " + str(speed), 1, WHITE), (10, 80))

        distanceStr = "---"
        v = 0
        for a in distances:
            distanceStr = str(distances[a])
            screen.blit(font.render("Distance (r, s): " + str(distanceStr), 1, WHITE), (300, 80+v*20))
            v+=1

        drawRadar()
        drawObstacles()

        text = bigFont.render("Steer Gain: " + str(round(steerGain, 1)), 1, (255, 128, 128))
        screen.blit(text, (0, 50))


        text = bigFont.render("Esc: exit    1,2,3,4: start    Space: stop", 1, (255, 255, 255))
        screen.blit(text, (20, 540))

        pyros.agent.keepAgents()

        pyros.gcc.drawConnection()
        pyros.gccui.frameEnd()

        if time.time() - pingLastTime > MAX_PING_TIMEOUT:
            pyros.publish("straight/ping", "")
            pingLastTime = time.time()


except SystemExit:
    pygame.quit()
    if thd:
        thd.cancel()
