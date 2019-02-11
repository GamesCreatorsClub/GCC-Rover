#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import roverscreen
import sys
import pygame
import pyros
import pyros.gcc
import pyros.gccui
import pyros.pygamehelper
import gccui


screen = pyros.gccui.initAll((320, 480), True)
font = pyros.gccui.font
smallFont = pyros.gccui.smallFont


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


pyros.init("radar-client-#", unique=True, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)

uiFactory = gccui.FlatTheme.FlatThemeFactory()
uiFactory.font = pyros.gccui.font
uiAdapter = gccui.UIAdapter(screen)

roverscreen.init(uiFactory, uiAdapter, font, smallFont)


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        uiAdapter.processEvent(event)

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)
    pyros.gccui.background(True)

    uiAdapter.draw(screen)

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()
