#!/usr/bin/python3

import time
import traceback
import pyroslib

NAME = "fine driver service"
TOPIC = "finemove"

WHEEL_CIRCUMFERENCE = 15.0  # 15mm

DELAY = 0.50

STRAIGHT = 1
SLANT = 2
SIDEWAYS = 3

MODE_NOTHING = 0
MODE_STARTING = 2
MODE_DRIVING = 3
MODE_STOPPING = 4

LEFT = 1
RIGHT = 2
FORWARD = 3
BACK = 4

BREAKING_FACTOR = 0.1

STARTING_ROTATION_SPEED = 28

CHANGE_TIMEOUT = 10
MIN_ACCEL = 1.5

atStart = True
wheelPosition = STRAIGHT

currentSpeed = 0

gyroReadOut = 0
previousGyroRead = 0
targetGyro = 0

accelXReadOut = 0
accelYReadOut = 0
accelDeltaTime = 0
targetDistance = 0
accelDistance = 0

calibrateAccel = False
minAccel = 0
maxAccel = 0
midAccel = 0
midAccelCount = 0

previousControlTime = 0

continuousTimeout = 50
needToChange = 0

_needGyro = False
_needAccel = False

originalDirection = None
leftMovingSpeed = -2
rightMovingSpeed = 2
lastRotationalSpeed = 0

forwardMovingSpeed = 2
backMovingSpeed = -2

startSpeed = 0

startedCommandTime = 0
startedMovingTime = 0


# sine = [0, 1, 0, -1, 0, -1]

sine = [0, 1, 0, -1]

# sine = [0, 1, 2, 1, 0, -1, -2, -3, -4, -4 -4, -4, -4, -4, -4, -4, -3, -2, -1]

# sine = [0, 0, 0, 0, 1, 1, 2, 1, 1, 0, 0, 0, 0, -1, -1, -2, -1, -1]

sineIndex = 0


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


def log(m, s):
    t = time.time() - startedCommandTime
    print("{0!s:>10} {1:<20} {2}".format(round(t, 3), m, s))


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
    global wheelPosition

    wheelDeg("fl", 0)
    wheelDeg("fr", 0)
    wheelDeg("bl", 0)
    wheelDeg("br", 0)

    wheelPosition = STRAIGHT


def slantWheels():
    global wheelPosition

    wheelDeg("fl", 60.0)
    wheelDeg("fr", -60.0)
    wheelDeg("bl", -60.0)
    wheelDeg("br", 60.0)

    wheelPosition = SLANT


def sidewaysWheels():
    global wheelPosition

    wheelDeg("fl", 90.0)
    wheelDeg("fr", -90.0)
    wheelDeg("bl", -90.0)
    wheelDeg("br", 90.0)
    if wheelPosition != SIDEWAYS:
        time.sleep(DELAY)
        wheelPosition = SIDEWAYS


def setRotationSpeed(speed):
    wheelSpeed("fl", speed)
    wheelSpeed("fr", -speed)
    wheelSpeed("bl", speed)
    wheelSpeed("br", -speed)


