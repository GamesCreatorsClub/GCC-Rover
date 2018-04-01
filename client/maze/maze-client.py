
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

INITIAL_SPEED = 20
INITIAL_GAIN = 1.7

gain = INITIAL_GAIN
speed = INITIAL_SPEED

pingLastTime = 0

angle = 0
distanceAtAngle = 0

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
    pyros.publish("maze/gain", str(gain))
    pyros.publish("maze/speed", str(speed))
    stop()


def sanitise(distance):
    # distance -= 100
    if distance < 2:
        distance = 2
    return distance


def toFloatString(f):
    r = str(round(f, 1))
    if "." not in r:
        return r + ".0"
    return r


def handleSensorDistance(topic, message, groups):
    global distanceAtAngle

    # print("** distance = " + message)
    if "," in message:
        pass
    else:
        split = message.split(":")
        d = float(split[1])
        if d >= 0:
            distanceAtAngle = sanitise(d)


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


def start():
    global run
    pyros.publish("maze/command", "start")
    run = True


def onKeyDown(key):
    global run, angle, speed, gain

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
        start()
    elif key == pygame.K_s:
        pyros.publish("sensor/distance/scan", "")
        print("** Asked for scan")
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
        speed -= 1
        if speed < 1:
            speed = -1
        pyros.publish("maze/speed", int(speed))
    elif key == pygame.K_UP:
        speed += 1
        if speed > 100:
            speed = 100
        pyros.publish("maze/speed", int(speed))
    elif key == pygame.K_LEFT:
        gain -= 0.1
        if gain < 1:
            gain = 1
        pyros.publish("maze/gain", int(round(gain, 1)))
    elif key == pygame.K_RIGHT:
        gain += 0.1
        if gain > 10:
            gain = 10
        pyros.publish("maze/gain", int(round(gain, 1)))


def onKeyUp(key):
    if pyros.gcc.handleConnectKeyUp(key):
        pass


pyros.subscribe("maze/data/corridor", handleDataCorridor)
pyros.subscribe("maze/data/idealDistance", handleDataIdealDistance)
pyros.subscribe("sensor/distance", handleSensorDistance)

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

    screen.blit(bigFont.render("Stopped: " + str(not run), 1, WHITE), pygame.Rect(10, 80, 0, 0))

    screen.blit(bigFont.render("Angle: " + str(angle), 1, WHITE), pygame.Rect(10, 120, 0, 0))

    screen.blit(bigFont.render("Speed: " + str(speed), 1, WHITE), pygame.Rect(300, 120, 0, 0))

    screen.blit(bigFont.render("Dist: " + str(distanceAtAngle), 1, WHITE), pygame.Rect(10, 160, 0, 0))

    screen.blit(bigFont.render("Selected: " + str(driveAngle), 1, WHITE), pygame.Rect(10, 200, 0, 0))

    screen.blit(bigFont.render("Gain: " + str(round(gain, 1)), 1, WHITE), pygame.Rect(300, 200, 0, 0))

    screen.blit(bigFont.render("Corridor: " + str(round(corridorWidth, 1)), 1, WHITE), pygame.Rect(300, 240, 0, 0))

    screen.blit(bigFont.render("Ideal dist: " + str(round(idealDistance, 1)), 1, WHITE), pygame.Rect(300, 280, 0, 0))

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()

    if time.time() - pingLastTime > MAX_PING_TIMEOUT:
        pyros.publish("maze/ping", "")
        pingLastTime = time.time()
