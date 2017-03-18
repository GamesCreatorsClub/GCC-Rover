
import sys
import time
import pygame
import pyros
import pyros.gcc
import pyros.agent
import pyros.pygamehelper

MAX_PING_TIMEOUT = 1

INITIAL_SPEED = 20
INITIAL_GAIN = 1

gain = INITIAL_GAIN
speed = INITIAL_SPEED

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
    stop()


def sanitise(distance):
    # distance -= 100
    if distance < 2:
        distance = 2
    return distance


def toFloatString(f):
    r = str(round(f, 1))
    if "." not in r:
        return r + ".0"
    return r


def handleSensorDistance(topic, message, groups):
    global distanceAtAngle

    # print("** distance = " + message)
    if "," in message:
        pass
    else:
        split = message.split(":")
        d = float(split[1])
        if d >= 0:
            distanceAtAngle = sanitise(d)



def stop():
    global run
    pyros.publish("maze/command", "stop")
    run = False


def start():
    global run
    pyros.publish("maze/command", "start")
    run = True


def onKeyDown(key):
    global run, angle, speed, gain

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
        pyros.publish("maze/speed", int(speed))
    elif key == pygame.K_UP:
        speed += 1
        if speed > 100:
            speed = 100
        pyros.publish("maze/speed", int(speed))
    elif key == pygame.K_LEFT:
        gain -= 0.1
        if gain < 1:
            gain = 1
        pyros.publish("maze/gain", int(round(gain, 1)))
    elif key == pygame.K_RIGHT:
        gain += 0.1
        if gain > 10:
            gain = 10
        pyros.publish("maze/gain", int(round(gain, 1)))

    else:
        pyros.gcc.handleConnectKeys(key)


def onKeyUp(key):
    return


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

    text = bigFont.render("Selected: " + str(driveAngle), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 200, 0, 0))

    text = bigFont.render("Gain: " + str(round(gain, 1)), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(300, 200, 0, 0))

    pygame.display.flip()
    frameclock.tick(30)

    if time.time() - pingLastTime > MAX_PING_TIMEOUT:
        pyros.publish("maze/ping", "")
