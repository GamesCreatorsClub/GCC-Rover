
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import sys
import time
import pygame
import pyros
import pyros.gcc
import pyros.gccui
import pyros.agent
import pyros.pygamehelper

WHITE = (255, 255, 255)
MAX_PING_TIMEOUT = 1

INITIAL_SPEED = 100
INITIAL_SIDE_GAIN = 0.4
INITIAL_FORWARD_GAIN = 1.0
INITIAL_DISTANCE_GAIN = 2.0
INITIAL_CORNER_GAIN = 1.7

sideGain = INITIAL_SIDE_GAIN
forwardGain = INITIAL_FORWARD_GAIN
distanceGain = INITIAL_DISTANCE_GAIN
cornerGain = INITIAL_CORNER_GAIN
speed = INITIAL_SPEED

pingLastTime = 0

angle = 0

distanceDeg1 = -1
distanceDeg2 = -1
distance1 = -1
distance2 = -1
avgDistance1 = -1
avgDistance2 = -1

gyroAngle = 0

corridorWidth = 0
idealDistance = 0

run = False

driveAngle = 0

screen = pyros.gccui.initAll((600, 600), True)
font = pyros.gccui.font
bigFont = pyros.gccui.bigFont


def connected():
    pyros.agent.init(pyros.client, "maze-agent.py")
    pyros.publish("maze/ping", "")
    pyros.publish("maze/sideGain", str(sideGain))
    pyros.publish("maze/forwardGain", str(forwardGain))
    pyros.publish("maze/distanceGain", str(distanceGain))
    pyros.publish("maze/cornerGain", str(cornerGain))
    pyros.publish("maze/speed", str(speed))
    stop()


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


def handleDataCorridor(topic, message, groups):
    global corridorWidth

    corridorWidth = float(message)


def handleDataIdealDistance(topic, message, groups):
    global idealDistance

    idealDistance = float(message)


def stop():
    global run
    pyros.publish("maze/command", "stop")
    run = False


def quickstart():
    global run
    pyros.publish("maze/command", "quickstart")
    run = True


def start():
    global run
    pyros.publish("maze/command", "start")
    run = True


def scanWidth():
    pyros.publish("maze/command", "scan")


