#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import time
import traceback
import pyroslib
import math

DEBUG = False
DEBUG_TIMING = True

WHEEL_CIRCUMFERENCE = 15  # 15mm

DELAY = 0.50

STRAIGHT = 1
SLANT = 2
SIDEWAYS = 3

LEFT = 1
RIGHT = 2
FORWARD = 3
BACK = 4

MODE_NOTHING = 0
MODE_STARTING = 1
MODE_DRIVING = 2

BREAKING_FACTOR = 0.1
STARTING_ROTATION_SPEED = 28
ROTATIONAL_SPEED_OVERSHOOT_FACTOR = 6
RAMP_UP_TIMEOUT = 20

wheelPosition = STRAIGHT

gyroReadOut = 0
previousGyroRead = 0

accelXReadOut = 0
accelYReadOut = 0
accelDeltaTime = 0
totalDistance = 0

previousControlTime = 0

continuousTimeout = 50

originalDirection = None
leftMovingSpeed = -1
rightMovingSpeed = 1
targetGyro = 0
currentSpeed = 0
startSpeed = 0
lastRotationalSpeed = 0
startedCommandTime = 0

_needGyro = False
_needAccel = False


def sign(x):
    if x > 0:
        return 1
    if x == 0:
        return 0
    return -1


def log(source, msg):
    if DEBUG:
        print(source + ": " + msg)


def doNothing():
    pass


_currentState = doNothing
_nextState = doNothing
_timeout = 0


def nextState(state):
    global _currentState
    _currentState = state


def timeout(ticks, nextStateRef):
    global _currentState, _nextState, _timeout

    _timeout = ticks
    _nextState = nextStateRef
    _currentState = timeoutState


def timeoutState():
    global _currentState, _timeout

    if _timeout > 0:
        # print("  timeoutState: " + str(timeout))
        _timeout -= 1
    else:
        # print("  timeoutState: moving on " + str(_nextState))
        _currentState = _nextState


def processCurrentState():
    _currentState()


def allWheels(fld, frd, bld, brd, fls, frs, bls, brs):
    pyroslib.publish("wheel/all", "fld:" + str(fld) + " frd:" + str(frd) + " bld:" + str(bld) + " brd:" + str(brd) + " fls:" + str(fls) + " frs:" + str(frs) + " bls:" + str(bls) + " brs:" + str(brs))


def allWheelsDeg(fld, frd, bld, brd):
    pyroslib.publish("wheel/all", "fld:" + str(fld) + " frd:" + str(frd) + " bld:" + str(bld) + " brd:" + str(brd))


def allWheelsSpeed(fls, frs, bls, brs):
    pyroslib.publish("wheel/all", "fls:" + str(fls) + " frs:" + str(frs) + " bls:" + str(bls) + " brs:" + str(brs))


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

    allWheelsDeg(0, 0, 0, 0)
    # wheelDeg("fl", 0)
    # wheelDeg("fr", 0)
    # wheelDeg("bl", 0)
    # wheelDeg("br", 0)

    if wheelPosition != STRAIGHT:
        time.sleep(DELAY)
        wheelPosition = STRAIGHT


def slantWheels():
    global wheelPosition, DELAY, SLANT

    allWheelsDeg(60.0, -60.0, -60.0, 60.0)
    # wheelDeg("fl", 60.0)
    # wheelDeg("fr", -60.0)
    # wheelDeg("bl", -60.0)
    # wheelDeg("br", 60.0)

    if wheelPosition != SLANT:
        time.sleep(DELAY)
        wheelPosition = SLANT


def sidewaysWheels():
    global wheelPosition, DELAY, SIDEWAYS

    allWheelsDeg(90.0, -90.0, -90.0, 90.0)
    # wheelDeg("fl", 90.0)
    # wheelDeg("fr", -90.0)
    # wheelDeg("bl", -90.0)
    # wheelDeg("br", 90.0)

    if wheelPosition != SIDEWAYS:
        time.sleep(DELAY)
        wheelPosition = SIDEWAYS


def setRotationSpeed(speed):
    allWheelsSpeed(speed, -speed, speed, -speed)
    # wheelSpeed("fl", speed)
    # wheelSpeed("fr", -speed)
    # wheelSpeed("bl", speed)
    # wheelSpeed("br", -speed)


def rotate():
    global gyroReadOut

    slantWheels()

    speed = int(currentCommand["args"])

    setRotationSpeed(speed)
    log("rotate", "s=" + str(speed))


