
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


MAX_PING_TIMEOUT = 1

pingLastTime = 0


screen_size = (1024, 800)

screen = pyros.gccui.initAll(screen_size, True)

arrow_image = pygame.image.load("arrow.png")
arrow_image = pygame.transform.scale(arrow_image, (50, 50))


gyroAngle = 0

running = False


def connected():
    print("Starting agent... ", end="")
    pyros.agent.init(pyros.client, "template-agent.py")
    print("Done.")


def toggleStart():
    global running

    pass


def stop():
    global running
    pyros.publish("templateAgent/command", "stop")
    running = False


def start():
    global running
    pyros.publish("templateAgent/command", "start")
    running = True


def onKeyDown(key):
    global running

    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif key == pygame.K_SPACE:
        print("Sending stop...")
        stop()
    elif key == pygame.K_RETURN:
        print("Sending start...")
        start()


def onKeyUp(key):
    pyros.gcc.handleConnectKeyUp(key)
    return


# pyros.subscribe("overtherainbow/gyro", handleGyro)

pyros.init("template-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.VIDEORESIZE:
            pyros.gccui.screenResized(event.size)

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)
    pyros.agent.keepAgents()
    pyros.gccui.background(True)

    # noinspection PyRedeclaration
    hpos = 40
    hpos = pyros.gccui.drawKeyValue("Running", str(running), 8, hpos)

    loc = arrow_image.get_rect().center
    rot_arrow_image = pygame.transform.rotate(arrow_image, -gyroAngle)
    rot_arrow_image.get_rect().center = loc
    screen.blit(rot_arrow_image, (530, 200))

    # if len(rotSpeeds) > 0:
    #     gyroDegPersSecText = str(round(sum(rotSpeeds) / len(rotSpeeds), 2))
    #     pyros.gccui.drawBigText(gyroDegPersSecText, (440, 10))
    #
    #     pyros.gccui.drawText("º/s", (445 + pyros.gccui.bigFont.size(gyroDegPersSecText)[0], 15))
    #
    #     pyros.gccui.drawBigText(str(int(thisGyroAngle)), (440, 40))

    pyros.gccui.drawSmallText("Put help here", (8, screen.get_height() - pyros.gccui.smallFont.get_height()))

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()

    now = time.time()
