#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import traceback
import pyroslib
import RPi.GPIO as GPIO

#
# lights service
#
# This service is responsible switching LEDs on and off.
#

DEBUG = False
CAMERA_LIGHT_GPIO = 16

lightsState = False


def setLights(state):
    global lightsState

    lightsState = state
    GPIO.output(CAMERA_LIGHT_GPIO, state)


def handleLights(topic, payload, groups):
    if "on" == payload or "ON" == payload or "1" == payload:
        print("Lights on.")
        setLights(True)
    else:
        print("Lights off.")
        setLights(False)


if __name__ == "__main__":
    try:
        print("Starting lights service...")

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(CAMERA_LIGHT_GPIO, GPIO.OUT)

        pyroslib.subscribe("lights/camera", handleLights)
        pyroslib.init("light-service")

        print("Started lights service.")

        pyroslib.forever(0.5)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
