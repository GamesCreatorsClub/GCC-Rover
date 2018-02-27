
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

CALIBRATION_TIME = 1
X_COLOUR = (128, 255, 128)
Y_COLOUR = (255, 128, 255)

POS_ZOOM = 4.0
VEL_ZOOM = 10.0

MAX_DATA_SIZE = 100000

screen = pyros.gccui.initAll((800, 800), True)
font = pyros.gccui.font
bigFont = pyros.gccui.bigFont

arrow_image = pygame.image.load("arrow.png")

calibrationStarted = None
calibrationSteps = 0

accelX = {
    "accel": 0.0,
    "vel": 0.0,
    "pos": 0.0,
    "offset": 0.0,
    "dt": 0.0,
    "data": [],
    "datav": [],
    "dp": -1,
    "dz": 1,
    "dyz": 50,
    "dyzv": 10
}

accelY = {
    "accel": 0.0,
    "vel": 0.0,
    "pos": 0.0,
    "offset": 0.0,
    "dt": 0.0,
    "data": [],
    "datav": [],
    "dp": -1,
    "dz": 1,
    "dyz": 50,
    "dyzv": 10
}

selectedAxis = accelY


def connected():
    pyros.publish("sensor/accel/continuous", "")
    startCalibration()


def handleAccelData(topic, message, groups):
    global calibrationSteps, calibrationStarted

    data = message.split(",")
    # print("Received data " + str(data))

    dt = float(data[3])

    x = float(data[0])
    y = float(data[1])

    oldXV = accelX["vel"]
    xo = x - accelX["offset"]
    accelX["accel"] = xo
    accelX["vel"] += xo * dt
    avgVX = (oldXV + accelX["vel"]) / 2
    accelX["pos"] += avgVX * dt

    accelX["data"].append(xo)
    accelX["datav"].append(accelX["vel"])

    oldYV = accelY["vel"]
    yo = y - accelY["offset"]
    accelY["accel"] = yo
    accelY["vel"] += yo * dt
    avgVY = (oldXV + accelY["vel"]) / 2
    accelY["pos"] += avgVY * dt

    accelY["data"].append(yo)
    accelY["datav"].append(accelY["vel"])

    if len(accelX["data"]) > MAX_DATA_SIZE:
        del accelX["data"][0]
        del accelX["datav"][0]
        del accelY["data"][0]
        del accelY["datav"][0]

    if calibrationStarted is not None:
        calibrationSteps += 1
        accelX["avg"] += x
        accelY["avg"] += y

        now = time.time()
        if now - calibrationStarted >= CALIBRATION_TIME:
            calibrationStarted = None
            accelX["offset"] = accelX["avg"] / calibrationSteps
            accelY["offset"] = accelY["avg"] / calibrationSteps
            accelX["vel"] = 0.0
            accelY["vel"] = 0.0

            print("Calibration finished. X offset " + str(accelX["offset"]) + ", Y offset " + str(accelY["offset"]))


def resetAll():
    accelX["vel"] = 0.0
    accelX["pos"] = 0.0
    accelY["vel"] = 0.0
    accelY["pos"] = 0.0


def startCalibration():
    global calibrationStarted, calibrationSteps

    calibrationSteps = 0
    resetAll()
    accelX["avg"] = 0.0
    accelY["avg"] = 0.0
    calibrationStarted = time.time()


def onKeyDown(key):
    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif key == pygame.K_ESCAPE:
        sys.exit()
    elif key == pygame.K_r:
        resetAll()
    elif key == pygame.K_c:
        startCalibration()


def onKeyUp(key):
    if pyros.gcc.handleConnectKeyUp(key):
        pass


