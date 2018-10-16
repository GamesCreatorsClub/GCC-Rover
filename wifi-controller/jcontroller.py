#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import joystick
import subprocess
from lib_oled96 import ssd1306

from time import sleep
from PIL import ImageFont, ImageDraw, Image
from smbus import SMBus
import RPi.GPIO as GPIO

import math

import pyros
import pyros.gcc
import socket

JCONTROLLER_UDP_PORT = 1880

rovers = {
    "2": {
        "address": "172.24.1.184",
        "port": 1883
    },
    "3": {
        "address": "172.24.1.185",
        "port": 1883
    },
    "4": {
        "address": "172.24.1.186",
        "port": 1883
    }
}

selectedRover = "2"


def getHost():
    return rovers[selectedRover]["address"]


def getPort():
    return rovers[selectedRover]["port"]


def connect():
    pyros.connect(rovers[selectedRover]["address"], rovers[selectedRover]["port"], waitToConnect=False)


textStream = None

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)

SCREEN_MONITOR = 1
SCREEN_ROVER = 2

LAST_SCREEN_MODE = SCREEN_ROVER

screenMode = SCREEN_MONITOR

# font = ImageFont.load_default()

font = ImageFont.truetype('FreeMono.ttf', 16)
fontBig = ImageFont.truetype('FreeMono.ttf', 32)

i2cbus = SMBus(1)

oled = ssd1306(i2cbus)
draw = oled.canvas
joystick.startNewThread()

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

joystick.axis_states["x"] = 0
joystick.axis_states["y"] = 0
joystick.axis_states["rx"] = 0
joystick.axis_states["ry"] = 0

for b in joystick.button_map:
    print("b=" + b)


def clear():
    draw.rectangle((0, 0, oled.width - 1, oled.height - 1), fill=0)


def drawText(xy, text):
    draw.text(xy, text, font=font, fill=1)


def drawJoysticks():
    x1 = int(joystick.axis_states["x"] * 20)
    y1 = int(joystick.axis_states["y"] * 20)
    x2 = int(joystick.axis_states["rx"] * 20)
    y2 = int(joystick.axis_states["ry"] * 20)

    draw.line((x1 + 20, 0, x1 + 20, 40), fill=255)
    draw.line((0, y1 + 20, 40, y1 + 20), fill=255)
    draw.line((87 + x2 + 20, 0, 87 + x2 + 20, 40), fill=255)
    draw.line((87, y2 + 20, 87 + 40, y2 + 20), fill=255)

    x3 = int(joystick.axis_states["hat0x"])
    y3 = int(joystick.axis_states["hat0y"])

    if x3 < 0:
        draw.rectangle((0, 50, 7, 57), fill=255)
        draw.rectangle((16, 50, 23, 57), outline=255)
    elif x3 > 0:
        draw.rectangle((0, 50, 7, 57), outline=255)
        draw.rectangle((16, 50, 23, 57), fill=255)
    else:
        draw.rectangle((0, 50, 7, 57), outline=255)
        draw.rectangle((16, 50, 23, 57), outline=255)

    if y3 < 0:
        draw.rectangle((8, 42, 15, 49), fill=255)
        draw.rectangle((8, 58, 15, 63), outline=255)
    elif y3 > 0:
        draw.rectangle((8, 42, 15, 49), outline=255)
        draw.rectangle((8, 58, 15, 63), fill=255)
    else:
        draw.rectangle((8, 42, 15, 49), outline=255)
        draw.rectangle((8, 58, 15, 63), outline=255)

    x = 54
    y = 0
    for i in range(0, 12):
        buttonState = joystick.button_states[joystick.button_map[i]]
        if buttonState:
            draw.rectangle((x, y, x + 7, y + 7), fill=255)
        else:
            draw.rectangle((x, y, x + 7, y + 7), outline=255)

        x = x + 8 + 2
        if x > 72:
            x = 54
            y = y + 8 + 2


def drawBattery(x, y, width):
    global batteryBlink

    batteryBlink += 1
    if batteryBlink > 8:
        batteryBlink = 0

    batteryState = GPIO.input(17)

    if batteryState:
        draw.rectangle((x + 2, y, x + width - 2, y + 5), fill=255)
        draw.rectangle((x, y + 2, x + 1, y + 3), fill=255)
        draw.line((x + 3, y + 1, x + 3, y + 1), fill=0)
        draw.line((x + 3, y + 2, x + 4, y + 1), fill=0)
        draw.line((x + 3, y + 3, x + 5, y + 1), fill=0)
        draw.line((x + 3, y + 4, x + 6, y + 1), fill=0)
        draw.line((x + 4, y + 4, x + 7, y + 1), fill=0)
        draw.line((x + 5, y + 4, x + 8, y + 1), fill=0)
        # drawText((0, 50), "B: OKW")
    else:
        if batteryBlink > 4:
            draw.rectangle((x + 2, y, x + width - 2, y + 5), outline=255)
            draw.rectangle((x, y + 2, x + 1, y + 3), fill=255)
            draw.line((x + width - 3, y + 5, x + width - 3, y + 5), fill=255)
            draw.line((x + width - 4, y + 5, x + width - 3, y + 4), fill=255)
            draw.line((x + width - 5, y + 5, x + width - 3, y + 3), fill=255)
            draw.line((x + width - 6, y + 5, x + width - 3, y + 2), fill=255)
            draw.line((x + width - 7, y + 5, x + width - 3, y + 1), fill=255)
        # drawText((0, 50), "B: LOW")


