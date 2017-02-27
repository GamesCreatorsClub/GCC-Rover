
import sys
import math
import pygame
import pyros
import pyros.gcc
import pyros.pygamehelper

SCALE = 10

pygame.init()
bigFont = pygame.font.SysFont("arial", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600, 600))

stopped = False
received = True

distances = {}


def parseDistances(p):
    for pair in p.split(","):
        split = pair.split(":")
        distances[float(split[0])] = float(split[1])


def handleMoveResponse(topic, message, groups):

    if message == "done-move":
        print("moved")
        pyros.publish("sensor/distance/scan", "scan")
    if message == "done-turn":
        print("turned")
        pyros.publish("move/forward", "30")


def handleSensorDistance(topic, message, groups):
    global received, angle

    print("** distance = " + message)
    parseDistances(message)
    received = True

    move()
    angle = 0
    largestDist = 0
    for d in distances:
        if distances[d] > largestDist:
            angle = float(d)
            largestDist = distances[d]
    print(" LARGEST DISTANCE = angle: " + str(angle) + " | distance: " + str(largestDist))

    if angle != 0:
        pyros.publish("move/rotate", int(angle))
    else:
        pyros.publish("move/forward", "30")


def move():
    pass


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
    global stopped, received, angle

    if key == pygame.K_ESCAPE:
        pyros.publish("drive", "stop")
        pyros.loop(0.7)
        sys.exit()
    elif key == pygame.K_SPACE:
        if not stopped:
            pyros.publish("drive", "stop")
            stopped = True
        if not stopped:
            stopped = True
    elif key == pygame.K_RETURN:
        if received:
            pyros.publish("sensor/distance/scan", "scan")
            print("** asked for distance")
    elif key == pygame.K_s:
        if received:
            received = False
            pyros.publish("sensor/distance/read", str(angle))
            print("** asked for distance")
    elif key == pygame.K_o:
        angle -= 1
        if angle < -90:
            angle = -90
    elif key == pygame.K_p:
        angle += 1
        if angle > 90:
            angle = 90
    else:
        pyros.gcc.handleConnectKeys(key)


def onKeyUp(key):
    return


angle = 0

pyros.subscribe("move/response", handleMoveResponse)
pyros.subscribe("sensor/distance", handleSensorDistance)
pyros.init("maze-client-#", unique=True, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)

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

    text = bigFont.render("Stopped: " + str(stopped), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 80, 0, 0))

    drawRadar()

    pygame.display.flip()
    frameclock.tick(30)
