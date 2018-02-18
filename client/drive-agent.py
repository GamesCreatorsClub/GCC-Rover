#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import time
import traceback
import pyroslib

DELAY = 0.15

current_speed = 100

STRAIGHT = 1
SLANT = 2
SIDEWAYS = 3

wheelPosition = STRAIGHT


def straightenWheels():
    global wheelPosition, DELAY, STRAIGHT

    wheelDeg("fl", 0)
    wheelDeg("fr", 0)
    wheelDeg("bl", 0)
    wheelDeg("br", 0)

    if wheelPosition != STRAIGHT:
        time.sleep(DELAY)
        wheelPosition = STRAIGHT


def slantWheels():
    global wheelPosition, DELAY, SLANT

    wheelDeg("fl", 60.0)
    wheelDeg("fr", -60.0)
    wheelDeg("bl", -60.0)
    wheelDeg("br", 60.0)
    if wheelPosition != SLANT:
        time.sleep(DELAY)
        wheelPosition = SLANT


def sidewaysWheels():
    global wheelPosition, DELAY, SIDEWAYS

    wheelDeg("fl", 90.0)
    wheelDeg("fr", -90.0)
    wheelDeg("bl", -90.0)
    wheelDeg("br", 90.0)
    if wheelPosition != SIDEWAYS:
        time.sleep(DELAY)
        wheelPosition = SIDEWAYS


def stopAllWheels():
    wheelSpeed("fl", 0)
    wheelSpeed("fr", 0)
    wheelSpeed("bl", 0)
    wheelSpeed("br", 0)


def turnOnSpot(amount):
    slantWheels()
    wheelSpeed("fl", amount)
    wheelSpeed("fr", -amount)
    wheelSpeed("bl", amount)
    wheelSpeed("br", -amount)


def moveMotors(amount):
    straightenWheels()
    wheelSpeed("fl", amount)
    wheelSpeed("fr", amount)
    wheelSpeed("bl", amount)
    wheelSpeed("br", amount)


def crabAlong(amount):
    sidewaysWheels()
    wheelSpeed("fl", amount)
    wheelSpeed("fr", -amount)
    wheelSpeed("bl", -amount)
    wheelSpeed("br", amount)


def wheelDeg(wheelName, angle):
    topic = "wheel/" + wheelName + "/deg"
    pyroslib.publish(topic, str(angle))
    # print("Published topic=" +  topic + "; msg=" + str(angle))


def wheelSpeed(wheelName, speed):
    topic = "wheel/" + wheelName + "/speed"
    pyroslib.publish(topic, str(speed))
    # print("Published topic=" +  topic + "; msg=" + str(speed))


def coonnected():
    print("DriverAgent: Connected to rover")
    straightenWheels()


def handleMessage(topic, message, groups):

    if topic == "drive":
        command = message.split(">")[0]
        if len(message.split(">")) > 1:
            command_args_list = message.split(">")[1].split(",")
            args1 = command_args_list[0]
        else:
            args1 = 0
        if command == "forward":
            moveMotors(int(args1))
        elif command == "back":
            moveMotors(-int(args1))
        elif command == "motors":
            moveMotors(int(args1))
        elif command == "align":
            straightenWheels()
        elif command == "slant":
            slantWheels()
        elif command == "rotate":
            turnOnSpot(int(args1))
        elif command == "pivotLeft":
            turnOnSpot(-int(args1))
        elif command == "pivotRight":
            turnOnSpot(int(args1))
        elif command == "stop":
            stopAllWheels()
        elif command == "sideways":
            sidewaysWheels()
        elif command == "crabLeft":
            crabAlong(-int(args1))
        elif command == "crabRight":
            crabAlong(int(args1))


if __name__ == "__main__":
    try:
        print("Starting drive agent...")

        pyroslib.subscribe("drive", handleMessage)
        pyroslib.init("drive-agent", unique=True)

        print("Started drive agent.")

        pyroslib.forever(0.02)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))


