
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import sys
import pygame
import pyros
import pyros.gcc
import pyros.gccui
import pyros.agent as agent
import pyros.pygamehelper


SCALE = 10


screen = pyros.gccui.initAll((640, 480), True)
font = pyros.gccui.font
bigFont = pyros.gccui.bigFont

feedback = ""
status = ""

angle = 22.5
distance = 10
speed = 10
foundSpeed = 0

def connected():
    pyros.agent.init(pyros.client, "fine-drive-agent.py")


def feedbackMessage(topic, message, groups):
    global feedback, foundSpeed

    feedback = message
    if message.startswith("done-move "):
        split = message.split(" ")
        foundSpeed = int(float(split[1]))


def onKeyDown(key):
    global angle, distance, speed, status

    if pyros.gcc.handleConnectKeyDown(key):
        pass
    if key == pygame.K_ESCAPE:
        pyros.publish("finemove/stop", "stop")
        pyros.loop(0.7)
    elif key == pygame.K_SPACE:
        pyros.publish("finemove/stop", "stop")
        print("** STOP!!!")
    elif key == pygame.K_UP:
        status = "** FORWARD"
        pyros.publish("finemove/forward", distance)
        print("** FORWARD")
    elif key == pygame.K_DOWN:
        status = "** BACK"
        pyros.publish("finemove/back", distance)
        print("** BACK")
    elif key == pygame.K_LEFT:
        status = "** ROTATE LEFT"
        pyros.publish("finemove/rotate", str(-angle))
        print("** ROTATE LEFT")
    elif key == pygame.K_RIGHT:
        status = "** ROTATE RIGHT"
        pyros.publish("finemove/rotate", str(angle))
        print("** ROTATE RIGHT")
    elif key == pygame.K_LEFTBRACKET:
        angle -= 22.5
    elif key == pygame.K_RIGHTBRACKET:
        angle += 22.5
    elif key == pygame.K_o:
        distance -= 5
    elif key == pygame.K_p:
        distance += 5
    elif key == pygame.K_k:
        speed -= 1
    elif key == pygame.K_l:
        speed += 1
    elif key == pygame.K_w:
        status = "** FORWARD CONT"
        pyros.publish("finemove/forward", "0")
        print("** FORWARD CONT")
    elif key == pygame.K_a:
        pyros.publish("move/steer", "-150 " + str(foundSpeed))
    elif key == pygame.K_s:
        pyros.publish("move/steer", "1000000 " + str(foundSpeed))
    elif key == pygame.K_d:
        pyros.publish("move/steer", "150 " + str(foundSpeed))
    else:
        pyros.gcc.handleConnectKeyDown(key)


def onKeyUp(key):
    if pyros.gcc.handleConnectKeyUp(key):
        pass


pyros.subscribe("finemove/feedback", feedbackMessage)
pyros.init("drive-controller-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)
    pyros.gccui.background(True)

    screen.blit(bigFont.render("Angle: " + str(angle), 1, (255, 255, 255)), (10, 60))

    screen.blit(bigFont.render("Distance: " + str(distance), 1, (255, 255, 255)), (350, 60))

    screen.blit(bigFont.render("Speed: " + str(speed), 1, (255, 255, 255)), (350, 100))

    screen.blit(bigFont.render("Detected Speed: " + str(foundSpeed), 1, (255, 255, 255)), (350, 140))

    screen.blit(bigFont.render(status, 1, (255, 255, 255)), (10, 180))

    screen.blit(bigFont.render(feedback, 1, (255, 255, 255)), (10, 240))

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()
