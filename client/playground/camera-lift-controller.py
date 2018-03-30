
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
import pyros.agent as agent
import pyros.pygamehelper

screen = pyros.gccui.initAll((600, 600), True)
font = pyros.gccui.font
bigFont = pyros.gccui.bigFont

IDLE = 0
UP = 1
DOWN = 2
RESET = 3

DIRECTIONS = ["IDLE", "UP", "DOWN", "RESET"]

status = "Idle"


def connected():
    pass


S1_FRONT = 60
S1_MID = 161
S1_BACK = 260

S2_DOWN = 175
S2_MID = 140
S2_UP = 74


def reset():
    global direction, stage, s1_pos, s2_pos, timer
    direction = RESET
    stage = 0
    s1_pos = S1_MID
    s2_pos = S2_MID
    timer = 0


def driveCamera():
    global direction, stage, s1_pos, s2_pos, status, timer

    if direction == IDLE:
        status = DIRECTIONS[direction] + " s:" + str(stage) + " p:" + str(s1_pos) + " " + str(s2_pos)

    elif direction == RESET:
        status = DIRECTIONS[direction] + " s:" + str(stage) + " timer:" + str(timer)
        if stage == 0:
            if timer % 10 == 0:
                pyros.publish("servo/11", str(S1_MID))
            elif timer % 10 > 1:
                pyros.publish("servo/11", "0")
        if stage == 1:
            if timer % 10 == 0:
                pyros.publish("servo/10", str(S2_MID))
            elif timer % 10 > 1:
                pyros.publish("servo/10", "0")

        timer = timer + 1
        if timer > 200:
            if stage == 0:
                stage = 1
                timer = 0
            else:
                direction = IDLE
    elif direction == UP:
        status = DIRECTIONS[direction] + " s:" + str(stage) + " p:" + str(s1_pos) + " " + str(s2_pos)
        if stage == 0:
            if s1_pos == S1_MID:
                stage = 1
            else:
                pyros.publish("servo/11", str(s1_pos))
                s1_pos = s1_pos + 1

        if stage == 1:
            if s2_pos == S2_UP:
                stage = 2
            else:
                pyros.publish("servo/10", str(s2_pos))
                s2_pos = s2_pos - 1

        if stage == 2:
            if s1_pos == S1_FRONT:
                stage = 3
            else:
                pyros.publish("servo/11", str(s1_pos))
                s1_pos = s1_pos - 1

    elif direction == DOWN:
        status = DIRECTIONS[direction] + " s:" + str(stage) + " p:" + str(s1_pos) + " " + str(s2_pos)
        if stage == 0:
            if s1_pos == S1_MID:
                stage = 1
            else:
                pyros.publish("servo/11", str(s1_pos))
                s1_pos = s1_pos + 1

        if stage == 1:
            if s2_pos == S2_DOWN:
                stage = 2
            else:
                pyros.publish("servo/10", str(s2_pos))
                s2_pos = s2_pos + 1

        if stage == 2:
            if s1_pos == S1_FRONT:
                stage = 3
            else:
                pyros.publish("servo/11", str(s1_pos))
                s1_pos = s1_pos - 1


def onKeyDown(key):
    global direction, stage

    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif key == pygame.K_UP:
        if direction != RESET:
            direction = UP
            stage = 0
    elif key == pygame.K_DOWN:
        if direction != RESET:
            direction = DOWN
            stage = 0
    elif key == pygame.K_SPACE:
        direction = IDLE
    elif key == pygame.K_r:
        reset()


def onKeyUp(key):
    if pyros.gcc.handleConnectKeyUp(key):
        pass


reset()

pyros.init("camera-lift-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    driveCamera()

    pyros.loop(0.03)
    pyros.gccui.background(True)

    text = bigFont.render("Status: " + status, 1, (255, 255, 255))
    screen.blit(text, (20, 40))

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()
