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
import threading


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



javaProcess = None
textStream = None

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)

SCREEN_MONITOR = 1
SCREEN_ROVER = 2
JAVA_PROGRAM = 3

LAST_SCREEN_MODE = JAVA_PROGRAM

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

javaCntr = 0

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


def drawTopSpeed(x, y):
    spd = calcRoverSpeed(1)

    if pyros.isConnected():
        x = x - draw.textsize(str(spd), font)[0]
        draw.text((x, y), str(spd), font=font, fill=1)


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
    joystick.disabled = False
    javaProcess = None


def startJavaCode():
    global javaProcess, textStream
    print("Starting java...")
    joystick.disabled = True

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

    x3 = int(joystick.axis_states["hat0x"])
    y3 = int(joystick.axis_states["hat0y"])

    tl = joystick.button_states["tl"]
    tl2 = joystick.button_states["tl2"]
    tr = joystick.button_states["tr"]
    tr2 = joystick.button_states["tr2"]
    a = joystick.button_states["a"]
    bb = joystick.button_states["b"]
    bx = joystick.button_states["x"]
    by = joystick.button_states["y"]
    start = joystick.button_states["start"]

    select = joystick.button_states["select"]
    if select and select != lastSelect:
        if screenMode == JAVA_PROGRAM:
            print("Stopping java...")
            stopJavaCode()
            joystick.disabled = False
            print("Stopped java.")

        screenMode += 1
        if screenMode == JAVA_PROGRAM:
            startJavaCode()

        if screenMode > LAST_SCREEN_MODE:
            screenMode = SCREEN_MONITOR

    if screenMode != JAVA_PROGRAM:
        if start and start != lastStart:
            sr = int(pyros.gcc.selectedRover)
            sr += 1
            if sr > 4:
                sr = 2

            pyros.gcc.selectedRover = str(sr)

            pyros.gcc.connect()

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

    lx = int(joystick.axis_states["x"])
    ly = int(joystick.axis_states["y"])
    ld = math.sqrt(lx * lx + ly * ly)

    rx = int(joystick.axis_states["rx"])
    ry = int(joystick.axis_states["ry"])
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
    elif kick > 0:
        pass
    else:
        pyros.publish("move/drive", str(ra) + " 0")
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

    screenTick += 1
    if screenTick >= 5:
        clear()

        drawBattery(106, 58, 21)
        drawConnection(40, 50)
        drawTopSpeed(105, 50)
        if screenMode == SCREEN_MONITOR:
            drawJoysticks()
        elif screenMode == SCREEN_ROVER:
            drawRover()
        elif screenMode == JAVA_PROGRAM:
            if javaCntr == 0:
                drawText((0, 0), "java.")
                javaCntr = 1
            elif javaCntr == 1:
                drawText((0, 0), "java..")
                javaCntr = 2
            elif javaCntr == 2:
                drawText((0, 0), "java...")
                javaCntr = 0

        oled.display()

        screenTick = 0

    processKeys()
    if screenMode != JAVA_PROGRAM:
        processJoysticks()
    else:
        if javaProcess is not None and javaProcess.returncode is None:
            line = textStream.readline()
            print("<< " + str(line))
            if "kill me" in line:
                lastSelect = True
                screenMode += 1
                if screenMode > LAST_SCREEN_MODE:
                    screenMode = SCREEN_MONITOR
                stopJavaCode()

    if joystick.button_states["select"] and joystick.button_states["start"]:
        countDownToShutdown()


pyros.subscribe("sensor/distance", handleDistance)
pyros.init("gcc-controller-#", unique=False, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)
pyros.forever(0.02, loop)