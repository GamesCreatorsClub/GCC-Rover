#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#


import subprocess
from time import sleep
# from smbus import SMBus
# import RPi.GPIO as GPIO

import math

import pyroslib as pyros
# import pyros.gcc
import threading

import time
import array
import struct
import threading
from fcntl import ioctl


print("starting jcontroller")
disabled = False

# We'll store the states here.
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

# Open the joystick device.

fn = '/dev/input/js0'
print('Opening %s...' % fn)
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
    axis_name = axis_names.get(axis, 'unknown(0x%02x)' % axis)
    axis_map.append(axis_name)
    axis_states[axis_name] = 0.0

# Get the button map.
buf = array.array('H', [0] * 200)
ioctl(jsdev, 0x80406a34, buf)  # JSIOCGBTNMAP

for btn in buf[:num_buttons]:
    btn_name = button_names.get(btn, 'unknown(0x%03x)' % btn)
    button_map.append(btn_name)
    button_states[btn_name] = 0

print('%d axes found: %s' % (num_axes, ', '.join(axis_map)))
print('%d buttons found: %s' % (num_buttons, ', '.join(button_map)))


def readEvents():
    evbuf = jsdev.read(8)
    if evbuf:
        time, value, event_type, number = struct.unpack('IhBB', evbuf)

        # print("Got event " + str(value) + "," + str(event_type) + "," + str(number))
        # if type & 0x80:
        #      print "(initial)",

        if event_type & 0x01:
            button = button_map[number]
            if button:
                button_states[button] = value
                # if value:
                #     print "%s pressed" % (button)
                # else:
                #     print "%s released" % (button)

        if event_type & 0x02:
            selected_axis = axis_map[number]
            if selected_axis:
                fvalue = value / 32767.0
                axis_states[selected_axis] = fvalue


def readEventsLoop():
    while True:
        if not disabled:
            readEvents()
        else:
            time.sleep(0.2)


def startNewThread():
    thread = threading.Thread(target=readEventsLoop, args=())
    thread.daemon = True
    thread.start()

textStream = None

# GPIO.setmode(GPIO.BCM)
#
# GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)


# font = ImageFont.load_default()

# i2cbus = SMBus(1)
#
# oled = ssd1306(i2cbus)
# draw = oled.canvas
startNewThread()

screenTick = 0
batteryBlink = 0
connectionBlink = 0

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

topSpeed = 50
sensorDistance = 200

doOrbit = False
prepareToOrbit = False
continueToReadDistance = False
boost = False
global kick
kick = 0


axis_states["x"] = 0
axis_states["y"] = 0
axis_states["rx"] = 0
axis_states["ry"] = 0

def doShutdown():
    print("Shutting down now!")
    try:
        subprocess.call(["/usr/bin/sudo", "/sbin/shutdown", "-h", "now"])
    except Exception as exception:
        print("ERROR: Failed to shutdown; " + str(exception))


def countDownToShutdown():
    i = 10
    while button_states["select"] and button_states["start"]:

        i -= 1
        if i == 0:

            doShutdown()

        sleep(0.5)


def stopJavaCode():
    global javaProcess

    try:
        print("Sending kill to java...")
        if javaProcess.returncode is None:
            javaProcess.kill()
            print("Sent kill to java...")

        sleep(0.01)
        # Just in case - we really need that process killed!!!
        subprocess.call(["/usr/bin/pkill", "-9", "/usr/bin/java -jar /home/pi/RPIcontroller.jar"])
    except:
        pass

    print("Finished killing java...")
    disabled = False
    javaProcess = None


def startJavaCode():
    global javaProcess, textStream
    print("Starting java...")
    disabled = True

    javaProcess = subprocess.Popen(["/usr/bin/java", "-jar", "/home/pi/RPIcontroller.jar"],
                               bufsize=0,
                               stdout=subprocess.PIPE,

                               shell=False,
                               universal_newlines=True)


    textStream = javaProcess.stdout
    print("Started java.")


