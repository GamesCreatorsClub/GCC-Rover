#!/usr/bin/python3

import time
import traceback
import pyroslib
import math


WHEEL_CIRCUMFERENCE = 15  # 15mm

DELAY = 0.50

STRAIGHT = 1
SLANT = 2
SIDEWAYS = 3

MODE_NOTHING = 0
MODE_STARTING = 1
MODE_DRIVING = 2

STARTING_ROTATION_SPEED = 30

current_speed = 0
current_motor_speed = 0

wheelPosition = STRAIGHT

gyroReadOut = 0
previousGyroRead = 0

accelXReadOut = 0
accelYReadOut = 0
accelDeltaTime = 0
totalDistance = 0

previousControlTime = 0

continuousTimeout = 50

_needGyro = False
_needAccel = False


def sign(x):
    if x > 0:
        return 1
    if x == 0:
        return 0
    return -1


def wheelDeg(wheelName, angle):
    topic = "wheel/" + wheelName + "/deg"
    pyroslib.publish(topic, str(angle))
    # print("Published topic=" +  topic + "; msg=" + str(angle))


def wheelSpeed(wheelName, speed):
    topic = "wheel/" + wheelName + "/speed"
    pyroslib.publish(topic, str(speed))
    # print("Published topic=" +  topic + "; msg=" + str(speed))


def needGyro():
    global continuousTimeout, _needGyro

    continuousTimeout = 50
    _needGyro = True

    pyroslib.publish("sensor/gyro/continuous", "start")


def needAccel():
    global continuousTimeout, _needAccel

    continuousTimeout = 50
    _needAccel = True

    pyroslib.publish("sensor/accel/continuous", "start")


def dontNeedGyro():
    global _needGyro

    _needGyro = False


def dontNeedAccel():
    global _needAccel

    _needAccel = False


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


def setRotationSpeed(speed):
    global current_motor_speed

    current_motor_speed = speed
    direction = currentCommand["direction"]
    if direction > 0:
        amount = speed
    else:
        amount = -speed

    wheelSpeed("fl", amount)
    wheelSpeed("fr", -amount)
    wheelSpeed("bl", amount)
    wheelSpeed("br", -amount)

    current_motor_speed = speed


def setForwardSpeed(speed):
    global current_motor_speed

    current_motor_speed = speed
    direction = currentCommand["direction"]
    if direction > 0:
        amount = speed
    else:
        amount = -speed

    wheelSpeed("fl", amount)
    wheelSpeed("fr", amount)
    wheelSpeed("bl", amount)
    wheelSpeed("br", amount)

    current_motor_speed = speed


def setSideSpeed(speed):
    global current_motor_speed

    current_motor_speed = speed
    direction = currentCommand["direction"]
    if direction > 0:
        amount = speed
    else:
        amount = -speed

    wheelSpeed("fl", amount)
    wheelSpeed("fr", -amount)
    wheelSpeed("bl", -amount)
    wheelSpeed("br", amount)

    current_motor_speed = speed


def crabAlong(amount):
    sidewaysWheels()
    setSideSpeed(amount)


def turnOnSpot():
    global gyroReadOut

    needGyro()

    gyroReadOut = 0

    slantWheels()

    target = int(currentCommand["args"])
    currentCommand["direction"] = sign(target)

    setRotationSpeed(STARTING_ROTATION_SPEED)


def turnOnSpotControl():
    global previousGyroRead, current_motor_speed

    print("Gyro is " + str(gyroReadOut))
    target = int(currentCommand["args"])
    rotational_speed = abs(gyroReadOut - previousGyroRead)
    if rotational_speed < 0.5:
        current_motor_speed += 1

        print("Change: ", str(rotational_speed), " Current_speed: ", str(current_motor_speed))

        setRotationSpeed(current_motor_speed)
    elif rotational_speed > 0.8:
        current_motor_speed -= 1
        print("Change: ", str(rotational_speed), " Current_speed: ", str(current_motor_speed))
        setRotationSpeed(current_motor_speed)

    if (target > 0 and gyroReadOut >= target) or (target < 0 and gyroReadOut <= target):
        newCommandMsg("", "", ["stop"])
        dontNeedGyro()
        pyroslib.publish("move/response", "done-turn")


def moveMotorsForward():
    moveMotors()
    return


def moveMotorsBack():
    currentCommand["args"] = -int(currentCommand["args"])
    moveMotors()
    return


def moveMotors():
    global accelYReadOut, current_speed, totalDistance

    needAccel()

    accelYReadOut = 0
    totalDistance = 0
    current_speed = 0

    straightenWheels()

    target = int(currentCommand["args"])
    currentCommand["direction"] = sign(target)
    currentCommand["mode"] = MODE_STARTING
    print("currnetCommand=" + str(currentCommand))
    setForwardSpeed(STARTING_ROTATION_SPEED)


def moveMotorsControl():
    global current_motor_speed, totalDistance, previousControlTime, current_speed

    if currentCommand["mode"] == MODE_STARTING:
        print("Accel is " + str(accelYReadOut))

        target = int(currentCommand["args"])
        direction = int(currentCommand["direction"])
        current_speed += - accelYReadOut * accelDeltaTime * direction
        if current_speed < 2:
            current_motor_speed += 1

            print("Total detected speed: ", str(current_speed), " new driving speed: ", str(current_motor_speed), " direction ", str(direction))

            setForwardSpeed(current_motor_speed)
        else:
            currentCommand["mode"] = MODE_DRIVING
    else:
        now = time.time()

        totalDistance += current_motor_speed * WHEEL_CIRCUMFERENCE * (now - previousControlTime) / 60  # RPM * time

        previousControlTime = now

        target = int(currentCommand["args"])
        if __name__ == '__main__':
            if (target > 0 and totalDistance >= target) or (target < 0 and totalDistance >= -target):
                newCommandMsg("", "", ["stop"])
                pyroslib.publish("move/response", "done-move")
                dontNeedAccel()

        # TODO - switching motor at some speed is not enough. Stopping would be far better - or slowing down
        # Slowing down has another risk - stopping before reaching destination. So slowing down should detec
        # if stopped - which, with current hardware, I am not sure how to do so.
    return


