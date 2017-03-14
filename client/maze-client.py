
import sys
import math
import pygame
import pyros
import pyros.gcc
import pyros.agent
import pyros.pygamehelper

COMFORTABLE_DISTANCE = 100
SMALLEST_DISTANCE = 60
DISTANCE = 10
SCALE = 10

angle = 0
distanceAtAngle = 0
smallestDist = 0
smallestDistAngle = 0
largestDist = 0
largestDistAngle = 0


driveAngle = 0
pygame.init()
bigFont = pygame.font.SysFont("arial", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600, 600))

stopped = True
received = True

distances = {}


def connected():
    pyros.agent.init(pyros.client, "playground/drive/fine-drive-agent.py")


def sanitise(distance):
    distance -= 100
    if distance < 20:
        distance = 20
    return distance


def parseDistances(p):
    distances.clear()
    for pair in p.split(","):
        split = pair.split(":")
        distances[float(split[0])] = sanitise(float(split[1]))


def handleMoveResponse(topic, message, groups):

    if message.startswith("done-turn"):
        print("** Turned!")
        move()

    if message.startswith("done-move"):
        print("** Moved!")
        pyros.publish("sensor/distance/scan", "scan")
        print("** Asked for distance scan")


def handleSensorDistance(topic, message, groups):
    global received, angle, driveAngle, distanceAtAngle
    global smallestDist, smallestDistAngle, largestDist, largestDistAngle

    print("** distance = " + message)
    if "," in message:
        parseDistances(message)
    else:
        split = message.split(":")
        distances[float(split[0])] = sanitise(float(split[1]))
        print("** Got " + message)
        distanceAtAngle = distances[angle]

    received = True
    largestDist = 0
    largestDistAngle = 0
    smallestDist = 2000
    smallestDistAngle = 0
    for d in distances:
        if distances[d] > largestDist:
            largestDistAngle = float(d)
            largestDist = distances[d]
        if distances[d] < smallestDist:
            smallestDistAngle = float(d)
            smallestDist = distances[d]

    print("** LARGEST  DISTANCE @ angle: " + str(largestDistAngle) + " | distance: " + str(largestDist))
    print("** SMALLEST DISTANCE @ angle: " + str(smallestDistAngle) + " | distance: " + str(smallestDist))

    selectedAngle = largestDistAngle

    # if smallestDist < SMALLEST_DISTANCE:
    #     if smallestDistAngle > 0:
    #         driveAngle = smallestDistAngle - 45
    #     else:
    #         driveAngle = smallestDistAngle + 45

    if selectedAngle != -90 and selectedAngle != 90:
        if distances[selectedAngle - 22.5] < COMFORTABLE_DISTANCE:
            selectedAngle += 22.5
        elif distances[selectedAngle + 22.5] < COMFORTABLE_DISTANCE:
            selectedAngle -= 22.5
    elif selectedAngle == -90:
        selectedAngle += 22.5
    elif selectedAngle == 90:
        selectedAngle -= 22.5

    driveAngle = selectedAngle

    if not stopped:
        goOneStep()


def goOneStep():
    global driveAngle

    if driveAngle != 0:
        pyros.publish("finemove/rotate", int(driveAngle))
    else:
        move()


def move():
    pyros.publish("finemove/forward", DISTANCE)


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

        # colour -= 20
        prevAngle = a

    aAngleRadians = math.pi * (180 - angle) / 180

    x = 300 + 500 / SCALE * math.sin(aAngleRadians)
    y = 300 + 500 / SCALE * math.cos(aAngleRadians)

    pygame.draw.line(screen, (128, 255, 128), (300, 300), (x, y), 4)

    dAngleRadians = math.pi * (180 - driveAngle) / 180

    x = 300 + 2200 / SCALE * math.sin(dAngleRadians)
    y = 300 + 2200 / SCALE * math.cos(dAngleRadians)

    pygame.draw.line(screen, (255, 128, 128), (300, 300), (x, y), 2)


def onKeyDown(key):
    global stopped, received, angle

    if key == pygame.K_ESCAPE:
        pyros.publish("finemove/stop", "stop")
        pyros.loop(0.7)
        sys.exit()
    elif key == pygame.K_SPACE:
        pyros.publish("finemove/stop", "stop")
        stopped = True
    elif key == pygame.K_RETURN:
        print("** Starting...")
        pyros.publish("sensor/distance/scan", "scan")
        print("** Asked for distance scan")
        stopped = False
    elif key == pygame.K_g:
        goOneStep()
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
    else:
        pyros.gcc.handleConnectKeys(key)


def onKeyUp(key):
    return


pyros.subscribe("finemove/feedback", handleMoveResponse)
# pyros.subscribe("move/response", handleMoveResponse)
pyros.subscribe("sensor/distance", handleSensorDistance)
pyros.init("maze-client-#", unique=True, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False, onConnected=connected)

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

    text = bigFont.render("Angle: " + str(angle), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 120, 0, 0))

    text = bigFont.render("Dist: " + str(distanceAtAngle), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 160, 0, 0))

    text = bigFont.render("Selected: " + str(driveAngle), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 200, 0, 0))

    drawRadar()

    pygame.display.flip()
    frameclock.tick(30)
