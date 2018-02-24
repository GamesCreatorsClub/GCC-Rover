#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import array
import math
import struct
import threading
import time
import traceback
from fcntl import ioctl

import pyroslib as pyros

DEBUG_AXES = False
DEBUG_BUTTONS = False
DEBUG_JOYSTICK = False
EXPO = 0.5

global dividerR, dividerL, lastDividerR, lastDividerL
lastDividerL = 1
lastDividerR = 1
dividerL = 1
dividerR = 1

# We'll store the states here.
axis_states = {}
button_states = {}

# These constants were borrowed from linux/input.h
axis_names = {
    0x00: 'x',
    0x01: 'y',
    # 0x02: 'z',
    0x02: 'rx',
    0x05: 'ry',
    # 0x05: 'rz',
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
    0x120: 'select',
    0x121: 'lbutton',
    0x122: 'rbutton',
    0x123: 'start',
    0x124: 'lup',
    0x125: 'lright',
    0x126: 'ldown',
    0x127: 'lleft',
    0x128: 'tl1',
    0x129: 'tr1',
    0x12a: 'tl2',
    0x12b: 'tr2',
    0x12c: 'by',
    0x12d: 'ba',
    0x12e: 'bb',
    0x12f: 'bx',
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
    # 0x13a: 'select',
    # 0x13b: 'start',
    # 0x13c: 'mode',
    # 0x13d: 'thumbl',
    # 0x13e: 'thumbr',

    # 0x220: 'dpad_up',
    # 0x221: 'dpad_down',
    # 0x222: 'dpad_left',
    # 0x223: 'dpad_right',

    # XBo 360 controller uses these codes.
    # 0x2c0: 'dpad_left',
    # 0x2c1: 'dpad_right',
    # 0x2c2: 'dpad_up',
    # 0x2c3: 'dpad_down',
}

axis_map = []
button_map = []

# Open the joystick device.

lunge_back_time = 0


def connectToJoystick(printError):
    global fn, jsdev

    try:
        fn = '/dev/input/js0'
        # print('Opening %s...' % fn)
        jsdev = open(fn, 'rb')

        # Get the device name.
        # buf = bytearray(63)
        # buf = array.array('c', ['\0'] * 64)

        buf = array.array('b', [0] * 64)

        ioctl(jsdev, 0x80006a13 + (0x10000 * len(buf)), buf)  # JSIOCGNAME(len)
        js_name = buf.tostring()
        print('Device name: %s' % js_name)

        # Get number of axes and buttons.
        buf = array.array('B', [0])
        ioctl(jsdev, 0x80016a11, buf)  # JSIOCGAXES
        num_axes = buf[0]

        buf = array.array('B', [0])
        ioctl(jsdev, 0x80016a12, buf)  # JSIOCGBUTTONS
        num_buttons = buf[0]

        # Get the axis map.
        buf = array.array('B', [0] * 0x40)
        ioctl(jsdev, 0x80406a32, buf)  # JSIOCGAXMAP

        for axis in buf[:num_axes]:
            axis_name = axis_names.get(axis, '0x%02x' % axis)
            axis_map.append(axis_name)
            axis_states[axis_name] = 0.0

        # Get the button map.
        buf = array.array('H', [0] * 200)
        ioctl(jsdev, 0x80406a34, buf)  # JSIOCGBTNMAP

        for btn in buf[:num_buttons]:
            btn_name = button_names.get(btn, '0x%03x' % btn)
            button_map.append(btn_name)
            button_states[btn_name] = 0

        print('%d axes found: %s' % (num_axes, ', '.join(axis_map)))
        print('%d buttons found: %s' % (num_buttons, ', '.join(button_map)))
        return True
    except Exception as e:
        if printError:
            print("Failed to connect to joystick" + str(e))

        return False
    except BaseException as e:
        if printError:
            print("Failed to connect to joystick - no exception given " + str(e))

        return False


def readEvents():
    reconnect = True
    noError = True

    while True:
        if reconnect:
            connected = connectToJoystick(noError)
            if connected:
                reconnect = False
                noError = True
            else:
                noError = False
            time.sleep(0.5)
        else:
            try:
                evbuf = jsdev.read(8)
                if evbuf:
                    time_of_event, value, event_type, number = struct.unpack('IhBB', evbuf)

                    if event_type & 0x01:
                        button = button_map[number]
                        if button:
                            button_states[button] = value

                    if event_type & 0x02:
                        selected_axis = axis_map[number]
                        if selected_axis:
                            fvalue = value / 32767.0
                            axis_states[selected_axis] = fvalue
            except BaseException as e:
                print("Failed to read joystick " + str(e))
                reconnect = True
                time.sleep(0.2)


