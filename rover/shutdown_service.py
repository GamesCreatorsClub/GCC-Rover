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
import storagelib
import RPi.GPIO as GPIO

#
# shutdown service
#
# This service is responsible shutting down Linux.
#

DEBUG = False

DEFAULT_SWITCH_PIN = 21

switchPin = None

lightsState = False
useLights = True


def setLights(state):
    global lightsState

    if state:
        pyroslib.publish("lights/camera", "on")
    else:
        pyroslib.publish("lights/camera", "off")
        pyroslib.loop(0.005)


def prepareToShutdown():
    print("Preparing to shut down...")
    previousLightsState = lightsState
    seconds = 0.0
    interval = 0.3
    state = True
    lastSeconds = int(seconds)

    if switchPin is not None:
        currentSwtich = GPIO.input(switchPin)
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
            currentSwtich = GPIO.input(switchPin)

        if not (previousSwitch == 0 and currentSwtich == 1):
            doShutdown()
        else:
            setLights(previousLightsState)
    else:
        doShutdown()


def doShutdown():
    print("Shutting down now!")
    pyroslib.publish("shutdown/announce", "now")
    pyroslib.loop(2.0)
    try:
        subprocess.call(["/usr/bin/sudo", "/sbin/shutdown", "-h", "now"])
    except Exception as exception:
        print("ERROR: Failed to shutdown; " + str(exception))


def checkIfSecretMessage(topic, payload, groups):
    if payload == "secret_message":
        prepareToShutdown()
    elif payload == "secret_message_now":
        doShutdown()


def loadStorage():
    global switchPin
    storagelib.subscribeToPath("shutdown/pin")
    storagelib.waitForData()
    storageMap = storagelib.storageMap["shutdown"]

    try:
        switchPin = int(storageMap['pin'])
        print("  Switch pin is set to " + str(switchPin))
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(DEFAULT_SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    except:
        switchPin = None
        print("  No switch pin defined")

    print("  Storage details loaded.")


if __name__ == "__main__":
    try:
        print("Starting shutdown service...")

        pyroslib.init("shutdown-service", unique=False)

        pyroslib.subscribe("system/shutdown", checkIfSecretMessage)
        print("  Loading storage details...")
        loadStorage()

        if switchPin is not None:
            if GPIO.input(switchPin) == 0:
                while GPIO.input(switchPin) == 0:
                    print("  Waiting to start shutdown-service - switch in wrong position...")
                    setLights(True)
                    time.sleep(0.3)
                    setLights(False)
                    i = 0
                    while GPIO.input(switchPin) == 0 and i < 25:
                        time.sleep(0.2)
                        i += 1

        print("Started shutdown service.")

        def checkSwitch():
            if switchPin is not None and GPIO.input(switchPin) == 0:
                prepareToShutdown()

        pyroslib.forever(0.5, checkSwitch, priority=pyroslib.PRIORITY_LOW)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