def drawAxle(txt, axle, y, colour):
    x = 20
    t = bigFont.render(txt + " vel: ", 1, colour)
    screen.blit(t, (x, y))
    x += t.get_width()

    t = bigFont.render(str(round(axle["vel"], 2)), 1, colour)
    screen.blit(t, (x + 50 - t.get_width() / 2, y))

    x += 120
    t = bigFont.render("pos: ", 1, colour)
    screen.blit(t, (x, y))
    x += t.get_width()

    t = bigFont.render(str(round(axle["pos"], 2)), 1, colour)
    screen.blit(t, (x + 50 - t.get_width() / 2, y))

    x += 120

    t = bigFont.render("off: ", 1, X_COLOUR)
    screen.blit(t, (x, y))
    x += t.get_width()

    t = bigFont.render(str(round(axle["offset"], 2)), 1, colour)
    screen.blit(t, (x + 50 - t.get_width() / 2, y))

    x += 120

    if calibrationStarted is not None:
        t = bigFont.render("calibrating", 1, colour)
        screen.blit(t, (x, y))

    return y + 30


def drawPos(x, y, w):
    pygame.draw.rect(screen, (128, 128, 128), (pygame.Rect(x, y, w, w)))
    pygame.draw.rect(screen, (255, 255, 255), (pygame.Rect(accelX["pos"] * POS_ZOOM + x + w / 2, accelY["pos"] * POS_ZOOM + y + w / 2, 5, 5)))


def drawVel(axle, colour, x, y, w, h):

    t = bigFont.render(str(round(axle["vel"], 2)), 1, colour)
    screen.blit(t, (x + (w - t.get_width()) / 2, y))

    th = t.get_height()
    y += th
    rh = h - th - 2

    pygame.draw.rect(screen, (128, 128, 128), (pygame.Rect(x, y + 2, w, rh)))

    pygame.draw.rect(screen, (64, 64, 64), (pygame.Rect(x, y + rh / 2 - 1, w, 2)))

    pygame.draw.rect(screen, colour, (pygame.Rect(x + w / 10, axle["vel"] * VEL_ZOOM + y + rh / 2 - 2, w * 0.8, 4)))


def drawGraph(axle, colour, x, y, w, h, velocity):
    pygame.draw.rect(screen, (128, 128, 128), (pygame.Rect(x, y, w, h)))
    pygame.draw.line(screen, (32, 32, 32), (x, y + h / 2), (x + w - 1, y + h / 2))
    x += 2
    y += 2
    w -= 4
    h -= 4
    if velocity:
        data = axle["datav"]
        dyz = axle["dyzv"]
    else:
        data = axle["data"]
        dyz = axle["dyz"]

    dp = axle["dp"]
    dz = axle["dz"]

    if dp < 0:
        dp = len(data) - w * dz
        if dp < 0:
            dp = 0

    ly = None
    loop = True
    while dp < len(data) and w > 0:
        d = 0.0
        p = dz
        while p > 0:
            d += data[dp]
            dp += 1
            p -= 1
        d /= dz
        ny = y + h / 2 + d * dyz
        if ny < y:
            ny = y
        if ny > y + h - 1:
            ny = y + h - 1

        if ly is not None:
            pygame.draw.line(screen, colour, (x - 1, ly), (x, ny))
        ly = ny
        x += 1
        w -= 1


pyros.subscribe("sensor/accel", handleAccelData)
pyros.init("accel-display-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)


resubscribe = time.time()

while True:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)
    pyros.gccui.background(True)

    cy = 50
    cy = drawAxle("X", accelX, cy, X_COLOUR)
    cy += 4

    cy = drawAxle("Y", accelY, cy, Y_COLOUR)
    cy += 10
    drawGraph(accelX, X_COLOUR, 10, cy, 780, 100, False)
    cy += 100

    cy += 10
    drawGraph(accelX, X_COLOUR, 10, cy, 780, 100, True)
    cy += 100

    cy += 10
    drawGraph(accelY, Y_COLOUR, 10, cy, 780, 100, False)
    cy += 100

    cy += 10
    drawGraph(accelY, Y_COLOUR, 10, cy, 780, 100, True)
    cy += 100

    cy += 10
    drawPos(10, cy, 200)
    drawVel(accelX, X_COLOUR, 220, cy, 60, 200)
    drawVel(accelY, Y_COLOUR, 290, cy, 60, 200)
    cy = cy + 210

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()

    if time.time() - resubscribe > 2:
        resubscribe = time.time()
        if pyros.isConnected():
            pyros.publish("sensor/accel/continuous", "")