def startReadEventsLoopThread():
    thread = threading.Thread(target=readEvents, args=())
    thread.daemon = True
    thread.start()


startReadEventsLoopThread()

topSpeed = 50
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


def processButtons():
    global lastX3, lastY3, lastSelect, lastStart
    global lastTL, lastTL2, lastTR, lastTR2, lastA, lastB, lastBX, lastBY, lastDividerL, lastDividerR
    global lastLButton, lastRButton, dividerL, dividerR

    global topSpeed, prepareToOrbit, continueToReadDistance, doOrbit, boost, kick, lastBoost

    # print("Axis states: " + str(axis_states))

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
        lastDividerR = dividerR
        if rbutton:
            dividerR = 4
        else:
            dividerR = 1
        lastDividerL = dividerL
        if lbutton:
            dividerL = 4
        else:
            dividerL = 1

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
        lastBoost = boost
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
            print("ERR Axis states: " + str(axis_states) + str(e))


def calcRoverSpeed(speed):
    if boost or lunge_back_time > 0:
        # spd = int(speed * topSpeed * 2)
        # if spd > 300:
        if speed > 0:
            spd = 300
        elif speed < 0:
            spd = -300
        else:
            spd = 0
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
    global kick, lastX1, lastY1, lastX2, lastY2, lastNoChange, lastTopSpeed, dividerR, dividerL, lastDividerR, lastDividerL, boost, lastBoost, lunge_back_time



    lx = float(axis_states["x"])
    ly = float(axis_states["y"])

    tr = button_states["tr1"]

    rx = float(axis_states["rx"])
    ry = float(axis_states["ry"])

    if ry < 0.1 and ry > -0.1 and rx < 0.1 and rx > -0.1 and ly < 0.1 and ly > -0.1 and lx < 0.1 and lx > -0.1:
        if boost:
            lunge_back_time += 1
            if lunge_back_time > 6:
                lunge_back_time = 6
            ry = -1
        else:
            if lunge_back_time > 0:
                lunge_back_time -= 1
                ry = 1
    else:
        if not ry > -0:
            lunge_back_time = 0


    if lx == lastX1 and ly == lastY1 and rx == lastX2 and ry == lastY2 and topSpeed == lastTopSpeed and lastNoChange == 0 and boost == lastBoost:
        pass
    else:
        if lx == lastX1 and ly == lastY1 and rx == lastX2 and ry == lastY2 and topSpeed == lastTopSpeed and dividerR == lastDividerR and dividerL == lastDividerL and boost == lastBoost:
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
            pyros.publish("move/drive", str(round(ra, 1)) + " " + str(int(roverSpeed / dividerR)))
            if DEBUG_JOYSTICK:
                print("Driving a:" + str(round(ra, 1)) + " s:" + str(roverSpeed) + " ld:" + str(ld) + " rd:" + str(rd))
        elif ld > 0.1 and rd > 0.1:

            ory = ry
            olx = lx
            ry = calculateExpo(ry, EXPO)

            lx = calculateExpo(lx, EXPO)

            roverSpeed = -calcRoverSpeed(ry)
            roverTurningDistance = calcRoverDistance(lx)
            pyros.publish("move/steer", str(roverTurningDistance) + " " + str(int(roverSpeed / 2 / dividerR)))
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
                lx = calculateExpo(lx, EXPO) / 2
                roverSpeed = calcRoverSpeed(lx)
                pyros.publish("move/rotate", int(roverSpeed / dividerL))
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


def handleDistance(topic, message, groups):
    global sensorDistance, prepareToOrbit

    # print("** distance = " + message)
    if "," in message:
        pass
    else:
        split = message.split(":")
        d = float(split[1])
        if d >= 0:
            sensorDistance = d

        if prepareToOrbit:
            prepareToOrbit = False


# Main event loop
def loop():
    processButtons()
    processJoysticks()


if __name__ == "__main__":
    try:
        print("Starting jcontroller service...")

        pyros.subscribe("sensor/distance", handleDistance)
        pyros.init("jcontroller-service")

        print("Started jcontroller service.")

        pyros.forever(0.1, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
