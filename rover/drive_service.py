#!/usr/bin/python3

import time
import traceback
import pyroslib

DELAY = 0.15

STRAIGHT = 1
SLANT = 2
SIDEWAYS = 3

STARTING_ROTATION_SPEED = 30

current_speed = 0

wheelPosition = STRAIGHT
gyroReadOut = 0

previousGyroRead = 0

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


def turnOnSpot():
    global gyroReadOut

    gyroReadOut = 0

    slantWheels()

    target = int(currentCommand["args"])
    setRotationSpeed(STARTING_ROTATION_SPEED)


def setRotationSpeed(speed):
    global current_speed

    current_speed = speed
    target = int(currentCommand["args"])
    if target > 0:
        amount = speed
    else:
        amount = -speed

    wheelSpeed("fl", amount)
    wheelSpeed("fr", -amount)
    wheelSpeed("bl", amount)
    wheelSpeed("br", -amount)

    current_speed = speed


def turnOnSpotControl():
    global previousGyroRead, current_speed

    print("Gyro is " + str(gyroReadOut))
    target = int(currentCommand["args"])
    rotational_speed = abs(gyroReadOut - previousGyroRead)
    if rotational_speed < 0.5:
        current_speed += 1

        print("Change: ", str(rotational_speed), " Current_speed: ", str(current_speed))

        setRotationSpeed(current_speed)
    elif rotational_speed > 0.8:
        current_speed -= 1
        print("Change: ", str(rotational_speed), " Current_speed: ", str(current_speed))

    if (target > 0 and gyroReadOut >= target) or (target < 0 and gyroReadOut <= target):
        newCommandMsg("", "", ["stop"])



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


def stopAllWheels():
    wheelSpeed("fl", 0)
    wheelSpeed("fr", 0)
    wheelSpeed("bl", 0)
    wheelSpeed("br", 0)
    print("Stopping all wheels!")


def nothing():
    return


commands = {
    "stop": {
        "start": stopAllWheels
    },
    "rotate": {
        "start": turnOnSpot,
        "do": turnOnSpotControl
    }
}

currentCommand = {}
continuousTimeout = 50


def newCommandMsg(topic, message, groups):
    global currentCommand

    if "stop" in currentCommand:
        currentCommand["stop"]()

    if groups[0] in commands:
        currentCommand = commands[groups[0]]
        currentCommand["args"] = message

        if "start" in currentCommand:
            currentCommand["start"]()
    else:
        print("Received unknown command " + groups[0])


def handleGyro(topic, message, groups):
    global gyroReadOut, previousGyroRead
    previousGyroRead =  gyroReadOut
    gyroReadOut += float(message)


def loop():
    global continuousTimeout
    continuousTimeout -= 1
    if continuousTimeout <= 0:
        continuousTimeout = 50
        pyroslib.publish("sensor/gyro/continuous", "")

    if "do" in currentCommand:
        currentCommand["do"]()


if __name__ == "__main__":
    try:
        print("Starting drive service...")

        pyroslib.subscribe("move/+", newCommandMsg)
        pyroslib.subscribe("sensor/gyro", handleGyro)
        pyroslib.init("drive-service")

        print("Started drive service.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
