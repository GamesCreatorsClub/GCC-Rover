#!/usr/bin/python3

import os
import traceback
import re
import pickle
import pyroslib


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
STORAGE_MAP_FILE = "/home/pi/rover-storage.config"
SERVO_REGEX = re.compile("servo/(\d+)")


storageMap = {}
wheelMap = {}
wheelCalibrationMap = {}
wheelMap["servos"] = {}


def initWheel(wheelName, motorServo, steerServo):
    wheelMap[wheelName] = {
        "deg": 0,
        "speed": 0
    }

    defaultWheelCal = {
        "deg": {
            "servo": steerServo,
            "90": "70",
            "0": "160",
            "-90": "230"
        },
        "speed": {
            "servo": motorServo,
            "-300": "95",
            "0": "155",
            "300": "215"
        }
    }

    if wheelName not in wheelCalibrationMap:
        wheelCalibrationMap[wheelName] = defaultWheelCal

    if "deg" not in wheelCalibrationMap[wheelName]:
        wheelCalibrationMap[wheelName]["deg"] = defaultWheelCal["deg"]

    if "speed" not in wheelCalibrationMap[wheelName]:
        wheelCalibrationMap[wheelName]["speed"] = defaultWheelCal["speed"]

    if "servo" not in wheelCalibrationMap[wheelName]["deg"]:
        wheelCalibrationMap[wheelName]["deg"]["servo"] = defaultWheelCal["deg"]["servo"]
    if "90" not in wheelCalibrationMap[wheelName]["deg"]:
        wheelCalibrationMap[wheelName]["deg"]["90"] = defaultWheelCal["deg"]["90"]
    if "0" not in wheelCalibrationMap[wheelName]["deg"]:
        wheelCalibrationMap[wheelName]["deg"]["0"] = defaultWheelCal["deg"]["0"]
    if "-90" not in wheelCalibrationMap[wheelName]["deg"]:
        wheelCalibrationMap[wheelName]["deg"]["-90"] = defaultWheelCal["deg"]["-90"]

    if "servo" not in wheelCalibrationMap[wheelName]["speed"]:
        wheelCalibrationMap[wheelName]["speed"]["servo"] = defaultWheelCal["speed"]["servo"]
    if "-300" not in wheelCalibrationMap[wheelName]["speed"]:
        wheelCalibrationMap[wheelName]["-300"]["servo"] = defaultWheelCal["speed"]["-300"]
    if "0" not in wheelCalibrationMap[wheelName]["speed"]:
        wheelCalibrationMap[wheelName]["speed"]["0"] = defaultWheelCal["speed"]["0"]
    if "300" not in wheelCalibrationMap[wheelName]["speed"]:
        wheelCalibrationMap[wheelName]["speed"]["300"] = defaultWheelCal["speed"]["300"]


def initWheels():
    global wheelCalibrationMap

    if "wheels" not in storageMap:
        storageMap["wheels"] = {}

    if "cal" not in storageMap["wheels"]:
        storageMap["wheels"]["cal"] = {}

    wheelCalibrationMap = storageMap["wheels"]["cal"]

    initWheel("fr", 0, 1)
    initWheel("fl", 2, 3)
    initWheel("br", 4, 5)
    initWheel("bl", 6, 7)


def moveServo(servoid, angle):
    # TODO move this out to separate service
    f = open("/dev/servoblaster", 'w')
    f.write(str(servoid) + "=" + str(angle) + "\n")
    f.close()


def handleServo(servoid, angle=0):
    wheelMap["servos"][str(servoid)] = angle
    moveServo(servoid, angle)


def handleWheel(mqttClient, topic, payload):
    # wheel/<name>/<deg|speed>

    topicsplit = topic.split("/")
    wheelName = topicsplit[1]
    command = topicsplit[2]

    if wheelName in wheelMap:
        wheel = wheelMap[wheelName]
        wheelCal = wheelCalibrationMap[wheelName]

        if DEBUG:
            print("Handing action: " + str(topicsplit) + ", " + str(payload))

        if command == "deg":
            if DEBUG:
                print("  Turning wheel: " + wheelName + " to " + str(payload) + " degs")
            handleDeg(wheel, wheelCal["deg"], float(payload))
        elif command == "speed":
            if DEBUG:
                print("  Setting wheel: " + wheelName + " speed to " + str(payload))
            handleSpeed(wheel, wheelCal["speed"], float(payload))
    else:
        print("ERROR: no wheel with name " + wheelName + " fonund.")


