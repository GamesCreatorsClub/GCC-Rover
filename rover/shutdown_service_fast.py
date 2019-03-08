#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import os
import pyroslib
import subprocess
import traceback
import time

#
# shutdown service
#
# This service is responsible shutting down Linux.
#

DEBUG = False
timeToShutDown = False
pyrosStopped = False


def doShutdown():
    global timeToShutDown
    timeToShutDown = True


def checkShutdown():
    if timeToShutDown:
        print("Shutting down... (cluster " + pyroslib.getClusterId() + ")")

        try:
            subprocess.call(["/usr/bin/sudo", "/bin/sync"])
        except Exception as exception:
            print("ERROR: Failed to shutdown; " + str(exception))

        pyroslib.publish("system/pyros:" + pyroslib.getClusterId(), "stop shutdown")
        now = time.time()
        while not pyrosStopped and time.time() - now < 1.0:
            pyroslib.loop(0.1)

        print("Shutting down now!")

        # with open("/home/pi/shutdown", "w") as f:
        #     f.write("shutdown")

        try:
            subprocess.call(["/usr/bin/sudo", "/sbin/shutdown", "-h", "now"])
        except Exception as exception:
            print("ERROR: Failed to shutdown; " + str(exception))


def systemOutput(topic, payload, groups):
    global pyrosStopped
    if payload == "stopped":
        pyrosStopped = True


def checkIfSecretMessage(topic, payload, groups):
    print("Received " + str(topic) + " with " + str(payload))
    if topic == "shutdown/announce" and payload == "now":
        doShutdown()
    elif topic == "system/shutdown" and payload == "secret_message_now":
        doShutdown()


if __name__ == "__main__":
    try:

        pyroslib.init("shutdown-service", unique=True)
        print("pyroslib.clusterId " + str(pyroslib.getClusterId()))

        pyroslib.subscribe("system/shutdown", checkIfSecretMessage)
        pyroslib.subscribe("shutdown/announce", checkIfSecretMessage)
        pyroslib.subscribe("system/pyros:" + pyroslib.getClusterId() + "/out", systemOutput)

        print("Started shutdown service.")

        pyroslib.forever(0.5, checkShutdown, priority=pyroslib.PRIORITY_LOW)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
