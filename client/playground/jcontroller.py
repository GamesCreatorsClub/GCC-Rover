#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import subprocess
import sys
import time
import math
import pygame

import pyros
import pyros.gcc
import pyros.gccui
import pyros.agent
import pyros.pygamehelper


DEBUG_AXES = True
DEBUG_BUTTONS = False
DEBUG_JOYSTICK = True
MAX_PING_TIMEOUT = 1

EXPO = 0.5


pingLastTime = 0

pyros.gccui.initAll((600, 250), True)

screen = pyros.gccui.screen

bigFont = pyros.gccui.bigFont
font = pyros.gccui.font

arrow_image = pygame.image.load("arrow.png")
arrow_image = pygame.transform.scale(arrow_image, (50, 50))

useGyro = False

gyroAngle = 0
gyroLastAngle = 0
gyroLastReadTime = 0
gyroDegPersSec = 0
gyroDegPersSecText = ""

axis_states = {}
button_states = {}

# These constants were borrowed from linux/input.h
axis_names = {
    0x00: 'x',
    0x01: 'y',
    0x02: 'z',
    0x03: 'rx',
    0x04: 'ry',
    0x05: 'rz',
    0x06: 'trottle',
    0x07: 'rudder',
    0x08: 'wheel',
    0x09: 'gas',
    0x0a: 'brake',
    0x10: 'hat0x',
    0x11: 'hat0y',
    0x12: 'hat1x',
    0x13: 'hat1y',
    0x14: 'hat2x',
    0x15: 'hat2y',
    0x16: 'hat3x',
    0x17: 'hat3y',
    0x18: 'pressure',
    0x19: 'distance',
    0x1a: 'tilt_x',
    0x1b: 'tilt_y',
    0x1c: 'tool_width',
    0x20: 'volume',
    0x28: 'misc',
}

button_names = {
    0x120: 'trigger',
    0x121: 'thumb',
    0x122: 'thumb2',
    0x123: 'top',
    0x124: 'top2',
    0x125: 'pinkie',
    0x126: 'base',
    0x127: 'base2',
    0x128: 'base3',
    0x129: 'base4',
    0x12a: 'base5',
    0x12b: 'base6',
    0x12f: 'dead',
    0x130: 'a',
    0x131: 'b',
    0x132: 'c',
    0x133: 'x',
    0x134: 'y',
    0x135: 'z',
    0x136: 'tl',
    0x137: 'tr',
    0x138: 'tl2',
    0x139: 'tr2',
    0x13a: 'select',
    0x13b: 'start',
    0x13c: 'mode',
    0x13d: 'thumbl',
    0x13e: 'thumbr',

    0x220: 'dpad_up',
    0x221: 'dpad_down',
    0x222: 'dpad_left',
    0x223: 'dpad_right',

    # XBo 360 controller uses these codes.
    0x2c0: 'dpad_left',
    0x2c1: 'dpad_right',
    0x2c2: 'dpad_up',
    0x2c3: 'dpad_down',
}

axis_map = []
button_map = []


axis_states["x"] = 0
axis_states["y"] = 0
axis_states["rx"] = 0
axis_states["ry"] = 0

for axis_name in axis_names:
    axis_states[axis_names[axis_name]] = 0.0

for btn_name in button_names:
    button_states[button_names[btn_name]] = 0


topSpeed = 20
sensorDistance = 200

lastNoChange = 0
lastX1 = 0
lastY1 = 0
lastX2 = 0
lastY2 = 0
lastX3 = 0
lastY3 = 0
lastSelect = False
lastStart = False
lastTL = False
lastTL2 = False
lastTR = False
lastTR2 = False
lastA = False
lastB = False
lastBX = False
lastBY = False
lastLButton = False
lastRButton = False
lastTopSpeed = topSpeed

doOrbit = False
prepareToOrbit = False
continueToReadDistance = False
boost = False
kick = 0


axis_states["x"] = 0
axis_states["y"] = 0
axis_states["rx"] = 0
axis_states["ry"] = 0


def drawText(xy, t, s):
    global font

    s.blit(font.render(str(t), 1, pyros.gccui.WHITE), (xy[0], xy[1]))