def handleDeg(wheel, wheelCal, degrees):
    if degrees >= 0:
        servoPosition = interpolate(degrees / 90.0, wheelCal["0"], wheelCal["90"])
    else:
        servoPosition = interpolate((degrees + 90) / 90.0, wheelCal["-90"], wheelCal["0"])

    wheel["deg"] = degrees
    wheel["degsServoPos"] = servoPosition
    servoNumber = wheelCal["servo"]

    moveServo(servoNumber, servoPosition)


def handleSpeed(wheel, wheelCal, speed):
    if speed >= 0:
        servoPosition = interpolate(speed / 300, wheelCal["0"], wheelCal["300"])
    else:
        servoPosition = interpolate((speed + 300) / 300, wheelCal["-300"], wheelCal["0"])

    wheel["speed"] = speed
    wheel["speedServoPos"] = servoPosition
    servoNumber = wheelCal["servo"]

    if str(speed) == "0":
        moveServo(servoNumber, servoPosition)


def interpolate(value, zerostr, maxstr):
    zero = float(zerostr)
    maxValue = float(maxstr)
    return (maxValue - zero) * value + zero


def driveWheel(wheelName):
    wheel = wheelMap[wheelName]
    wheelCal = wheelCalibrationMap[wheelName]["speed"]

    speed = wheel["speed"]
    if "speedServoPos" in wheel:
        servoPosition = wheel["speedServoPos"]

        servoNumber = wheelCal["servo"]

        if str(speed) != "0":
            moveServo(servoNumber, servoPosition)


def driveWheels():
    driveWheel("fl")
    driveWheel("fr")
    driveWheel("bl")
    driveWheel("br")


# --- Storage Map code -------------------------
def loadStorageMap():
    if os.path.exists(STORAGE_MAP_FILE):
        file = open(STORAGE_MAP_FILE, "rb")
        loaded = pickle.load(file)
        file.close()

        if DEBUG:
            print("  Loaded " + str(loaded))

        for key in loaded:
            storageMap[key] = loaded[key]

        print("  Storage map is " + str(storageMap))
    else:
        print("  No storage map found @ " + STORAGE_MAP_FILE)


def composeRecursively(m, prefix):
    res = ""
    for key in m:
        if type(m[key]) is dict:
            newPrefix = prefix + key + "/"
            res += composeRecursively(m[key], newPrefix)
        else:
            res += prefix + key + "=" + str(m[key]) + "\n"

    return res


def readoutStorage():
    pyroslib.publish("storage/values", composeRecursively(storageMap, ""))


def writeStorage(topicSplit, value):
    m = storageMap
    for i in range(0, len(topicSplit) - 1):
        key = topicSplit[i]
        if key not in m:
            m[key] = {}
        m = m[key]
    key = topicSplit[len(topicSplit) - 1]
    m[key] = value

    if DEBUG:
        print("Storing to storage " + str(topicSplit) + " = " + value)

    file = open(STORAGE_MAP_FILE, 'wb')

    pickle.dump(storageMap, file, 0)

    file.close()

# --- Storage Map code end -------------------------


def servoTopic(topic, payload, groups):
    servo = int(groups[0])
    moveServo(servo, payload)


def wheelDegTopic(topic, payload, groups):
    wheelName = groups[0]

    if wheelName in wheelMap:
        wheel = wheelMap[wheelName]
        wheelCal = wheelCalibrationMap[wheelName]

        if DEBUG:
            print("  Turning wheel: " + wheelName + " to " + str(payload) + " degs")

        handleDeg(wheel, wheelCal["deg"], float(payload))

    else:
        print("ERROR: no wheel with name " + wheelName + " fonund.")


def wheelSpeedTopic(topic, payload, groups):
    wheelName = groups[0]

    if wheelName in wheelMap:
        wheel = wheelMap[wheelName]
        wheelCal = wheelCalibrationMap[wheelName]

        if DEBUG:
            print("  Setting wheel: " + wheelName + " speed to " + str(payload))
        handleSpeed(wheel, wheelCal["speed"], float(payload))
    else:
        print("ERROR: no wheel with name " + wheelName + " fonund.")


def storageWriteTopic(topic, payload, groups):
    writeStorage(groups, payload)


def storageReadTopic(topic, payload, groups):
    if DEBUG:
        print("Reading out storage")
    readoutStorage()


if __name__ == "__main__":
    try:
        print("Starting wheels service...")

        loadStorageMap()
        initWheels()

        pyroslib.subscribe("servo/+", servoTopic)
        pyroslib.subscribe("wheel/+/deg", wheelDegTopic)
        pyroslib.subscribe("wheel/+/speed", wheelSpeedTopic)
        pyroslib.subscribe("storage/write/#", storageWriteTopic)
        pyroslib.subscribe("storage/read", storageReadTopic)
        pyroslib.init("wheels-service")

        print("Started wheels service.")

        pyroslib.forever(0.02, driveWheels)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
