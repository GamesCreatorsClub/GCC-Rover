#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import pyroslib
import subprocess
import traceback

#
# shutdown service
#
# This service is responsible shutting down Linux.
#

DEBUG = False


def doShutdown():
    print("Shutting down now!")
    pyroslib.loop(0.5)
    try:
        subprocess.call(["/usr/bin/sudo", "/sbin/shutdown", "-h", "now"])
    except Exception as exception:
        print("ERROR: Failed to shutdown; " + str(exception))


def checkIfSecretMessage(topic, payload, groups):
    print("Received " + str(topic) + " with " + str(payload))
    if topic == "shutdown/announce" and payload == "now":
        doShutdown()
    elif topic == "system/shutdown" and payload == "secret_message_now":
        doShutdown()


if __name__ == "__main__":
    try:
        print("Starting shutdown service...")

        pyroslib.init("shutdown-service", unique=True)

        pyroslib.subscribe("system/shutdown", checkIfSecretMessage)
        pyroslib.subscribe("shutdown/announce", checkIfSecretMessage)

        print("Started shutdown service.")

        pyroslib.forever(0.5)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