def drawLine(start, end):
    pygame.draw.line(screen, (255, 255, 255), (start[0] + 20, start[1] + 70), (end[0] + 20, end[1] + 70))


def drawRect(start, end):
    pass # pygame.draw.rect(screen, (255, 255, 255), (start[0], start[1] + 50, end[0], end[1] + 50))


def drawJoysticks():
    x1 = float(axis_states["x"] * 20)
    y1 = float(axis_states["y"] * 20)
    x2 = float(axis_states["rx"] * 20)
    y2 = float(axis_states["ry"] * 20)

    drawLine((x1 + 20, 0), (x1 + 20, 40))
    drawLine((0, y1 + 20),(40, y1 + 20))
    drawLine((87 + x2 + 20, 0), (87 + x2 + 20, 40))
    drawLine((87, y2 + 20), (87 + 40, y2 + 20))

    x3 = float(axis_states["hat0x"])
    y3 = float(axis_states["hat0y"])

    white = (255,255,255)
    if x3 < 0:
        drawRect((0, 50), (7, 57))
        drawRect((16, 50), (23, 57))
    elif x3 > 0:
        drawRect((0, 50), (7, 57))
        drawRect((16, 50), (23, 57))
    else:
        drawRect((0, 50), (7, 57))
        drawRect((16, 50), (23, 57))

    if y3 < 0:
        drawRect((8, 42), (15, 49))
        drawRect((8, 58), (15, 63))
    elif y3 > 0:
        drawRect((8, 42), (15, 49))
        drawRect((8, 58), (15, 63))
    else:
        drawRect((8, 42), (15, 49))
        drawRect((8, 58), (15, 63))


def drawRover():
    drawText((0, 50), "R:", screen)
    drawText((55, 50), "S:", screen)
    drawText((0, 0), "D:", screen)

    x = 80 - 48
    drawText((x, 0), str(sensorDistance), screen)

    if doOrbit:
        drawText((96, 0),"O", screen)
    if prepareToOrbit:
        drawText((105, 0), str("p"), screen)
    if continueToReadDistance:
        drawText((114, 0), str("c"), screen)


def drawTopSpeed(x, y):
    spd = calcRoverSpeed(1)

    if pyros.isConnected():
        x = x - 16
        drawText((x, y), "Speed: " + str(spd), screen)


def doShutdown():
    print("Shutting down now!")
    try:
        subprocess.call(["/usr/bin/sudo", "/sbin/shutdown", "-h", "now"])
    except Exception as exception:
        print("ERROR: Failed to shutdown; " + str(exception))


