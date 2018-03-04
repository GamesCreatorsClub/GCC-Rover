#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import traceback
import time
import re
import copy
import pyroslib
import storagelib

#
# wheels service
#
#
# This service is responsible for moving wheels on the rover.
# Current implementation also handles:
#     - servos
#     - storage map
#

DEBUG = False
DEBUG_SPEED = True
DEBUG_SPEED_VERBOSE = False
DEBUG_TURN = False
DEBUG_SERVO = False

PWM = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],

    [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0],

    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
]


STORAGE_MAP_FILE = "/home/pi/rover-storage.config"
SERVO_REGEX = re.compile("servo/(\d+)")

PROTOTYPE_WHEEL_CALIBRATION = {
    "deg": {
        "servo": "",
        "90": "70",
        "0": "160",
        "-90": "230"
    },
    "speed": {
        "servo": "",
        "-300": "95",
        "-240": "115",
        "-0": "149",
        "0": "155",
        "240": "195",
        "300": "215"
    }
}

pwmIndex = 0

wheelMap = {}
wheelCalibrationMap = {}
wheelMap["servos"] = {}

servoBlasterFile = None


def moveServo(servoid, angle):
    global servoBlasterFile

    angle = int(angle)

    # TODO move this out to separate service
    servoLine = str(servoid) + "=" + str(angle)
    if DEBUG_SERVO:
        print("ServoBlaser <- " + servoLine)
    try:
        servoBlasterFile.write(servoLine + "\n")
        servoBlasterFile.flush()
    except:
        try:
            servoBlasterFile.close()
        except:
            pass
        if DEBUG:
            print("Lost connection to /dev/servoblaster - reopening")
        servoBlasterFile = open("/dev/servoblaster", 'w')


def initWheel(wheelName, motorServo, steerServo):
    wheelMap[wheelName] = {
        "deg": 0,
        "speed": 0,
        "servoSpeedPos": 0,
        "gen": None
    }


def initWheels():
    global wheelCalibrationMap

    if "wheels" not in storagelib.storageMap:
        storagelib.storageMap["wheels"] = {}

    if "cal" not in storagelib.storageMap["wheels"]:
        storagelib.storageMap["wheels"]["cal"] = {}

    wheelCalibrationMap = storagelib.storageMap["wheels"]["cal"]

    initWheel("fr", 0, 1)
    initWheel("fl", 2, 3)
    initWheel("br", 4, 5)
    initWheel("bl", 6, 7)


def subscribeWheels():
    storagelib.subscribeWithPrototype("wheels/cal/fl", PROTOTYPE_WHEEL_CALIBRATION)
    storagelib.subscribeWithPrototype("wheels/cal/fr", PROTOTYPE_WHEEL_CALIBRATION)
    storagelib.subscribeWithPrototype("wheels/cal/bl", PROTOTYPE_WHEEL_CALIBRATION)
    storagelib.subscribeWithPrototype("wheels/cal/br", PROTOTYPE_WHEEL_CALIBRATION)


def ensureWheelData(name, motorServo, steerServo):
    calMap = copy.deepcopy(PROTOTYPE_WHEEL_CALIBRATION)
    calMap["speed"]["servo"] = str(moveServo)
    calMap["deg"]["servo"] = str(steerServo)
    storagelib.bulkPopulateIfEmpty("wheels/cal/" + name, calMap)


def loadStorage():
    subscribeWheels()
    storagelib.waitForData()
    ensureWheelData("fr", 0, 1)
    ensureWheelData("fl", 2, 3)
    ensureWheelData("br", 4, 5)
    ensureWheelData("bl", 6, 7)
    print("  Storage details loaded.")


def handleServo(servoid, angle=0):
    wheelMap["servos"][str(servoid)] = angle
    moveServo(servoid, angle)


def handleDeg(wheel, wheelCal, degrees):
    if degrees >= 0:
        servoPosition = interpolate(degrees / 90.0, wheelCal["0"], wheelCal["90"])
    else:
        servoPosition = interpolate((degrees + 90) / 90.0, wheelCal["-90"], wheelCal["0"])

    wheel["deg"] = degrees
    wheel["degsServoPos"] = servoPosition
    servoNumber = wheelCal["servo"]

    moveServo(servoNumber, servoPosition)


