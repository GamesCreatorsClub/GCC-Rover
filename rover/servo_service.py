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


def moveServo(servoid, position):
    if DEBUG:
        print("Moving servo " + str(servoid) + " to position " + str(position))

    # TODO move this out to separate service
    f = open("/dev/servoblaster", 'w')
    f.write(str(servoid) + "=" + str(position) + "\n")
    f.close()


def handleServo(topic, payload, groups):
    servoId = int(groups[0])
    position = int(float(payload))

    moveServo(servoId, position)


if __name__ == "__main__":
    try:
        print("Starting servo service...")

        pyroslib.subscribe("servo/+", handleServo)

        pyroslib.init("servo-service")

        print("Started servo service.")

        pyroslib.forever(0.02

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