def processButtons():
    global lastX3, lastY3, lastSelect, lastStart
    global lastTL, lastTL2, lastTR, lastTR2, lastA, lastB, lastBX, lastBY
    global lastLButton, lastRButton

    global topSpeed, prepareToOrbit, continueToReadDistance, doOrbit, boost, kick

    print("Axis states: " + str(axis_states))

    # 4 ly up: "TopBtn2", lx r 5: "PinkieBtn", ly down 6: "BaseBtn", lx left 7:"BaseBtn2"
    # x3 = int(axis_states["hat0x"])
    # y3 = int(axis_states["hat0y"])

    try:
        lup = button_states["lup"]
        lright = button_states["lright"]
        ldown = button_states["ldown"]
        lleft = button_states["lleft"]

        x3 = 0
        y3 = 0
        if lup:
            y3 = -1
        if ldown:
            y3 = 1
        if lleft:
            x3 = -1
        if lright:
            x3 = 1

        tl = button_states["tl1"]
        tl2 = button_states["tl2"]
        tr = button_states["tr1"]
        tr2 = button_states["tr2"]
        a = button_states["ba"]
        bb = button_states["bb"]
        bx = button_states["bx"]
        by = button_states["by"]

        start = button_states["start"]
        select = button_states["select"]

        lbutton = button_states["lbutton"]
        rbutton = button_states["rbutton"]

        if y3 != lastY3:
            if y3 < 0:
                if topSpeed >= 20:
                    topSpeed += 10
                    if topSpeed > 300:
                        topSpeed = 300
                else:
                    topSpeed += 1
            elif y3 > 0:
                if topSpeed <= 20:
                    topSpeed -= 1
                    if topSpeed < 1:
                        topSpeed = 1
                else:
                    topSpeed -= 10

        if x3 != lastX3:
            if x3 > 0:
                topSpeed += 100
                if topSpeed > 300:
                    topSpeed = 300
            elif x3 < 0:
                if topSpeed >= 100:
                    topSpeed -= 100
                    if topSpeed < 30:
                        topSpeed = 30
                elif topSpeed > 50:
                    topSpeed = 50

        if tl and tl != lastTL:
            prepareToOrbit = True
            pyros.publish("sensor/distance/read", "0")

        doOrbit = tl

        continueToReadDistance = tl2
        if tl2 != lastTL2:
            if tl:
                pyros.publish("sensor/distance/continuous", "start")
            else:
                pyros.publish("sensor/distance/continuous", "stop")

        boost = tr

        # kick
        if lastTR2 != tr2:
            if tr2:
                pyros.publish("servo/9", "90")
            else:
                pyros.publish("servo/9", "165")

        if bx and bx != lastBX:
            kick = 1
            # pyros.publish("move/drive", "0 300")
            # pyros.sleep(1)
            # pyros.publish("move/drive", "0 0")

        lastX3 = x3
        lastY3 = y3
        lastStart = start
        lastTL = tl
        lastTL2 = tl2
        lastTR = tr
        lastTR2 = tr2
        lastA = a
        lastB = bb
        lastBX = bx
        lastBY = by
        lastSelect = select
        lastLButton = lbutton
        lastRButton = rbutton

        if DEBUG_BUTTONS:
            print("OK Button states: " + str(button_states))
        if DEBUG_AXES:
            print("OK Axis states: " + str(axis_states))

    except Exception as e:
        if DEBUG_BUTTONS:
            print("ERR Button states: " + str(button_states) + str(e))
        if DEBUG_AXES:
            print("ERR Axis states  : " + str(axis_states) + str(e))


def calcRoverSpeed(speed):
    if boost:
        spd = int(speed * topSpeed * 2)
        if spd > 300:
            spd = 300
        return spd
    else:
        return int(speed * topSpeed)


def calculateExpo(v, expoPercentage):
    if v >= 0:
        return v * v * expoPercentage + v * (1.0 - expoPercentage)
    else:
        return - v * v * expoPercentage + v * (1.0 - expoPercentage)


def calcRoverDistance(distance):
    if distance >= 0:
        distance = abs(distance)
        distance = 1.0 - distance
        distance += 0.2
        distance *= 500
    else:
        distance = abs(distance)
        distance = 1.0 - distance
        distance += 0.2
        distance = - distance * 500

    return int(distance)


