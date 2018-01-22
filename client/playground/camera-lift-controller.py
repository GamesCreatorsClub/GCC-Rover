
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
import pyros.agent as agent
import pyros.pygamehelper


pygame.init()
bigFont = pygame.font.SysFont("arial", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600, 600))

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

    if key == pygame.K_ESCAPE:
        sys.exit(0)
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
    else:
        pyros.gcc.handleConnectKeys(key)


def onKeyUp(key):
    global stopped

    pass


pyros.init("camera-lift-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)

    screen.fill((0, 0, 0))

    # for i in range(0, 5):
    #     driveCamera()
    #     time.sleep(0.005)

    driveCamera()

    if pyros.isConnected():
        text = bigFont.render("R: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (128, 255, 128))
    else:
        text = bigFont.render("" + pyros.gcc.getSelectedRoverDetailsText(), 1, (255, 128, 128))
    screen.blit(text, (0, 0))

    text = bigFont.render("Status: " + status, 1, (255, 255, 255))
    screen.blit(text, (0, 40))

    pygame.display.flip()
    frameclock.tick(30)
