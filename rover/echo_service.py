#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import traceback
import pyroslib

#
# echo service
#
# This service is just sending echo back to different topic.
#

DEBUG = False


def handleEcho(topic, payload, groups):
    print("Got echo in " + payload)
    if len(groups) > 0:
        pyroslib.publish("echo/out", groups[0] + ":" + payload)
    else:
        pyroslib.publish("echo/out", "default:" + payload)

if __name__ == "__main__":
    try:
        print("Starting echo service...")

        pyroslib.subscribe("echo/in", handleEcho)
        pyroslib.subscribe("echo/in/a/b/#", handleEcho)
        pyroslib.subscribe("echo/in/b/+/c", handleEcho)
        pyroslib.init("echo-service")

        print("Started echo service.")

        pyroslib.forever(0.5)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
