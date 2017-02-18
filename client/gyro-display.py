
import sys
import time
import pygame
import pyros
import pyros.gcc
import pyros.pygamehelper

pygame.init()
bigFont = pygame.font.SysFont("arial", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600, 600))
arrow_image = pygame.image.load("arrow.png")


gyroAngle = 0.0


def connected():
    pyros.publish("sensor/gyro/continuous", "")


def handleGyroData(topic, message, groups):
    global gyroAngle

    data = message.split(",")
    gyroAngle += float(data[2])


def onKeyDown(key):
    if key == pygame.K_ESCAPE:
        sys.exit()
    else:
        pyros.gcc.handleConnectKeys(key)


def onKeyUp(key):
    return


pyros.subscribe("sensor/gyro", handleGyroData)
pyros.init("gyro-display-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort())


resubscribe = time.time()

while True:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)

    screen.fill((0, 0, 0))

    if pyros.isConnected():
        text = bigFont.render("Connected to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (128, 255, 128))
    else:
        text = bigFont.render("Connecting to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (255, 128, 128))

    screen.blit(text, (0, 0))

    loc = arrow_image.get_rect().center
    rot_arrow_image = pygame.transform.rotate(arrow_image, -gyroAngle)
    rot_arrow_image.get_rect().center = loc

    screen.blit(rot_arrow_image, (150, 150))

    pygame.display.flip()
    frameclock.tick(30)

    if time.time() - resubscribe > 2:
        resubscribe = time.time()
        if pyros.isConnected():
            pyros.publish("sensor/gyro/continuous", "")
