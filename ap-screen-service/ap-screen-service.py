#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import time
import subprocess
import RPi.GPIO as GPIO

SCREEN_OFF_TIME = 300  # 5 seconds

GPIO_RIGHT = 27  # Joypad left
GPIO_LEFT = 17  # Joypad right
GPIO_UP = 18  # Joypad up
GPIO_DOWN = 22  # Joypad down
GPIO_SPACE = 13  # 'Select' button
GPIO_ENTER = 12  # 'Start' button
GPIO_ESC = 19  # Exit ROM; PiTFT Button 1
GPIO_BACKSPACE = 5  # Backspace

GPIO_BACKLIGHT = 9  # Backlight

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_RIGHT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(GPIO_LEFT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(GPIO_UP, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(GPIO_DOWN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(GPIO_SPACE, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(GPIO_ENTER, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(GPIO_ESC, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(GPIO_BACKSPACE, GPIO.IN, pull_up_down=GPIO.PUD_UP)

GPIO.setup(GPIO_BACKLIGHT, GPIO.OUT)

right = False
left = False
up = False
down = False
space = False
enter = False
esc = False
backspace = False

isScreenOn = True


def setScreenState(state):
    global isScreenOn
    GPIO.output(GPIO_BACKLIGHT, state)
    isScreenOn = state


def screenOn():
    setScreenState(True)


def screenOff():
    setScreenState(False)


def readKeys():
    global right, left, up, down, space, enter, esc, backspace

    right = not GPIO.input(GPIO_RIGHT)
    left = not GPIO.input(GPIO_LEFT)
    up = not GPIO.input(GPIO_UP)
    down = not GPIO.input(GPIO_DOWN)
    space = not GPIO.input(GPIO_SPACE)
    enter = not GPIO.input(GPIO_ENTER)
    esc = not GPIO.input(GPIO_ESC)
    backspace = not GPIO.input(GPIO_BACKSPACE)


def hasAnyKey():
    return right or left or up or down or space or enter or esc or backspace


def hasShutdownCombo():
    return left and esc


def doShutdown():
    print("Shutting down now!")
    try:
        subprocess.call(["/usr/bin/sudo", "/sbin/shutdown", "-h", "now"])
    except Exception as exception:
        print("ERROR: Failed to shutdown; " + str(exception))


def shutdown():
    screenOn()
    print("Preparing to shut down...")
    seconds = 0.0
    interval = 0.3
    state = True
    lastSeconds = int(seconds)

    currentSwtich = hasShutdownCombo()
    previousSwitch = currentSwtich

    while seconds <= 6.0 and not (previousSwitch == 0 and currentSwtich == 1):
        time.sleep(interval)
        seconds += interval
        setScreenState(state)
        state = not state
        if lastSeconds != int(seconds):
            lastSeconds = int(seconds)
            print("Preparing to shut down... " + str(lastSeconds))

        previousSwitch = currentSwtich
        readKeys()
        currentSwtich = hasShutdownCombo()

    if not (previousSwitch == 0 and currentSwtich == 1):
        print("Shutting down...")
        doShutdown()
    else:
        print("Shutdown stopped.")

screenOn()
lastKeySeen = time.time()

print("Started Access Point Screen service")

while True:
    readKeys()

    if hasAnyKey():
        lastKeySeen = time.time()
        if not isScreenOn:
            screenOn()

        if hasShutdownCombo():
            print("Detected shutdown key combo...")
            shutdown()

    elif isScreenOn:
        now = time.time()

        if now - lastKeySeen > SCREEN_OFF_TIME:
            screenOff()

    time.sleep(0.02)
