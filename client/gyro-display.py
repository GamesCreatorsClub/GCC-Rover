
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
import pyros.pygamehelper

screen = pyros.gccui.initAll((600, 600), True)
bigFont = pyros.gccui.bigFont

arrow_image = pygame.image.load("arrow.png")


gyroAngle = 0.0


def connected():
    pyros.publish("sensor/gyro/continuous", "")


def handleGyroData(topic, message, groups):
    global gyroAngle

    data = message.split(",")
    gyroAngle += float(data[2])


def onKeyDown(key):
    if pyros.gcc.handleConnectKeyDown(key):
        pass


def onKeyUp(key):
    if pyros.gcc.handleConnectKeyUp(key):
        pass


pyros.subscribe("sensor/gyro", handleGyroData)
pyros.init("gyro-display-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)


resubscribe = time.time()

while True:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)
    pyros.gccui.background(True)

    loc = arrow_image.get_rect().center
    rot_arrow_image = pygame.transform.rotate(arrow_image, -gyroAngle)
    rot_arrow_image.get_rect().center = loc

    screen.blit(rot_arrow_image, (150, 150))

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()

    if time.time() - resubscribe > 2:
        resubscribe = time.time()
        if pyros.isConnected():
            pyros.publish("sensor/gyro/continuous", "")
