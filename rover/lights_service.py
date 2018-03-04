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
CAMERA_LIGHT_GPIO = 16 # this is AMP shutdown on Voice HAT
BUTTON_LIGHT_GPIO = 25 # LED on Voice HAT button

lightsState = {CAMERA_LIGHT_GPIO:False, BUTTON_LIGHT_GPIO:False}


def setLights(gpio, state):
    global lightsState

    lightsState[gpio] = state
    GPIO.output(gpio, state)


def handleLights(topic, payload, groups):
    gpio = CAMERA_LIGHT_GPIO
    if topic == "lights/button":
        gpio = BUTTON_LIGHT_GPIO

    if "on" == payload or "ON" == payload or "1" == payload:
        print("Lights on. {0}".format(gpio))
        setLights(gpio, True)
    else:
        print("Lights off. {0}".format(gpio))
        setLights(gpio, False)

if __name__ == "__main__":
    try:
        print("Starting lights service...")

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(CAMERA_LIGHT_GPIO, GPIO.OUT)
        GPIO.setup(BUTTON_LIGHT_GPIO, GPIO.OUT)

        pyroslib.subscribe("lights/camera", handleLights)
        pyroslib.subscribe("lights/button", handleLights)
        pyroslib.init("light-service")

        print("Started lights service.")

        pyroslib.forever(0.5)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
