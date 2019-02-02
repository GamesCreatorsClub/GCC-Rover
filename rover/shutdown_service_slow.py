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
doPrepareToShutdown = False
timeToShutDown = False
wheelPyrosStopped = False
masterPyrosStopped = False


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


def wheelsSystemOut(topic, payload, groups):
    global wheelPyrosStopped
    if payload.strip() == "stopped":
        wheelPyrosStopped = True


def masterSystemOut(topic, payload, groups):
    global masterPyrosStopped
    if payload.strip() == "stopped":
        masterPyrosStopped = True


def doShutdown():
    global wheelPyrosStopped, masterPyrosStopped

    print("Shutting down...")

    pyroslib.publish("shutdown/announce", "now")

    _now = time.time()
    while time.time() - _now < 15 and not wheelPyrosStopped:
        pyroslib.loop(0.1)

    if wheelPyrosStopped:
        print("Wheels PyROS stopped")
        _now = time.time()
        while time.time() - _now < 5:
            pyroslib.loop(0.1)
    else:
        print("Wheels PyROS didn't respond in 15 minutes. Stopping now.")

    print("Allowing wheels to stop...")

    now = time.time()
    while not masterPyrosStopped and time.time() - now < 30.0:
        pyroslib.loop(0.1)

    print("Stopping PyROS...")

    pyroslib.publish("system/pyros:master", "stop shutdown")

    now = time.time()
    while not masterPyrosStopped and time.time() - now < 1.0:
        pyroslib.loop(0.1)

    print("Shutting down now!")

    # with open("/home/pi/shutdown", "w") as f:
    #     f.write("shutdown")

    try:
        subprocess.call(["/usr/bin/sudo", "/sbin/shutdown", "-h", "now"])
    except Exception as exception:
        print("ERROR: Failed to shutdown; " + str(exception))


def checkIfSecretMessage(topic, payload, groups):
    global doPrepareToShutdown, timeToShutDown
    if payload == "secret_message":
        doPrepareToShutdown = True
    elif payload == "secret_message_now":
        timeToShutDown = True


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
        pyroslib.subscribe("system/pyros:wheels/out", wheelsSystemOut)
        pyroslib.subscribe("system/pyros:master/out", masterSystemOut)

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
            if doPrepareToShutdown or (switchPin is not None and GPIO.input(switchPin) == 0):
                prepareToShutdown()
            elif timeToShutDown:
                doShutdown()

        pyroslib.forever(0.5, checkSwitch)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))