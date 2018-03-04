#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import traceback
import subprocess
import time
import pyroslib
import RPi.GPIO as GPIO

#
# shutdown service
#
# This service is responsible shutting down Linux.
#

DEBUG = False

#SWITCH_GPIO = 21
SWITCH_GPIO = 23 # GPIO 23 is the button on Voice HAT


lightsState = False


def setLights(state):
    global lightsState

    if state:
        pyroslib.publish("lights/button", "on")
    else:
        pyroslib.publish("lights/button", "off")
        pyroslib.loop(0.005)


def prepareToShutdown():
    print("Preparing to shut down...")
    previousLightsState = lightsState
    seconds = 0.0
    interval = 0.3
    state = True
    lastSeconds = int(seconds)

    currentSwtich = GPIO.input(SWITCH_GPIO)
    previousSwitch = currentSwtich

    while seconds <= 6.0 and not (previousSwitch == 0 and currentSwtich == 1):
        time.sleep(interval)
        seconds += interval
        setLights(state)
        state = not state
        if lastSeconds != int(seconds):
            lastSeconds = int(seconds)
            print("Preparing to shut down... " + str(lastSeconds))

        previousSwitch = currentSwtich
        currentSwtich = GPIO.input(SWITCH_GPIO)

    if not (previousSwitch == 0 and currentSwtich == 1):
        doShutdown()
    else:
        setLights(previousLightsState)


def doShutdown():
    print("Shutting down now!")
    try:
        subprocess.call(["/usr/bin/sudo", "/sbin/shutdown", "-h", "now"])
    except Exception as exception:
        print("ERROR: Failed to shutdown; " + str(exception))


def checkIfSecretMessage(topic, payload, groups):
    if payload == "secret_message":
        prepareToShutdown()


if __name__ == "__main__":
    try:
        print("Starting shutdown service...")

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SWITCH_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        pyroslib.subscribe("system/shutdown", checkIfSecretMessage)

        pyroslib.init("shutdown-service")

        if GPIO.input(SWITCH_GPIO) == 0:
            while GPIO.input(SWITCH_GPIO) == 0:
                print("  Waiting to start shutdown-service - switch in wrong position...")
                setLights(True)
                time.sleep(0.3)
                setLights(False)
                i = 0
                while GPIO.input(SWITCH_GPIO) == 0 and i < 25:
                    time.sleep(0.2)
                    i += 1

        print("Started shutdown service.")

        def checkSwitch():
            if GPIO.input(SWITCH_GPIO) == 0:
                prepareToShutdown()

        pyroslib.forever(0.5, checkSwitch)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
