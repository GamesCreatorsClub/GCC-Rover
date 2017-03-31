
import sys
import math
import pygame
import pyros
import pyros.gcc
import pyros.pygamehelper

SCALE = 10
WHITE = (255, 255, 255)

pygame.init()
font = pygame.font.SysFont("arial", 24)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600, 600))

received = False

distances = {}


def parseDistances(p):
    distances.clear()
    for pair in p.split(","):
        split = pair.split(":")
        distances[float(split[0])] = float(split[1])


def handleSensorDistance(topic, message, groups):
    global received, angle

    print("** distance = " + message)
    parseDistances(message)
    received = True

    angle = 0
    largestDist = 0
    for d in distances:

        if distances[d] > largestDist:
            angle = float(d)
            largestDist = distances[d]
    print(" LARGEST DISTANCE = angle: " + str(angle) + " | distance: " + str(largestDist))


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


def onKeyDown(key):
    global angle

    if key == pygame.K_ESCAPE:
        sys.exit()
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
        pyros.gcc.handleConnectKeys(key)


def onKeyUp(key):
    return


angle = 0

pyros.subscribe("sensor/distance", handleSensorDistance)
pyros.init("radar-client-#", unique=True, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)

    screen.fill((0, 0, 0))

    if pyros.isConnected():
        text = font.render("Connected to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (128, 255, 128))
    else:
        text = font.render("Connecting to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (255, 128, 128))

    screen.blit(text, (0, 0))

    screen.blit(font.render("Angle (o, p): " + str(angle), 1, WHITE), (0, 80))

    distanceStr = "---"
    if angle in distances:
        distanceStr = str(distances[angle])
    screen.blit(font.render("Distance (r, s): " + str(distanceStr), 1, WHITE), (300, 80))

    drawRadar()

    pygame.display.flip()
    frameclock.tick(30)
