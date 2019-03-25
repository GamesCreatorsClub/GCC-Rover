#!/usr/bin/env python3

#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import traceback
import pyroslib

#
# uplink service
#
# This service is just turning servo one way or another
#

DEBUG = False


UPLINK_SERVO = 3
MIN = 80
MAX = 220

position = MIN

direction = 1


def moveServo(servoid, position):
    try:
        with open("/dev/servoblaster", 'w') as f:
            f.write(str(servoid) + "=" + str(position) + "\n")
    except Exception as ex:
        print("Sending servo exception: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))


def stopCallback():
    print("Asked to stop!")


def loop():
    global position, direction

    position += direction

    if position >= MAX:
        direction = -direction

    if position <= MIN:
        direction = -direction

    servo_position = int(position)
    print("Moving servo to " + str(servo_position))
    moveServo(UPLINK_SERVO, servo_position)


if __name__ == "__main__":
    try:
        print("Starting uplink service...")

        pyroslib.init("uplink-service", onStop=stopCallback)

        print("Started uplink service.")

        pyroslib.forever(0.02, loop, priority=pyroslib.PRIORITY_LOW)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