distance = 150.0


def faceAngleFront(dist):
    x = math.atan2(36.5, dist - 69)

    return math.degrees(x) - 90.0


def faceAngleBack(dist):
    x = math.atan2(36.5, dist + 69)

    return math.degrees(x) - 90.0


def orbit():
    args = currentCommand["args"].split(" ")
    d = int(args[0])
    speed = int(args[1])

    wheelDeg("fl", str(faceAngleFront(d)))
    wheelDeg("fr", str(-faceAngleFront(d)))
    wheelDeg("bl", str(faceAngleBack(d)))
    wheelDeg("br", str(-faceAngleBack(d)))

    wheelSpeed("fl", str(speed))
    wheelSpeed("fr", str(speed))
    wheelSpeed("bl", str(speed))
    wheelSpeed("br", str(speed))


def sideAngleFront(dist):
    x = math.atan2(69, dist - 36.5)

    return math.degrees(x)


def sideAngleBack(dist):
    x = math.atan2(69, dist + 36.5)

    return math.degrees(x)


def calcInnerSpeed(spd, dist):
    midc = 2 * math.pi * dist
    inc = 2 * math.pi * (dist - 36.5)
    return spd * (inc / midc)


def calcOuterSpeed(spd, dist):
    midc = 2 * math.pi * dist
    outc = 2 * math.pi * (dist + 36.5)
    return spd * (outc / midc)


def steer():
    args = currentCommand["args"].split(" ")

    d = int(args[0])
    speed = int(args[1])
    frontAngle = sideAngleFront(abs(d))
    backAngle = sideAngleBack(abs(d))

    print("d=" + str(d) + " s=" + str(speed) + " fa=" + str(frontAngle) +  " ba= " + str(backAngle))

    innerSpeed = calcInnerSpeed(speed, d)
    outerSpeed = calcOuterSpeed(speed, d)

    if d >= 0:
        wheelDeg("fl", str(frontAngle))
        wheelDeg("bl", str(-frontAngle))
        wheelDeg("fr", str(backAngle))
        wheelDeg("br", str(-backAngle))
        wheelSpeed("fl", str(outerSpeed))
        wheelSpeed("fr", str(innerSpeed))
        wheelSpeed("bl", str(outerSpeed))
        wheelSpeed("br", str(innerSpeed))
    else:
        wheelDeg("fl", str(-backAngle))
        wheelDeg("bl", str(backAngle))
        wheelDeg("fr", str(-frontAngle))
        wheelDeg("br", str(frontAngle))
        wheelSpeed("fl", str(innerSpeed))
        wheelSpeed("fr", str(outerSpeed))
        wheelSpeed("bl", str(innerSpeed))
        wheelSpeed("br", str(outerSpeed))


def drive():
    args = currentCommand["args"].split(" ")
    try:
        angle = float(args[0])
        speed = int(args[1])

        if angle < -90:
            angle += 180
            speed = -speed
        elif angle > 90:
            angle -= 180
            speed = -speed

        wheelDeg("fl", angle)
        wheelDeg("fr", angle)
        wheelDeg("bl", angle)
        wheelDeg("br", angle)

        wheelSpeed("fl", speed)
        wheelSpeed("fr", speed)
        wheelSpeed("bl", speed)
        wheelSpeed("br", speed)

    except:
        return


def stopAllWheels():
    wheelSpeed("fl", 0)
    wheelSpeed("fr", 0)
    wheelSpeed("bl", 0)
    wheelSpeed("br", 0)
    print("Stopping all wheels!")
    return


def nothing():
    return


commands = {
    "stop": {
        "start": stopAllWheels
    },
    "rotate": {
        "start": turnOnSpot,
        "do": turnOnSpotControl
    },
    "forward": {
        "start": moveMotorsForward,
        "do": moveMotorsControl
    },
    "back": {
        "start": moveMotorsBack,
        "do": moveMotorsControl
    },
    "drive": {
        "start": drive,
        "do": nothing
    },
    "orbit": {
        "start": orbit,
        "do": nothing
    },
    "steer": {
        "start": steer,
        "do": nothing
    }
}

currentCommand = {}


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
    previousGyroRead = gyroReadOut
    data = message.split(",")
    gyroReadOut += float(data[2])


def handleAccel(topic, message, groups):
    global accelXReadOut, accelYReadOut, accelDeltaTime

    data = message.split(",")
    # print("Received data " + str(data))
    accelXReadOut += float(data[0])
    accelYReadOut += float(data[1])
    accelDeltaTime = float(data[3])


def loop():
    global continuousTimeout
    continuousTimeout -= 1
    if continuousTimeout <= 0:
        continuousTimeout = 50
        if _needGyro:
            pyroslib.publish("sensor/gyro/continuous", "start")
        if _needAccel:
            pyroslib.publish("sensor/accel/continuous", "start")

    if "do" in currentCommand:
        currentCommand["do"]()


if __name__ == "__main__":
    try:
        print("Starting drive service...")

        pyroslib.subscribe("move/+", newCommandMsg)
        pyroslib.subscribe("sensor/gyro", handleGyro)
        pyroslib.subscribe("sensor/accel", handleAccel)
        pyroslib.init("drive-service")

        print("Started drive service.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