def processJoysticks():
    global kick, lastX1, lastY1, lastX2, lastY2, lastNoChange, lastTopSpeed

    lx = float(axis_states["x"])
    ly = float(axis_states["y"])

    rx = float(axis_states["rx"])
    ry = float(axis_states["ry"])

    if lx == lastX1 and ly == lastY1 and rx == lastX2 and ry == lastY2 and topSpeed == lastTopSpeed and lastNoChange == 0:
        pass
    else:
        if lx == lastX1 and ly == lastY1 and rx == lastX2 and ry == lastY2 and topSpeed == lastTopSpeed:
            lastNoChange = lastNoChange - 1
        else:
            lastNoChange = 10

        lastX1 = lx
        lastY1 = ly
        lastX2 = rx
        lastY2 = ry
        lastTopSpeed = topSpeed

        ld = math.sqrt(lx * lx + ly * ly)
        rd = math.sqrt(rx * rx + ry * ry)
        ra = math.atan2(rx, -ry) * 180 / math.pi

        if ld < 0.1 and rd > 0.1:
            distance = rd
            distance = calculateExpo(distance, EXPO)

            roverSpeed = calcRoverSpeed(distance)
            pyros.publish("move/drive", str(round(ra, 1)) + " " + str(int(roverSpeed)))
            if DEBUG_JOYSTICK:
                print("Driving a:" + str(round(ra, 1)) + " s:" + str(roverSpeed) + " ld:" + str(ld) + " rd:" + str(rd))
        elif ld > 0.1 and rd > 0.1:

            ory = ry
            olx = lx
            ry = calculateExpo(ry, EXPO)

            lx = calculateExpo(lx, EXPO)

            roverSpeed = -calcRoverSpeed(ry)
            roverTurningDistance = calcRoverDistance(lx)
            pyros.publish("move/steer", str(roverTurningDistance) + " " + str(int(roverSpeed)))
            if DEBUG_JOYSTICK:
                print("Steering d:" + str(roverTurningDistance) + " s:" + str(roverSpeed) + " ry: " + str(ory) + " lx:" + str(olx) + " ld:" + str(ld) + " rd:" + str(rd))
        elif ld > 0.1:
            if doOrbit and not prepareToOrbit:
                distance = sensorDistance
                if distance > 1000:
                    distance = 1000
                roverSpeed = calcRoverSpeed(lx) / 2.5
                pyros.publish("move/orbit", str(int(sensorDistance + 70)) + " " + str(roverSpeed))
                if DEBUG_JOYSTICK:
                    print("Orbit sen:" + str(int(sensorDistance + 70)) + " s:" + str(roverSpeed) + " ld:" + str(ld) + " rd:" + str(rd))
            else:
                olx = lx
                lx = calculateExpo(lx, EXPO)
                roverSpeed = calcRoverSpeed(lx)
                pyros.publish("move/rotate", int(roverSpeed))
                if DEBUG_JOYSTICK:
                    print("Rotate s:" + str(roverSpeed) + " lx:" + str(olx) + " ld:" + str(ld) + " rd:" + str(rd))
        elif kick > 0:
            if DEBUG_JOYSTICK:
                print("Kick stop:  ld:" + str(ld) + " rd:" + str(rd))
            pass
        else:
            # pyros.publish("move/drive", str(ra) + " 0")
            # if ra != 0:
            #     print("-> move/drive " + str(ra))
            roverSpeed = 0
            pyros.publish("move/stop", "0")

            if DEBUG_JOYSTICK:
                print("Rotate stop:  ld:" + str(ld) + " rd:" + str(rd))


# # Main event loop
# def main():
#     global screenTick
#     pygame.init()
#     screenTick += 1
#     if screenTick >= 5:
#         clear()
#
#         # drawBattery(106, 58, 21)
#         drawConnection(40, 50)
#         drawTopSpeed(105, 50)
#         if screenMode == SCREEN_MONITOR:
#             drawJoysticks()
#         elif screenMode == SCREEN_ROVER:
#             drawRover()
#
#         screenTick = 0
#
#         processKeys()
#         processJoysticks()


def onKeyDown(key):
    global topSpeed, useGyro

    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif key == pygame.K_a:
        axis_states['x'] = -1.0
    elif key == pygame.K_d:
        axis_states['x'] = 1.0
    elif key == pygame.K_w:
        axis_states['y'] = -1.0
    elif key == pygame.K_s:
        axis_states['y'] = 1.0
    elif key == pygame.K_LEFT:
        axis_states['rx'] = -1.0
    elif key == pygame.K_RIGHT:
        axis_states['rx'] = 1.0
    elif key == pygame.K_UP:
        axis_states['ry'] = -1.0
    elif key == pygame.K_DOWN:
        axis_states['ry'] = 1.0
    elif key == pygame.K_MINUS:
        if topSpeed <= 20:
            topSpeed -= 1
            if topSpeed < 1:
                topSpeed = 1
        else:
            topSpeed -= 10
    elif key == pygame.K_EQUALS:
        if topSpeed >= 20:
            topSpeed += 10
            if topSpeed > 300:
                topSpeed = 300
        else:
            topSpeed += 1
    elif key == pygame.K_LEFTBRACKET:
        if topSpeed >= 100:
            topSpeed -= 100
            if topSpeed < 30:
                topSpeed = 30
        elif topSpeed > 50:
            topSpeed = 50
    elif key == pygame.K_RIGHTBRACKET:
        topSpeed += 100
        if topSpeed > 300:
            topSpeed = 300

    elif key == pygame.K_g:
        useGyro = not useGyro

    elif key == pygame.K_c:
        pyros.publish("sensor/gyro/continuous", "calibrate,50")