def onKeyDown(key):
    global run, angle, speed, gyroAngle, sideGain, forwardGain, distanceGain, cornerGain

    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif key == pygame.K_ESCAPE:
        stop()
        pyros.loop(0.7)
    elif key == pygame.K_SPACE:
        stop()
    elif key == pygame.K_RETURN:
        print("** Starting...")
        run = True
        quickstart()
    elif key == pygame.K_BACKSLASH:
        print("** Starting...")
        run = True
        start()
    elif key == pygame.K_s:
        scanWidth()
        # pyros.publish("sensor/distance/scan", "")
        # print("** Asked for scan")
    elif key == pygame.K_r:
        pyros.publish("sensor/distance/read", str(angle))
        print("** Asked for distance")
    elif key == pygame.K_o:
        angle -= 22.5
        if angle < -90:
            angle = -90
        pyros.publish("sensor/distance/read", str(angle))
        print("** Asked for distance")
    elif key == pygame.K_p:
        angle += 22.5
        if angle > 90:
            angle = 90
        pyros.publish("sensor/distance/read", str(angle))
        print("** Asked for distance")
    elif key == pygame.K_DOWN:
        if speed > 100:
            speed -= 50
        elif speed > 50:
            speed -= 5
        else:
            speed -= 1

        if speed < 1:
            speed = 1

        pyros.publish("maze/speed", int(speed))
    elif key == pygame.K_UP:
        if speed >= 100:
            speed += 50
        elif speed >= 50:
            speed += 10
        else:
            speed += 1

        if speed > 300:
            speed = 300

        pyros.publish("maze/speed", int(speed))
    elif key == pygame.K_LEFT and (pyros.gcc.rshift or pyros.gcc.lshift):
        sideGain -= 0.1
        if sideGain < 0.1:
            sideGain = 0.1
        pyros.publish("maze/sideGain", str(float(round(sideGain, 1))))
    elif key == pygame.K_RIGHT and (pyros.gcc.rshift or pyros.gcc.lshift):
        sideGain += 0.1
        if sideGain > 10:
            sideGain = 10
        pyros.publish("maze/sideGain", str(float(round(sideGain, 1))))
    elif key == pygame.K_LEFT and not pyros.gcc.rshift and not pyros.gcc.lshift:
        forwardGain -= 0.1
        if forwardGain < 0.1:
            forwardGain = 0.1
        pyros.publish("maze/forwardGain", str(float(round(forwardGain, 1))))
    elif key == pygame.K_RIGHT and not pyros.gcc.rshift and not pyros.gcc.lshift:
        forwardGain += 0.1
        if forwardGain > 10:
            forwardGain = 10
        pyros.publish("maze/forwardGain", str(float(round(forwardGain, 1))))
    elif key == pygame.K_LEFTBRACKET and (pyros.gcc.rshift or pyros.gcc.lshift):
        distanceGain -= 0.1
        if distanceGain < 0.1:
            distanceGain = 0.1
        pyros.publish("maze/distanceGain", str(float(round(distanceGain, 1))))
    elif key == pygame.K_RIGHTBRACKET and (pyros.gcc.rshift or pyros.gcc.lshift):
        distanceGain += 0.1
        if distanceGain > 10:
            distanceGain = 10
        pyros.publish("maze/distanceGain", str(float(round(distanceGain, 1))))
    elif key == pygame.K_LEFTBRACKET and not pyros.gcc.rshift and not pyros.gcc.lshift:
        cornerGain -= 0.1
        if cornerGain < 0.1:
            cornerGain = 0.1
        pyros.publish("maze/cornerGain", str(float(round(cornerGain, 1))))
    elif key == pygame.K_RIGHTBRACKET and not pyros.gcc.rshift and not pyros.gcc.lshift:
        cornerGain += 0.1
        if cornerGain > 10:
            cornerGain = 10
        pyros.publish("maze/cornerGain", str(float(round(cornerGain, 1))))
    elif key == pygame.K_g:
        pyros.publish("sensor/gyro/continuous", "calibrate,50")
        gyroAngle = 0


def onKeyUp(key):
    if pyros.gcc.handleConnectKeyUp(key):
        pass


pyros.subscribe("maze/data/distances", handleDistances)
pyros.subscribe("maze/data/gyro", handleGyro)
pyros.subscribe("maze/data/corridor", handleDataCorridor)
pyros.subscribe("maze/data/idealDistance", handleDataIdealDistance)

pyros.init("maze-client-#", unique=True, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False, onConnected=connected)


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)
    pyros.gccui.background(True)
    pyros.agent.keepAgents()

    hpos = 50
    hpos = pyros.gccui.drawKeyValue("Stopped", str(not run), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Angle", str(angle), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Speed", str(speed), 8, hpos)

    avgDistance1String = str(format(avgDistance1, '.2f'))
    avgDistance2String = str(format(avgDistance2, '.2f'))

    hpos +=40

    hpos = pyros.gccui.drawKeyValue("Dist @ " + str(distanceDeg1), str(distance1) + ", avg: " + avgDistance1String, 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Dist @ " + str(distanceDeg2), str(distance2) + ", avg: " + avgDistance2String, 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Gyro angle", str(round(gyroAngle, 2)), 8, hpos)
    hpos +=40

    hpos = pyros.gccui.drawKeyValue("Selected", str(driveAngle), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Side Gain", str(round(sideGain, 1)), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Fwd Gain", str(round(forwardGain, 1)), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Dist Gain", str(round(distanceGain, 1)), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Cor Gain", str(round(cornerGain, 1)), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Corridor", str(round(corridorWidth, 1)), 8, hpos)
    hpos = pyros.gccui.drawKeyValue("Ideal dist", str(round(idealDistance, 1)), 8, hpos)

    pyros.gccui.drawSmallText("g-calibrate, s-scan, r-read, o/p-change angle, DOWN/UP-speed, LEFT/RIGHT-gain, SPACE-stop, RETURN-start", (8, screen.get_height() - pyros.gccui.smallFont.get_height()))

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()