def handleSpeed(wheel, wheelCal, speedStr):
    servoNumber = wheelCal["servo"]

    if speedStr == "0":
        servoPosition = int(interpolate(0.5, wheelCal["-0"], wheelCal["0"]))
        if DEBUG_SPEED_VERBOSE:
            print("    got speed 0 @ " + str(servoPosition) + " for " + str(servoNumber))
        speed = 0
    else:
        if "240" in wheelCal and "-240" in wheelCal:
            if speedStr == "-0":
                servoPosition = interpolate(0, wheelCal["-0"], wheelCal["-240"])
                if DEBUG_SPEED_VERBOSE:
                    print("    got speed -0 @ " + str(servoPosition) + " for " + str(servoNumber))
                speed = 0
            elif speedStr == "+0":
                servoPosition = interpolate(0, wheelCal["0"], wheelCal["240"])
                if DEBUG_SPEED_VERBOSE:
                    print("    got speed +0 @ " + str(servoPosition) + " for " + str(servoNumber))
                speed = 0
            else:
                speed = float(speedStr)
                if speed >= 0:
                    if speed <= 240:
                        servoPosition = interpolate(speed / 300, wheelCal["0"], wheelCal["240"])
                    else:
                        servoPosition = interpolate((speed - 240) / 60, wheelCal["240"], wheelCal["300"])
                else:
                    if speed >= -240:
                        servoPosition = interpolate(-speed / 300, wheelCal["-0"], wheelCal["-240"])
                    else:
                        servoPosition = interpolate((-speed - 240) / 60, wheelCal["-240"], wheelCal["-300"])

        else:
            if speedStr == "-0":
                servoPosition = interpolate(0, wheelCal["-0"], wheelCal["-300"])
                if DEBUG_SPEED_VERBOSE:
                    print("    got speed -0 @ " + str(servoPosition) + " for " + str(servoNumber))
                speed = 0
            elif speedStr == "+0":
                servoPosition = interpolate(0, wheelCal["0"], wheelCal["300"])
                if DEBUG_SPEED_VERBOSE:
                    print("    got speed +0 @ " + str(servoPosition) + " for " + str(servoNumber))
                speed = 0
            else:
                speed = float(speedStr)
                if speed >= 0:
                    servoPosition = interpolate(speed / 300, wheelCal["0"], wheelCal["300"])
                else:
                    servoPosition = interpolate(-speed / 300, wheelCal["-0"], wheelCal["-300"])

        if DEBUG_SPEED_VERBOSE:
            print("    got speed " + speedStr + " @ " + str(servoPosition) + " for " + str(servoNumber))

    wheel["speed"] = speedStr

    if "speedServoPos" in wheel and wheel["speedServoPos"] != servoPosition:
        wheel["gen"] = brakeDance([wheel["speedServoPos"], servoPosition])

    wheel["speedServoPos"] = servoPosition

    if speedStr == "0" or speedStr == "-0":
        moveServo(servoNumber, servoPosition)
        wheel["speedServoPos"] = servoPosition
    else:
        wheel["speedServoPos"] = servoPosition


def interpolate(value, zerostr, maxstr):
    zero = float(zerostr)
    maxValue = float(maxstr)
    return (maxValue - zero) * value + zero


# use the start value, then go through 0 and -0 and then to the target position
# set up as an infinite generator
def brakeDance(vals):
    # return the start value
    yield vals[0]
    yield vals[1]
    yield vals[0]
    while True:
        yield vals[1]


def driveWheel(wheelName):
    wheel = wheelMap[wheelName]
    wheelCal = wheelCalibrationMap[wheelName]["speed"]

    speedStr = wheel["speed"]
    if "speedServoPos" in wheel and "gen" in wheel:
        # servo position is not a value, but a generator
        servoPosition = wheel["speedServoPos"]
        if wheel["gen"] is not None:
            servoPosition = next(wheel["gen"])

        pwmPart = (int(servoPosition * 10) % 10) // 2
        servoPosition = int(servoPosition) + PWM[pwmPart][pwmIndex]

        servoNumber = wheelCal["servo"]

        if speedStr != "0" and speedStr != "-0":
            moveServo(servoNumber, servoPosition)


def driveWheels():
    global pwmIndex

    driveWheel("fl")
    driveWheel("fr")
    driveWheel("bl")
    driveWheel("br")
    pwmIndex += 1
    if pwmIndex >= len(PWM[0]):
        pwmIndex = 0


def servoTopic(topic, payload, groups):
    servo = int(groups[0])
    moveServo(servo, payload)
    print("servo")


def wheelDegTopic(topic, payload, groups):
    wheelName = groups[0]

    if wheelName in wheelMap:
        wheel = wheelMap[wheelName]
        wheelCal = wheelCalibrationMap[wheelName]

        if DEBUG_TURN:
            print("  Turning wheel: " + wheelName + " to " + str(payload) + " degs")

        handleDeg(wheel, wheelCal["deg"], float(payload))

    else:
        print("ERROR: no wheel with name " + wheelName + " fonund.")


def wheelSpeedTopic(topic, payload, groups):
    wheelName = groups[0]

    if wheelName in wheelMap:
        wheel = wheelMap[wheelName]
        wheelCal = wheelCalibrationMap[wheelName]

        if DEBUG_SPEED:
            print("  Setting wheel: " + wheelName + " speed to " + str(payload))
        handleSpeed(wheel, wheelCal["speed"], payload)
    else:
        print("ERROR: no wheel with name " + wheelName + " fonund.")


def wheelsCombined(topic, payload, groups):
    if DEBUG_SPEED:
        print(str(int(time.time() * 1000) % 10000000) + ": wheels " + payload)

    wheelCmds = payload.split(" ")
    for wheelCmd in wheelCmds:
        kv = wheelCmd.split(":")
        if len(kv) > 1:
            wheelName = kv[0][:2]
            command = kv[0][2]
            value = kv[1]

            if wheelName in wheelMap:
                wheel = wheelMap[wheelName]
                wheelCal = wheelCalibrationMap[wheelName]
                if command == "s":
                    handleSpeed(wheel, wheelCal["speed"], value)
                elif command == "d":
                    handleDeg(wheel, wheelCal["deg"], float(value))


if __name__ == "__main__":
    try:
        print("Starting wheels service...")
        print("    initialising wheels...")
        initWheels()
        print("    opening servo blaster file...")
        servoBlasterFile = open("/dev/servoblaster", 'w')

        print("    sbscribing to topics...")
        pyroslib.subscribe("servo/+", servoTopic)
        pyroslib.subscribe("wheel/all", wheelsCombined)
        pyroslib.subscribe("wheel/+/deg", wheelDegTopic)
        pyroslib.subscribe("wheel/+/speed", wheelSpeedTopic)
        pyroslib.init("wheels-service")

        print("  Loading storage details...")
        loadStorage()

        print("Started wheels service.")

        pyroslib.forever(0.02, driveWheels)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