def setForwardSpeed(speed):
    wheelSpeed("fl", speed)
    wheelSpeed("fr", speed)
    wheelSpeed("bl", speed)
    wheelSpeed("br", speed)


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

    def sineSpeed(speed):
        global sineIndex

        setRotationSpeed(speed + sine[sineIndex])
        sineIndex += 1
        if sineIndex >= len(sine):
            sineIndex = 0

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

    def startUp():
        setCurrentSpeed(currentSpeed)
        timeout(10, waitToStartMoving)
        log("startUp", "speed=" + str(currentSpeed))

    def startAgain():
        global gyroReadOut, targetGyro
        targetGyro -= gyroReadOut
        log("startAgain", "speed=" + str(currentSpeed) + " adjusted target to " + str(targetGyro))
        gyroReadOut = 0
        nextState(waitToStartMoving)

    def waitToStartMoving():
        global currentSpeed, leftMovingSpeed, rightMovingSpeed, startSpeed, _timeout
        sineSpeed(currentSpeed)

        if abs(gyroReadOut) < 1:
            log("waitToStartMoving", "increasing speed to " + str(currentSpeed) + ", gyro " + str(gyroReadOut))
            increaseSpeed()
            _timeout = 20
            nextState(waitToStartMovingNoIncrease)
        elif abs(gyroReadOut) > 2.0:
            log("waitToStartMoving", "stared too fast " + str(currentSpeed) + ", gyro " + str(gyroReadOut))
            if originalDirection == LEFT:
                setCurrentSpeed(int(currentSpeed * 0.5))
            else:
                setCurrentSpeed(int(currentSpeed * 0.5))
            timeout(25, startAgain)
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
        sineSpeed(currentSpeed)

        if abs(gyroReadOut) < 1:
            if _timeout > 0:
                _timeout -= 1
            else:
                nextState(waitToStartMoving)
        elif abs(gyroReadOut) > 2.0:
            log("waitToStartMovingNI", "stared too fast " + str(currentSpeed) + ", gyro " + str(gyroReadOut))
            if originalDirection == LEFT:
                setCurrentSpeed(currentSpeed + 10)
            else:
                setCurrentSpeed(currentSpeed - 10)
            timeout(25, startAgain)
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
        if originalDirection == RIGHT and targetGyro < gyroReadOut + rotational_speed * 3:
            log("turnControl", "getting close gyro + " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target")
            setCurrentSpeed(0)
            timeout(5, startBreaking)
        elif originalDirection == LEFT and targetGyro > gyroReadOut + rotational_speed * 3:
            log("turnControl", "getting close gyro - " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target")
            setCurrentSpeed(0)
            timeout(5, startBreaking)
        elif abs(rotational_speed) < 0.5:
            log("turnControl", "increasing speed " + str(currentSpeed) + " @ " + str(rotational_speed) + " gyro " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target")
            increaseSpeed()
            _timeout = 10
            nextState(turnControlNoIncrease)
        elif abs(rotational_speed) > 1.5 and abs(currentSpeed - startSpeed) > 1:
            log("turnControl", "decreasing speed " + str(currentSpeed) + " @ " + str(rotational_speed) + " gyro " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target" + ", threshold " + str(abs(currentSpeed - startSpeed)))
            decreaseSpeed()
            _timeout = 10
            nextState(turnControlNoIncrease)
        else:
            log("turnControl", " coasting @ " + str(rotational_speed) + " gyro " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target")

    def turnControlNoIncrease():
        global _timeout

        rotational_speed = gyroReadOut - previousGyroRead
        if originalDirection == RIGHT and targetGyro < gyroReadOut + rotational_speed * 3:
            log("turnControlNI", "getting close gyro + " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target")
            setCurrentSpeed(0)
            timeout(5, startBreaking)
        elif originalDirection == LEFT and targetGyro > gyroReadOut + rotational_speed * 3:
            log("turnControlNI", "getting close gyro - " + str(gyroReadOut) + " <=> " + str(targetGyro) + " target")
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
        processCommand("stop", "stop")
        dontNeedGyro()
        pyroslib.publish(TOPIC + "/feedback", "done")

    targetGyro = int(currentCommand["args"])
    if targetGyro < gyroReadOut:
        originalDirection = LEFT
        currentSpeed = leftMovingSpeed + 2
        startSpeed = currentSpeed
    else:
        originalDirection = RIGHT
        currentSpeed = rightMovingSpeed - 2
        startSpeed = currentSpeed

    needGyro()

    if wheelPosition != SLANT:
        slantWheels()
        timeout(50, startUp)
    else:
        nextState(startUp)


def driveStraightBack():
    targetAccel = int(currentCommand["args"])
    currentCommand["args"] = str(-targetAccel)
    driveStraight()


def driveStraight():
    global accelYReadOut, targetDistance, currentSpeed, forwardMovingSpeed, backMovingSpeed
    global startedCommandTime, lastRotationalSpeed
    global originalDirection

    startedCommandTime = time.time()
    log("main", "Started moving")
    accelYReadOut = 0

    def setCurrentSpeed(speed):
        global currentSpeed
        setForwardSpeed(speed)
        currentSpeed = speed

    def sineSpeed(speed):
        global sineIndex

        setForwardSpeed(speed + sine[sineIndex])
        sineIndex += 1
        if sineIndex >= len(sine):
            sineIndex = 0

    def increaseSpeed():
        if originalDirection == BACK:
            setCurrentSpeed(currentSpeed - 1)
        else:
            setCurrentSpeed(currentSpeed + 1)

    def decreaseSpeed():
        global currentSpeed
        if originalDirection == BACK:
            setCurrentSpeed(currentSpeed + 1)
        else:
            setCurrentSpeed(currentSpeed - 1)

    def startUp():
        global _timeout, midAccelCount, minAccel, maxAccel, midAccel, calibrateAccel
        log("startUp", "calibrating accel")
        midAccelCount = 0
        minAccel = 0
        maxAccel = 0
        midAccel = 0
        calibrateAccel = True
        timeout(50, fetchCalibrated)

    def fetchCalibrated():
        global calibrateAccel, accelYReadOut, midAccel, accelDistance, _timeout
        calibrateAccel = False
        accelDistance = 0
        accelYReadOut = 0
        midAccel /= midAccelCount
        log("fetchCalibrated", "got accel offset " + str(midAccel) + ", speed " + str(currentSpeed))
        setCurrentSpeed(currentSpeed)
        _timeout = 10
        nextState(initialTimeout)
        # timeout(10, waitToStartMoving)

    def initialTimeout():
        global _timeout
        if _timeout > 0:
            _timeout -= 1
        else:
            nextState(waitToStartMoving)
        sineSpeed(currentSpeed)

    def waitToStartMoving():
        global currentSpeed, backMovingSpeed, forwardMovingSpeed, _timeout, startedMovingTime

        if abs(accelYReadOut) < MIN_ACCEL:
            log("waitToStartMoving", "increasing speed to " + str(currentSpeed) + ", accel " + str(accelYReadOut))
            increaseSpeed()
            _timeout = 25
            nextState(waitToStartMovingNoIncrease)
        # elif abs(accelYReadOut) > 2.0:
        #     log("waitToStartMoving", "stared too fast " + str(currentSpeed) + ", gyro " + str(gyroReadOut))
        #     if originalDirection == LEFT:
        #         setCurrentSpeed(currentSpeed + 10)
        #     else:
        #         setCurrentSpeed(currentSpeed - 10)
        #     timeout(25, startAgain)
        else:
            if originalDirection == BACK:
                backMovingSpeed = currentSpeed
                log("waitToStartMoving", "recorded backMovingSpeed " + str(backMovingSpeed) + ", accel " + str(accelYReadOut))
            else:
                forwardMovingSpeed = currentSpeed
                log("waitToStartMoving", "recorded forwardMovingSpeed " + str(forwardMovingSpeed) + ", accel " + str(accelYReadOut))
            nextState(driveControl)
            startedMovingTime = time.time()

    def waitToStartMovingNoIncrease():
        global currentSpeed, backMovingSpeed, forwardMovingSpeed, _timeout, startedMovingTime
        sineSpeed(currentSpeed)

        if abs(accelYReadOut) < MIN_ACCEL:
            if _timeout > 0:
                _timeout -= 1
            else:
                nextState(waitToStartMoving)
        # elif abs(gyroReadOut) > 2.0:
        #     log("waitToStartMovingNI", "stared too fast " + str(currentSpeed) + ", gyro " + str(gyroReadOut))
        #     if originalDirection == LEFT:
        #         setCurrentSpeed(currentSpeed + 10)
        #     else:
        #         setCurrentSpeed(currentSpeed - 10)
        #     timeout(25, startAgain)
        else:
            if originalDirection == BACK:
                backMovingSpeed = currentSpeed
                log("waitToStartMovingNI", "recorded leftMovingSpeed " + str(backMovingSpeed) + " @ " + str(accelYReadOut))
            else:
                forwardMovingSpeed = currentSpeed
                log("waitToStartMovingNI", "recorded rightMovingSpeed " + str(forwardMovingSpeed) + " @ " + str(accelYReadOut))
            nextState(driveControl)
            startedMovingTime = time.time()

    def driveControl():
        global _timeout

        sineSpeed(currentSpeed)

        now = time.time()
        deltaTime = now - startedMovingTime
        distance = deltaTime * abs(currentSpeed * 20) * WHEEL_CIRCUMFERENCE / 60

        if distance >= abs(targetDistance) or abs(accelDistance) >= abs(targetDistance):
            log("driveControl", " reached distance @ " + str(currentSpeed) + " distance " + str(distance) + " <=> " + str(targetDistance) + " target")
            setCurrentSpeed(0)
            timeout(5, startBreaking)
        else:
            log("driveControl", " coasting @ " + str(currentSpeed) + " distance " + str(distance) + " <=> " + str(targetDistance) + " target")

    def startBreaking():
        log("startBreaking", "")
        if originalDirection == BACK:
            setCurrentSpeed(forwardMovingSpeed * BREAKING_FACTOR)
        else:
            setCurrentSpeed(backMovingSpeed * BREAKING_FACTOR)
        timeout(10, stopBreaking)

    def stopBreaking():
        log("stopBreaking", "end moving.")
        setCurrentSpeed(0)
        processCommand("stop", "stop")
        dontNeedGyro()
        pyroslib.publish(TOPIC + "/feedback", "done")

    targetDistance = int(currentCommand["args"])
    if targetDistance < 0:
        originalDirection = BACK
        currentSpeed = backMovingSpeed + 2
    else:
        originalDirection = FORWARD
        currentSpeed = forwardMovingSpeed - 2

    needAccel()

    if wheelPosition != STRAIGHT:
        straightenWheels()
        timeout(50, startUp)
    else:
        nextState(startUp)


def driveStraightContBack():
    targetAccel = int(currentCommand["args"])
    currentCommand["args"] = str(-targetAccel)
    driveStraightCont()


def driveStraightCont():
    global currentSpeed

    currentSpeed = int(currentCommand["args"])

    def sineSpeed(speed):
        global sineIndex

        setForwardSpeed(speed + sine[sineIndex])
        sineIndex += 1
        if sineIndex >= len(sine):
            sineIndex = 0

    def driveControl():
        global _timeout

        sineSpeed(currentSpeed)

    nextState(driveControl)


def stopAll():
    wheelSpeed("fl", 0)
    wheelSpeed("fr", 0)
    wheelSpeed("bl", 0)
    wheelSpeed("br", 0)
    log("stopAll", "Stopping all wheels!")
    pyroslib.publish(TOPIC + "/feedback", "done")


def nothing():
    return


commands = {
    "stop": {
        "start": stopAll,
        "do": doNothing
    },
    "rotate": {
        "start": turnOnSpot,
        "do": processCurrentState
    },
    "forward": {
        "start": driveStraight,
        "do": processCurrentState
    },
    "back": {
        "start": driveStraightBack,
        "do": processCurrentState
    },
    "forwardcont": {
        "start": driveStraightCont,
        "do": processCurrentState
    },
    "backcont": {
        "start": driveStraightContBack,
        "do": processCurrentState
    }
}

currentCommand = {}


def newCommandMsg(topic, message, groups):
    global currentCommand

    command = topic.split("/")[1]
    print("Received new command " + command)
    processCommand(command, message)


def processCommand(command, args):
    global currentCommand

    if "stop" in currentCommand:
        currentCommand["stop"]()

    if command in commands:
        currentCommand = commands[command]
        currentCommand["args"] = args

        if "start" in currentCommand:
            currentCommand["start"]()
    else:
        print("Received unknown command " + command)


def handleGyro(topic, message, groups):
    global gyroReadOut, previousGyroRead
    previousGyroRead = gyroReadOut
    data = message.split(",")
    gyroReadOut += float(data[2])


def handleAccel(topic, message, groups):
    global accelXReadOut, accelYReadOut, accelDeltaTime, minAccel, maxAccel, midAccel, midAccelCount, accelDistance

    data = message.split(",")
    # print("Received data " + str(data))
    accelX = float(data[0])
    accelY = -float(data[1])
    accelDeltaTime = float(data[3])
    if calibrateAccel:
        if accelY < minAccel:
            minAccel = accelY
        if accelY > maxAccel:
            maxAccel = accelY
        midAccel += accelY
        midAccelCount += 1
        # log("Accel", "y:{0:>10} m:{1:>10} c:{2:>10}".format(round(accelY, 3), round(midAccel, 3), midAccelCount))
    else:
        # if minAccel <= accelY <= maxAccel:
        #     acceYAdj = 0
        # else:
        #     acceYAdj = (accelY - midAccel)
        acceYAdj = (accelY - midAccel)
        accelXReadOut += accelX
        accelYReadOut += acceYAdj
        accelYReadOut *= 0.97
        accelDistance += accelYReadOut * accelDeltaTime
        # log("Accel", "y:{0:>10} a:{1:>10} n:{2:>10}".format(round(accelY, 3), round(acceYAdj, 3), round(accelYReadOut, 3)))


def loop():
    global continuousTimeout, atStart

    if atStart:
        straightenWheels()
        atStart = False

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
        print("Starting fine drive service...")

        for c in commands:
            pyroslib.subscribe(TOPIC + "/" + c, newCommandMsg)
        pyroslib.subscribe("sensor/gyro", handleGyro)
        pyroslib.subscribe("sensor/accel", handleAccel)
        pyroslib.init(NAME.replace(" ", "-"))

        print("Started fine drive service.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