def onKeyUp(key):

    if pyros.gcc.handleConnectKeyUp(key):
        pass
    elif key == pygame.K_a:
        axis_states['x'] = 0.0
    elif key == pygame.K_d:
        axis_states['x'] = 0.0
    elif key == pygame.K_w:
        axis_states['y'] = 0.0
    elif key == pygame.K_s:
        axis_states['y'] = 0.0
    elif key == pygame.K_LEFT:
        axis_states['rx'] = 0.0
    elif key == pygame.K_RIGHT:
        axis_states['rx'] = 0.0
    elif key == pygame.K_UP:
        axis_states['ry'] = 0.0
    elif key == pygame.K_DOWN:
        axis_states['ry'] = 0.0

    pass


def handleGyroData(topic, message, groups):
    global gyroAngle

    data = message.split(",")

    gyroChange = float(data[2])

    gyroAngle += gyroChange


pyros.subscribe("sensor/gyro", handleGyroData)

pyros.init("gcc-jcontroller-local-#", unique=False, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)


try:
    j = pygame.joystick.Joystick(0)  # create a joystick instance
    j.init() # init instance
    print('Enabled joystick: ' + j.get_name())
    ljx = 0
    ljy = 0
    ljrx = 0
    ljry = 0
except pygame.error:
    print('no joystick found.')

rotSpeeds = []

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.JOYAXISMOTION:    # 7
            if ljx != j.get_axis(0):
                ljx = j.get_axis(0)
                axis_states['x'] = ljx
            if ljy != j.get_axis(1):
                ljy = j.get_axis(1)
                axis_states['y'] = ljy
            if ljrx != j.get_axis(3):
                ljrx = j.get_axis(3)
                axis_states['rx'] = ljx
            if ljry != j.get_axis(4):
                ljry = j.get_axis(4)
                axis_states['ry'] = ljry

            print("x: " + str(axis_states['x']) + " y: " + str(axis_states['y']) + " rx: " + str(axis_states['rx']) + " ry: " + str(axis_states['ry']))
        elif event.type == pygame.JOYBALLMOTION:  # 8
            pass
        elif event.type == pygame.JOYHATMOTION:   # 9
            axis_states['rx'] = j.get_hat(0)
            axis_states['ry'] = j.get_hat(1)
            print("rh: " + str(axis_states['rx']) + " lh: " + str(axis_states['ry']))
        elif event.type == pygame.JOYBUTTONDOWN:  # 10
            pass
        elif event.type == pygame.JOYBUTTONUP:    # 11
            pass

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    processButtons()
    processJoysticks()

    pyros.loop(0.03)

    pyros.gccui.background(True)

    drawTopSpeed(30, 30)

    drawJoysticks()

    now = time.time()
    thisGyroAngle = gyroAngle
    rotSpeed = (gyroLastAngle - thisGyroAngle) / (now - gyroLastReadTime)
    rotSpeeds.append(rotSpeed)
    if len(rotSpeeds) > 30:
        del rotSpeeds[0]

    if useGyro:
        loc = arrow_image.get_rect().center
        rot_arrow_image = pygame.transform.rotate(arrow_image, -gyroAngle)
        rot_arrow_image.get_rect().center = loc
        screen.blit(rot_arrow_image, (450, 50))

        if len(rotSpeeds) > 0:
            gyroDegPersSecText = str(round(sum(rotSpeeds) / len(rotSpeeds), 2))
            pyros.gccui.drawBigText(gyroDegPersSecText, (440, 10))

            pyros.gccui.drawText("º/s", (445 + pyros.gccui.bigFont.size(gyroDegPersSecText)[0], 15))

    gyroLastReadTime = now
    gyroLastAngle = thisGyroAngle

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()

    if useGyro and time.time() - pingLastTime > MAX_PING_TIMEOUT:
        pyros.publish("sensor/gyro/continuous", "start")
        pingLastTime = time.time()
