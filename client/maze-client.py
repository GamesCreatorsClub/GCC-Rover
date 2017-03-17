
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

MAX_ROTATE_DISTANCE = 500
INITIAL_SPEED = 15
INITIAL_TURNING_RADIUS = 180

angle = 0
speed = INITIAL_SPEED
turningRadius = INITIAL_TURNING_RADIUS
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

run = True
received = True

distances = {}

nextState = None
corridorWidth = 0
idealDistance = 0


gain = 4
continuousCounter = 0


def doNothing():
    pass


def sanitise(distance):
    distance -= 100
    if distance < 2:
        distance = 2
    return distance


def parseDistances(p):
    distances.clear()
    for pair in p.split(","):
        split = pair.split(":")
        distances[float(split[0])] = sanitise(float(split[1]))


def handleMoveResponse(topic, message, groups):

    if message.startswith("done-turn"):
        print("** Turned!")

    if message.startswith("done-move"):
        print("** Moved!")
        pyros.publish("sensor/distance/scan", "scan")
        print("** Asked for distance scan")


def handleSensorDistance(topic, message, groups):
    global received, angle, driveAngle, distanceAtAngle
    global smallestDist, smallestDistAngle, largestDist, largestDistAngle

    # print("** distance = " + message)
    if "," in message:
        parseDistances(message)
    else:
        split = message.split(":")
        d = float(split[1])
        if d >= 0:
            distances[float(split[0])] = sanitise(d)

    received = True
    if nextState is not None:
        nextState()


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


def stop():
    global run, nextState
    nextState = doNothing
    run = False
    pyros.publish("move/stop", "stop")


def start():
    global run, nextState
    run = True
    nextState = preStartInitiateRightScan
    preStartInitiateLeftScan()


def preStartInitiateLeftScan():
    global nextState
    nextState = preStartInitiateRightScan
    pyros.publish("sensor/distance/read", str(-90))


def preStartInitiateRightScan():
    global nextState
    nextState = preStartWarmUp
    pyros.publish("sensor/distance/read", str(90))


def preStartWarmUp():
    global corridorWidth, idealDistance, nextState

    nextState = goForward

    corridorWidth = distances[-90.0] + distances[90.0]

    idealDistance = (corridorWidth / 2) * math.sqrt(2)

    print("Corridor is " + str(corridorWidth) + "mm wide. Ideal distance=" + str(idealDistance))
    pyros.publish("sensor/distance/read", str(-45))
    pyros.publish("sensor/distance/continuous", "start")


def goForward():
    global nextState

    distance = distances[-45.0]

    if abs(distance) > idealDistance * 1.25:
        print("FORWARD: Got distance " + str(distance) + ", waiting for end of the wall...")
        pyros.publish("move/steer", str(int(-MAX_ROTATE_DISTANCE * 3)) + " " + str(speed))
        pyros.publish("sensor/distance/read", str(-90))
        nextState = waitForTurning
    else:
        delta = idealDistance - distance

        if delta >= 0:
            rotateDistance = MAX_ROTATE_DISTANCE - delta * gain
            if rotateDistance < 100:
                rotateDistance = 100
        else:
            rotateDistance = -MAX_ROTATE_DISTANCE - delta * gain
            if rotateDistance > -100:
                rotateDistance = -100

        print("FORWARD: Got distance " + str(distance) + " where delta is " + str(delta) + " steering at distance " + str(rotateDistance))

        pyros.publish("move/steer", str(int(rotateDistance)) + " " + str(speed))
    doContinuousRead()


def waitForTurning():
    global nextState

    distance = distances[-90.0]

    if abs(distance) > idealDistance * 0.75:
        print("WAIT: Got distance " + str(distance) + ", starting turning at steering distance " + str(-turningRadius))
        pyros.publish("move/steer", str(int(-turningRadius)) + " " + str(speed))

        nextState = turning
    else:
        print("WAIT: Got distance " + str(distance) + ", waiting...")

    doContinuousRead()


def turning():
    global nextState

    distance = distances[-90.0]

    if abs(distance) < idealDistance * 0.75:
        print("TURN: Got distance " + str(distance) + ", back to hugging the wall")
        pyros.publish("sensor/distance/read", str(-45))

        nextState = goForward
    else:
        print("TURN: Got distance " + str(distance) + ", turning...")

    doContinuousRead()



def doContinuousRead():
    global continuousCounter
    continuousCounter += 1
    if continuousCounter > 10:
        pyros.publish("sensor/distance/continuous", "start")
        continuousCounter = 0


def onKeyDown(key):
    global run, received, angle, speed, turningRadius

    if key == pygame.K_ESCAPE:
        stop()
        pyros.loop(0.7)
        sys.exit()
    elif key == pygame.K_SPACE:
        stop()
    elif key == pygame.K_RETURN:
        print("** Starting...")
        run = True
        start()
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
    elif key == pygame.K_DOWN:
        speed -= 1
        if speed < 1:
            speed = -1
    elif key == pygame.K_UP:
        speed += 1
        if speed > 100:
            speed = 100
    elif key == pygame.K_LEFT:
        turningRadius -= 10
        if turningRadius <= 0:
            turningRadius = 0
    elif key == pygame.K_RIGHT:
        turningRadius += 10
        if turningRadius > 400:
            turningRadius = 400

    else:
        pyros.gcc.handleConnectKeys(key)


def onKeyUp(key):
    return


def connected():
    stop()


pyros.subscribe("move/feedback", handleMoveResponse)
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

    text = bigFont.render("Stopped: " + str(not run), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 80, 0, 0))

    text = bigFont.render("Angle: " + str(angle), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 120, 0, 0))

    text = bigFont.render("Speed: " + str(speed), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(300, 120, 0, 0))

    text = bigFont.render("Dist: " + str(distanceAtAngle), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 160, 0, 0))

    text = bigFont.render("turningRadius: " + str(turningRadius), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(300, 160, 0, 0))

    text = bigFont.render("Selected: " + str(driveAngle), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 200, 0, 0))

    drawRadar()

    pygame.display.flip()
    frameclock.tick(30)