def turnOnSpot():
    global gyroReadOut, targetGyro
    global currentSpeed, startSpeed, leftMovingSpeed, rightMovingSpeed
    global startedCommandTime, lastRotationalSpeed
    global originalDirection

    startedCommandTime = time.time()
    log("main", "Started turning")
    gyroReadOut = 0

    def setCurrentSpeed(speed):
        global currentSpeed
        setRotationSpeed(speed)
        currentSpeed = speed

    def increaseSpeed():
        if originalDirection == LEFT:
            setCurrentSpeed(currentSpeed - 1)
        else:
            setCurrentSpeed(currentSpeed + 1)

    def decreaseSpeed():
        global currentSpeed
        if originalDirection == LEFT:
            setCurrentSpeed(currentSpeed + 1)
        else:
            setCurrentSpeed(currentSpeed - 1)

    def calibrateGyro():
        pyroslib.publish("sensor/gyro/continuous", "calibrate,50")
        timeout(51, fetchCalibrated)

    def fetchCalibrated():
        pyroslib.publish("sensor/gyro/continuous", "start")
        nextState(startUp)

    def startUp():
        setCurrentSpeed(currentSpeed)
        timeout(10, waitToStartMoving)
        log("startUp", "speed=" + str(currentSpeed) + ", gyro " + str(gyroReadOut))

    def waitToStartMoving():
        global currentSpeed, leftMovingSpeed, rightMovingSpeed, startSpeed, _timeout

        if abs(gyroReadOut) < 0.5:
            increaseSpeed()
            log("waitToStartMoving", "increasing speed to " + str(currentSpeed) + ", gyro " + str(gyroReadOut) + " <=> " + str(targetGyro))
            _timeout = RAMP_UP_TIMEOUT
            nextState(waitToStartMovingNoIncrease)
        elif abs(gyroReadOut) > 2.0:
            log("waitToStartMoving", "stared too fast " + str(currentSpeed) + ", gyro " + str(gyroReadOut) + " <=> " + str(targetGyro))
            if originalDirection == LEFT:
                setCurrentSpeed(int(currentSpeed * 0.5))
            else:
                setCurrentSpeed(int(currentSpeed * 0.5))
            _timeout = RAMP_UP_TIMEOUT
            nextState(waitToStartMovingNoIncrease)
        else:
            increaseSpeed()
            if originalDirection == LEFT:
                leftMovingSpeed = currentSpeed
                startSpeed = currentSpeed
                log("waitToStartMoving", "recorded leftMovingSpeed " + str(leftMovingSpeed))
            else:
                rightMovingSpeed = currentSpeed
                startSpeed = currentSpeed
                log("waitToStartMoving", "recorded rightMovingSpeed " + str(rightMovingSpeed))
            nextState(turnControl)

    def waitToStartMovingNoIncrease():
        global currentSpeed, leftMovingSpeed, rightMovingSpeed, startSpeed, _timeout
        setCurrentSpeed(currentSpeed)

        if abs(gyroReadOut) < 1:
            if _timeout > 0:
                _timeout -= 1
            else:
                nextState(waitToStartMoving)
        else:
            if originalDirection == LEFT:
                leftMovingSpeed = currentSpeed
                startSpeed = currentSpeed
                log("waitToStartMovingNI", "recorded leftMovingSpeed " + str(leftMovingSpeed) + " @ " + str(gyroReadOut))
            else:
                rightMovingSpeed = currentSpeed
                startSpeed = currentSpeed
                log("waitToStartMovingNI", "recorded rightMovingSpeed " + str(rightMovingSpeed) + " @ " + str(gyroReadOut))
            nextState(turnControl)

    def turnControl():
        global _timeout
        rotational_speed = gyroReadOut - previousGyroRead
        if originalDirection == RIGHT and targetGyro < gyroReadOut + rotational_speed * ROTATIONAL_SPEED_OVERSHOOT_FACTOR:
            log("turnControl", "getting close @ " + str(rotational_speed) + " gyro + " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target")
            setCurrentSpeed(0)
            timeout(5, startBreaking)
        elif originalDirection == LEFT and targetGyro > gyroReadOut + rotational_speed * ROTATIONAL_SPEED_OVERSHOOT_FACTOR:
            log("turnControl", "getting close @ " + str(rotational_speed) + " gyro - " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target")
            setCurrentSpeed(0)
            timeout(5, startBreaking)
        elif abs(rotational_speed) < 0.05:
            increaseSpeed()
            log("turnControl", "increasing speed " + str(currentSpeed) + " @ " + str(rotational_speed) + " gyro " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target")
            _timeout = 10
            nextState(turnControlNoIncrease)
        elif abs(rotational_speed) > 1.5 and abs(currentSpeed - startSpeed) > 1:
            decreaseSpeed()
            log("turnControl", "decreasing speed " + str(currentSpeed) + " @ " + str(rotational_speed) + " gyro " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target" + ", threshold " + str(abs(currentSpeed - startSpeed)))
            _timeout = 10
            nextState(turnControlNoIncrease)
        else:
            setCurrentSpeed(currentSpeed)
            log("turnControl", " coasting @ " + str(rotational_speed) + " gyro " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target")

    def turnControlNoIncrease():
        global _timeout

        rotational_speed = gyroReadOut - previousGyroRead
        if originalDirection == RIGHT and targetGyro < gyroReadOut + rotational_speed * ROTATIONAL_SPEED_OVERSHOOT_FACTOR:
            log("turnControlNI", "getting close @ " + str(rotational_speed) + " gyro + " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target")
            setCurrentSpeed(0)
            timeout(5, startBreaking)
        elif originalDirection == LEFT and targetGyro > gyroReadOut + rotational_speed * ROTATIONAL_SPEED_OVERSHOOT_FACTOR:
            log("turnControlNI", "getting close @ " + str(rotational_speed) + " gyro - " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target")
            setCurrentSpeed(0)
            timeout(5, startBreaking)
        elif _timeout == 0:
            log("turnControlNI", " reached timeout @ " + str(rotational_speed) + " gyro " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target")
            nextState(turnControl)
        else:
            log("turnControlNI", " speeding up @ " + str(rotational_speed) + " gyro " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target")
            _timeout -= 1

    def startBreaking():
        if originalDirection == LEFT:
            setCurrentSpeed(rightMovingSpeed * BREAKING_FACTOR)
        else:
            setCurrentSpeed(leftMovingSpeed * BREAKING_FACTOR)
        log("startBreaking", "gyro " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target @ speed " + str(currentSpeed))
        timeout(5, stopBreaking)

    def stopBreaking():
        log("stopBreaking", "end to rotation " + str(gyroReadOut))
        setCurrentSpeed(0)
        setStopAll()
        dontNeedGyro()
        pyroslib.publish("move/feedback", "done-turn," + str(gyroReadOut))

    targetGyro = float(currentCommand["args"])
    if targetGyro < gyroReadOut:
        originalDirection = LEFT
        currentSpeed = leftMovingSpeed + 2
        if currentSpeed > 0:
            currentSpeed = 0
        startSpeed = currentSpeed
    else:
        originalDirection = RIGHT
        currentSpeed = rightMovingSpeed - 2
        if currentSpeed < 0:
            currentSpeed = 0
        startSpeed = currentSpeed

    needGyro()

    slantWheels()
    if wheelPosition != SLANT:
        timeout(50, calibrateGyro)
    else:
        nextState(calibrateGyro)


def faceAngleFront(dist):
    x = math.atan2(36.5, dist - 69)

    return math.degrees(x) - 90.0


def faceAngleBack(dist):
    x = math.atan2(36.5, dist + 69)

    return math.degrees(x) - 90.0


def orbit():
    args = currentCommand["args"].split(" ")

    d = int(args[0])
    if len(args) > 1:
        speed = int(args[1])
    else:
        speed = 0
    frontAngle = faceAngleFront(abs(d))
    backAngle = faceAngleBack(abs(d))

    innerSpeed = calcInnerSpeed(speed, abs(d))
    outerSpeed = calcOuterSpeed(speed, abs(d))

    adjust = 0
    if innerSpeed > 300:
        adjust = innerSpeed - 300
    elif innerSpeed < -300:
        adjust = innerSpeed + 300
    elif outerSpeed > 300:
        adjust = outerSpeed - 300
    elif outerSpeed < -300:
        adjust = outerSpeed + 300

    innerSpeed -= adjust
    outerSpeed -= adjust

    log("orbit", "d=" + str(d) + " s=" + str(speed) + " fa=" + str(frontAngle) + " ba=" + str(backAngle) + " is=" + str(innerSpeed) + " os=" + str(outerSpeed) + " adj=" + str(adjust) + " args:" + str(args))

    allWheels(str(frontAngle), str(-frontAngle), str(backAngle), str(-backAngle), str(-innerSpeed), str(innerSpeed), str(-outerSpeed), str(outerSpeed))
    # wheelDeg("fl", str(frontAngle))
    # wheelDeg("fr", str(-frontAngle))
    # wheelDeg("bl", str(backAngle))
    # wheelDeg("br", str(-backAngle))
    #
    # wheelSpeed("fl", str(-innerSpeed))
    # wheelSpeed("fr", str(innerSpeed))
    # wheelSpeed("bl", str(-outerSpeed))
    # wheelSpeed("br", str(outerSpeed))


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
    if len(args) > 1:
        speed = int(args[1])
    else:
        speed = 0
    frontAngle = sideAngleFront(abs(d))
    backAngle = sideAngleBack(abs(d))

    innerSpeed = calcInnerSpeed(speed, abs(d))
    outerSpeed = calcOuterSpeed(speed, abs(d))

    adjust = 0
    if innerSpeed > 300:
        adjust = innerSpeed - 300
    elif innerSpeed < -300:
        adjust = innerSpeed + 300
    elif outerSpeed > 300:
        adjust = outerSpeed - 300
    elif outerSpeed < -300:
        adjust = outerSpeed + 300

    innerSpeed -= adjust
    outerSpeed -= adjust

    log("steer", "d=" + str(d) + " s=" + str(speed) + " fa=" + str(frontAngle) + " ba=" + str(backAngle) + " is=" + str(innerSpeed) + " os=" + str(outerSpeed) + " adj=" + str(adjust) + " args:" + str(args))

    if d >= 0:
        # wheelDeg("fl", str(backAngle))
        # wheelDeg("bl", str(-backAngle))
        # wheelDeg("fr", str(frontAngle))
        # wheelDeg("br", str(-frontAngle))
        if speed != 0:
            allWheels(backAngle, frontAngle, -backAngle, -frontAngle, outerSpeed, innerSpeed, outerSpeed, innerSpeed)
            # wheelSpeed("fl", str(outerSpeed))
            # wheelSpeed("fr", str(innerSpeed))
            # wheelSpeed("bl", str(outerSpeed))
            # wheelSpeed("br", str(innerSpeed))
        else:
            allWheelsDeg(backAngle, frontAngle, -backAngle, -frontAngle)

    else:
        # wheelDeg("fl", str(-frontAngle))
        # wheelDeg("bl", str(frontAngle))
        # wheelDeg("fr", str(-backAngle))
        # wheelDeg("br", str(backAngle))
        if speed != 0:
            allWheels(-frontAngle, -backAngle, frontAngle, backAngle, innerSpeed, outerSpeed, innerSpeed, outerSpeed)
            # wheelSpeed("fl", str(innerSpeed))
            # wheelSpeed("fr", str(outerSpeed))
            # wheelSpeed("bl", str(innerSpeed))
            # wheelSpeed("br", str(outerSpeed))
        else:
            allWheelsDeg(-frontAngle, -backAngle, frontAngle, backAngle)


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

        if DEBUG_TIMING:
            print(str(int(time.time() * 1000) % 10000000) + ": driving  fld:" + str(angle) + " frd:" + str(angle) + " bld:" + str(angle) + " brd:" + str(angle) + " fls:" + str(speed) + " frs:" + str(speed) + " bls:" + str(speed) + " brs:" + str(speed))
        allWheels(angle, angle, angle, angle, speed, speed, speed, speed)
        # wheelDeg("fl", angle)
        # wheelDeg("fr", angle)
        # wheelDeg("bl", angle)
        # wheelDeg("br", angle)
        #
        # wheelSpeed("fl", speed)
        # wheelSpeed("fr", speed)
        # wheelSpeed("bl", speed)
        # wheelSpeed("br", speed)

    except:
        return


def stopAllWheels():
    allWheelsSpeed(0, 0, 0, 0)
    # wheelSpeed("fl", 0)
    # wheelSpeed("fr", 0)
    # wheelSpeed("bl", 0)
    # wheelSpeed("br", 0)
    # print("Stopping all wheels!")
    return


def alignAllWheels():
    allWheelsDeg(0, 0, 0, 0)
    # wheelDeg("fl", 0)
    # wheelDeg("fr", 0)
    # wheelDeg("bl", 0)
    # wheelDeg("br", 0)


commands = {
    "stop": {
        "start": stopAllWheels,
        "do": doNothing
    },
    "rotate": {
        "start": rotate,
        "do": doNothing
    },
    "drive": {
        "start": drive,
        "do": doNothing
    },
    "orbit": {
        "start": orbit,
        "do": doNothing
    },
    "steer": {
        "start": steer,
        "do": doNothing
    },
    "turn": {
        "start": turnOnSpot,
        "do": processCurrentState
    }
}

currentCommand = {}


def processCommand(topic, message, groups):
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


def setStopAll():
    processCommand("move/stop", "stop", ["stop"])


def handleGyro(topic, message, groups):
    global gyroReadOut, previousGyroRead
    previousGyroRead = gyroReadOut
    data = message.split(",")
    gyroReadOut += float(data[2])


def handleAccel(topic, message, groups):
    global accelXReadOut, accelYReadOut, accelDeltaTime

    data = message.split(",")
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

        pyroslib.subscribe("move/+", processCommand)
        pyroslib.subscribe("sensor/gyro", handleGyro)
        pyroslib.subscribe("sensor/accel", handleAccel)
        pyroslib.init("drive-service")

        print("Started drive service.")

        stopAllWheels()
        alignAllWheels()

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
