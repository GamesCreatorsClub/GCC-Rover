
import os
import sys
import time
import pickle
import paho.mqtt.client as mqtt
import re


#
# wheels service
#
#
# This service is responsible for moving wheels on the rover.
# Current implementation also handles:
#     - servos
#     - storage map
#

storageMap = {}
wheelMap = {}
wheelCalibrationMap = {}

DEBUG = False

client = mqtt.Client("wheels-service")

STORAGE_MAP_FILE = "/home/pi/rover-storage.config"

SERVO_REGEX = re.compile("servo/(\d+)")

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

    print("  Started wheelhandler.")


def moveServo(servoid, angle):
    f = open("/dev/servoblaster", 'w')
    f.write(str(servoid) + "=" + str(angle) + "\n")
    f.close()


def handleWheel(client, topic, payload):
    # wheel/<name>/<deg|speed>

    topicsplit = topic.split("/")
    wheelName = topicsplit[1]
    command = topicsplit[2]

    if wheelName in wheelMap:
        wheel = wheelMap[wheelName]
        wheelCal = wheelCalibrationMap[wheelName]

        if DEBUG:
            print("Handing action: " +  str(topicsplit) + ", " + str(payload))

        if command == "deg":
            if DEBUG:
                print("  Turning wheel: " + wheelName + " to " + str(payload) + " degs")
            handleDeg(wheel, wheelCal["deg"], float(payload))
        elif command == "speed":
            if DEBUG:
                print("  Setting wheel: " + wheelName + " speed to " + str(payload))
            handleSpeed(wheel, wheelCal["speed"], float(payload))
    else:
        print("ERROR: no wheel with name " +  wheelName + " fonund.")

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
    max = float(maxstr)
    return (max - zero) * value + zero


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
            print("  Loaded " +  str(loaded))

        for key in loaded:
            storageMap[key] = loaded[key]

        print("  Storage map is " + str(storageMap))
    else:
        print("  No storage map found @ " + STORAGE_MAP_FILE)


def composeRecursively(map, prefix):
    res = ""
    for key in map:
        if type(map[key]) is dict:
            newPrefix = prefix + key + "/"
            res = res + composeRecursively(map[key], newPrefix)
        else:
            res = res + prefix + key + "=" + str(map[key]) + "\n"

    return  res


def readoutStorage():
    client.publish("storage/values", composeRecursively(storageMap, ""))


def writeStorage(topicsplit, value):
    map = storageMap
    for i in range(2, len(topicsplit) - 1):
        key = topicsplit[i]
        if key not in map:
            map[key] = {}
        map = map[key]
    key = topicsplit[len(topicsplit) - 1]
    map[key] = value

    if DEBUG:
        print("Storing to storage " + str(topicsplit) + " = " + value)

    file = open("rover-storage.config", 'wb')

    pickle.dump(storageMap, file, 0)

    file.close()

# --- Storage Map code end -------------------------


def onConnect(client, data, rc):
    try:
        if rc == 0:
            client.subscribe("servo/+", 0)
            client.subscribe("wheel/+/deg", 0)
            client.subscribe("wheel/+/speed", 0)
            client.subscribe("storage/write/#", 0)
            client.subscribe("storage/read", 0)
        else:
            print("ERROR: Connection returned error result: " + str(rc))
            sys.exit(rc)
    except Exception as e:
        print("ERROR: Got exception on connect; " + str(e))


def onMessage(client, data, msg):
    global dist

    try:
        payload = str(msg.payload, 'utf-8')
        topic = msg.topic


        if  topic.startswith("wheel/"):
            handleWheel(client, topic, payload)
        else:
            servoMatch = SERVO_REGEX.match(msg.topic)
            if servoMatch:
                servo = int(servoMatch.group(1))
                # print("servo matched: " + topic + ", servo " + str(servo))
                moveServo(servo, payload)

            elif topic.startswith("storage/"):
                topicsplit = topic.split("/")
                if topicsplit[1] == "read":
                    if DEBUG:
                        print("Reading out storage")
                    readoutStorage()
                elif topicsplit[1] == "write":
                    writeStorage(topicsplit, payload)
    except Exception as e:
        print("ERROR: Got exception on message; " + str(e))


#
# Initialisation
#

print("Starting wheels-service...")

loadStorageMap()

client.on_connect = onConnect
client.on_message = onMessage

client.connect("localhost", 1883, 60)

initWheels()

print("Started wheels-service.")

while True:
    try:
        for i in range(0, 10):
            time.sleep(0.0015)
            client.loop(0.0005)
        driveWheels()
    except Exception as e:
        print("ERROR: Got exception in main loop; " + str(e))
