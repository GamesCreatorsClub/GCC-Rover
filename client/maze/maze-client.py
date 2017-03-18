
import sys
import time
import pygame
import pyros
import pyros.gcc
import pyros.agent
import pyros.pygamehelper

MAX_PING_TIMEOUT = 1
MAX_ROTATE_DISTANCE = 500

INITIAL_SPEED = 15
INITIAL_TURNING_RADIUS = 180
INITIAL_GAIN = 4

gain = INITIAL_GAIN
speed = INITIAL_SPEED
turningRadius = INITIAL_TURNING_RADIUS

pingLastTime = 0

angle = 0
distanceAtAngle = 0

run = False

driveAngle = 0
pygame.init()
bigFont = pygame.font.SysFont("arial", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600, 600))


def connected():
    pyros.agent.init(pyros.client, "maze-agent.py")
    pyros.publish("maze/ping", "")
    pyros.publish("maze/gain", str(gain))
    pyros.publish("maze/speed", str(speed))
    pyros.publish("maze/radius", str(turningRadius))
    stop()


def handleMoveResponse(topic, message, groups):

    if message.startswith("done-turn"):
        print("** Turned!")

    if message.startswith("done-move"):
        print("** Moved!")
        pyros.publish("sensor/distance/scan", "scan")
        print("** Asked for distance scan")


def stop():
    global run
    pyros.publish("maze/command", "stop")
    run = False


def start():
    global run
    pyros.publish("maze/command", "start")
    run = True


def onKeyDown(key):
    global run, angle, speed, turningRadius

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

    text = bigFont.render("Turning Radius: " + str(turningRadius), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(300, 160, 0, 0))

    text = bigFont.render("Selected: " + str(driveAngle), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 200, 0, 0))

    text = bigFont.render("Gain: " + str(gain), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(300, 200, 0, 0))

    pygame.display.flip()
    frameclock.tick(30)

    if time.time() - pingLastTime > MAX_PING_TIMEOUT:
        pyros.publish("maze/ping", "")