def processKeys():
    global lastX3, lastY3, lastSelect, lastStart
    global lastTL, lastTL2, lastTR, lastTR2, lastA, lastB, lastBX, lastBY

    global screenMode, topSpeed

    global prepareToOrbit, continueToReadDistance, doOrbit, boost, kick

#Button states: " + str(button_states) + "\n" +
    # print("Axis states: " + str(axis_states))



    x3 = int(axis_states["hat0x"])
    y3 = int(axis_states["hat0y"])

    tl = button_states["base"]
    tl2 = button_states["top2"]
    tr = button_states["base2"]
    tr2 = button_states["pinkie"]
    a = button_states["thumb"]
    bb = button_states["thumb2"]
    bx = button_states["trigger"]
    by = button_states["top"]
    start = button_states["base4"]

    select = button_states["base3"]

    # x3 = int(joystick.axis_states["hat0x"])
    # y3 = int(joystick.axis_states["hat0y"])
    #
    # tl = joystick.button_states["tl"]
    # tl2 = joystick.button_states["tl2"]
    # tr = joystick.button_states["tr"]
    # tr2 = joystick.button_states["tr2"]
    # a = joystick.button_states["a"]
    # bb = joystick.button_states["b"]
    # bx = joystick.button_states["x"]
    # by = joystick.button_states["y"]
    # start = joystick.button_states["start"]
    #
    # select = joystick.button_states["select"]

    # if start and start != lastStart:
    #     sr = int(pyros.gcc.selectedRover)
    #     sr += 1
    #     if sr > 4:
    #         sr = 2
    #
    #     pyros.gcc.selectedRover = str(sr)
    #
    #     pyros.gcc.connect()

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
            topSpeed += 50
            if topSpeed > 300:
                topSpeed = 300
        elif x3 < 0:
            if topSpeed >= 100:
                topSpeed -= 50
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


    ## kick
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
    global kick

    lx = int(axis_states["x"])
    ly = int(axis_states["rx"])
    ld = math.sqrt(lx * lx + ly * ly)

    rx = int(axis_states["y"])
    ry = int(axis_states["ry"])

    # lx = int(axis_states["x"])
    # ly = int(axis_states["y"])
    # ld = math.sqrt(lx * lx + ly * ly)
    #
    # rx = int(axis_states["rx"])
    # ry = int(axis_states["ry"])
    rd = math.sqrt(rx * rx + ry * ry)
    ra = math.atan2(rx, -ry) * 180 / math.pi

    if ld < 0.1 and rd > 0.1:
        distance = rd
        distance = calculateExpo(distance, 0.75)

        roverSpeed = calcRoverSpeed(distance)
        pyros.publish("move/drive", str(round(ra, 1)) + " " + str(int(roverSpeed)))
    elif ld > 0.1 and rd > 0.1:

        ry = calculateExpo(ry, 0.75)

        lx = calculateExpo(lx, 0.75)

        roverSpeed = -calcRoverSpeed(ry)
        roverTurningDistance = calcRoverDistance(lx)
        pyros.publish("move/steer", str(roverTurningDistance) + " " + str(roverSpeed))
    elif ld > 0.1:
        if doOrbit and not prepareToOrbit:
            distance = sensorDistance
            if distance > 1000:
                distance = 1000
            roverSpeed = calcRoverSpeed(lx)
            pyros.publish("move/orbit", str(int(sensorDistance + 70)) + " " + str(roverSpeed))
        else:
            lx = calculateExpo(lx, 0.75)
            roverSpeed = calcRoverSpeed(lx) / 4
            pyros.publish("move/rotate", int(roverSpeed))
            print("-> move/rotate " + str(roverSpeed))
    elif kick > 0:
        pass
    else:
        pyros.publish("move/drive", str(ra) + " 0")
        if ra != 0:
            print("-> move/drive " + str(ra))
        roverSpeed = 0
        pyros.publish("move/stop", "0")


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
    global screenTick, screenMode, lastSelect, javaCntr

    processKeys()
    processJoysticks()

    # if button_states["select"] and button_states["start"]:
    #     countDownToShutdown()


pyros.subscribe("sensor/distance", handleDistance)
pyros.init("jcontroller-service")
pyros.forever(0.02, loop)