def drawRover():
    draw.text((0, 50), "R:", font=font, fill=1)
    draw.text((55, 50), "S:", font=font, fill=1)

    draw.text((0, 0), "D:", font=font, fill=1)

    x = 80 - draw.textsize(str(sensorDistance), font)[0]
    draw.text((x, 0), str(sensorDistance), font=font, fill=1)
    if doOrbit:
        draw.text((96, 0), str("o"), font=font, fill=1)
    if prepareToOrbit:
        draw.text((105, 0), str("p"), font=font, fill=1)
    if continueToReadDistance:
        draw.text((114, 0), str("c"), font=font, fill=1)


def drawConnection(x, y):
    global connectionBlink

    connectionBlink += 1
    if connectionBlink > 2:
        connectionBlink = 0

    s = pyros.gcc.selectedRover
    if pyros.isConnected() or connectionBlink > 0:
        draw.text((x, y), s, font=font, fill=1)


def doShutdown():
    print("Shutting down now!")
    try:
        subprocess.call(["/usr/bin/sudo", "/sbin/shutdown", "-h", "now"])
    except Exception as exception:
        print("ERROR: Failed to shutdown; " + str(exception))


def countDownToShutdown():
    i = 10
    while joystick.button_states["select"] and joystick.button_states["start"]:
        clear()

        i -= 1
        if i == 0:
            x = (128 - draw.textsize("Switch off", font)[0]) // 2
            draw.text((x, 10), "Switch off", font=font, fill=1)

            x = (128 - draw.textsize("in 10s", fontBig)[0]) // 2
            draw.text((x, 32), "in 10s", font=fontBig, fill=1)
            oled.display()

            doShutdown()

        x = (128 - draw.textsize("Shutdown in", font)[0]) // 2
        draw.text((x, 10), "Shutdown in", font=font, fill=1)

        x = (128 - draw.textsize(str(i), fontBig)[0]) // 2
        draw.text((x, 32), str(i), font=fontBig, fill=1)
        oled.display()
        sleep(0.5)


def processJoysticks():
    global kick
    global lastSelect, lastStart, screenMode, s

    start = joystick.button_states["start"]

    select = joystick.button_states["select"]

    if select and select != lastSelect:
        screenMode += 1

        if screenMode > LAST_SCREEN_MODE:
            screenMode = SCREEN_MONITOR

    if start and start != lastStart:
        sr = int(pyros.gcc.selectedRover)
        sr += 1
        if sr > 4:
            sr = 2

        pyros.gcc.selectedRover = str(sr)

        pyros.gcc.connect()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    lastStart = start
    lastSelect = select

    if pyros.isConnected():
        x3 = int(joystick.axis_states["hat0x"])
        y3 = int(joystick.axis_states["hat0y"])
        if x3 < 0:
            lleft = 1
            lright = 0
        elif x3 > 0:
            lleft = 0
            lright = 1
        else:
            lleft = 0
            lright = 0

        if y3 < 0:
            lup = 1
            ldown = 0
        elif y3 > 0:
            lup = 0
            ldown = 1
        else:
            lup = 0
            ldown = 0

        tl = joystick.button_states["tl"]
        tl2 = joystick.button_states["tl2"]
        tr = joystick.button_states["tr"]
        tr2 = joystick.button_states["tr2"]
        a = joystick.button_states["a"]
        bb = joystick.button_states["b"]
        bx = joystick.button_states["x"]
        by = joystick.button_states["y"]
        # start = joystick.button_states["start"]
        #
        # select = joystick.button_states["select"]

        lx = round(float(joystick.axis_states["x"]), 2)
        ly = round(float(joystick.axis_states["y"]), 2)

        rx = round(float(joystick.axis_states["rx"]), 2)
        ry = round(float(joystick.axis_states["ry"]), 2)

        msg = "J#"
        msg += "x=" + str(lx) + ";y=" + str(ly)
        msg += ";rx=" + str(rx) + ";ry=" + str(ry)
        msg += ";tl1=" + str(tl2) + ";tl2=" + str(tl)
        msg += ";tr1=" + str(tr2) + ";tr2=" + str(tr)
        msg += ";ba=" + str(a) + ";bb=" + str(bb)
        msg += ";bx=" + str(bx) + ";by=" + str(by)
        msg += ";lleft=" + str(lleft) + ";lright=" + str(lright)
        msg += ";lup=" + str(lup) + ";ldown=" + str(ldown)

        # s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(bytes(msg, 'utf-8'), (pyros.host(), JCONTROLLER_UDP_PORT))
        #print("sending to " + str(pyros.host()) + ": " + msg + "     x=" + str(joystick.axis_states["x"]))


# Main event loop
def loop():
    global screenTick, screenMode, lastSelect, javaCntr

    screenTick += 1
    if screenTick >= 5:
        clear()

        drawBattery(106, 58, 21)
        drawConnection(40, 50)
        # drawTopSpeed(105, 50)
        if screenMode == SCREEN_MONITOR:
            drawJoysticks()
        elif screenMode == SCREEN_ROVER:
            drawRover()

        oled.display()

        screenTick = 0

    processJoysticks()

    if joystick.button_states["select"] and joystick.button_states["start"]:
        countDownToShutdown()


pyros.init("gcc-controller-#", unique=False, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)
pyros.forever(0.02, loop)