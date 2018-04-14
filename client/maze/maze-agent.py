
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import math
import time
import traceback

import pyroslib

DEBUG_LEVEL_OFF = 0
DEBUG_LEVEL_INFO = 1
DEBUG_LEVEL_DEBUG = 2
DEBUG_LEVEL_ALL = 3
DEBUG_LEVEL = DEBUG_LEVEL_ALL


MAX_TIMEOUT = 5

MAX_WALL_END_WAIT_TIMEOUT = 2
MAX_ROTATE_DISTANCE = 500
MIN_ROTATE_DISTANCE = 0
MIN_DISTANCE = 100

SQRT2 = math.sqrt(2)

INITIAL_SPEED = 40
INITIAL_GAIN = 1.7


gain = INITIAL_GAIN
speed = INITIAL_SPEED

driveAngle = 0

run = True
received = True
turned = False
justScanWidth = False

leftDistance = 0
rightDistance = 0
corridorWidth = 0
idealDistance = 0

lastWallDistance = 0

scanTime = 0
SCAN_TIME = 1.2

continuousCounter = 0
wallEndWaitTimeout = 0

DISTANCE_AVG_TIME = 0.5

distances = {}

distanceTimestamp = 0
distanceDeg1 = -1
distanceDeg2 = -1
distance1 = -1
distance2 = -1
avgDistance1 = -1
avgDistance2 = -1
deltaDistance1 = -1
deltaDistance2 = -1

historyDistancesDeg1 = -1
historyDistancesDeg2 = -1
historyDistances1 = []
historyDistanceTimes1 = []
historyDistances2 = []
historyDistanceTimes2 = []

lastDistanceReceivedTime = 0

gyroAngle = 0
gyroDeltaAngle = 0
gyroStartAngle = 0
gyroIntegral = 0
EPSILON_ANGLE = 2

renewContinuous = time.time()
digestTime = time.time()
readingDistanceContinuous = True
readingGyroContinuous = True

KGAIN_INDEX = 0
KpI = 1
KiI = 2
KdI = 3

ERROR_INDEX = 0
PREVIOUS_ERROR_INDEX = 1
INTEGRAL_INDEX = 2
DERIVATIVE_INDEX = 3
DELTA_TIME_INDEX = 4

MAX_FORWARD_DELTA = 50
MINIMUM_FORWARD_SPEED = 20
MAX_ANGLE = 45

ACTION_NONE = 0
ACTION_TURN = 1
ACTION_DRIVE = 2

lastActionTime = 0
sideAngleAccum = 0
lastAngle = 0
lastForwardDelta = 0
accumSideDelta = 0

sideGains = [1.1, 0.8, 0.3, 0.05]
sidePid = [0, 0, 0, 0, 0]

gyroGains = [1.5, 0.8, 0.8, 0.2]
gyroPid = [0, 0, 0, 0, 0]


def doNothing():
    pass


doDistance = doNothing
doGyro = doNothing
algorithm = doNothing
algorithmIndex = 0
algorithmsList = []


def log(level, what):
    if level <= DEBUG_LEVEL:
        print(what)


def logArgs(*msg):
    tnow = time.time()
    dt = str((tnow - distanceTimestamp) * 1000) + "ms"

    logMsg = formatArgR("", int(tnow * 1000) % 100000, 7) + " " + " ".join(msg)
    log(DEBUG_LEVEL_DEBUG, logMsg)


def formatArgL(label, value, fieldSize):
    if len(label) > 0:
        return label + ":" + str(value).ljust(fieldSize)
    else:
        return str(value).ljust(fieldSize)


def formatArgR(label, value, fieldSize):
    if len(label) > 0:
        return label + ":" + str(value).rjust(fieldSize)
    else:
        return str(value).rjust(fieldSize)


def setAlgorithm(alg):
    global algorithm
    algorithm = alg


def setAlgorithms(*algs):
    global algorithmIndex, algorithmsList

    algorithmIndex = 0
    algorithmsList[:] = []
    for a in algs:
        algorithmsList.append(a)
    setAlgorithm(algorithmsList[0])


def handleDistances(topic, message, groups):
    global historyDistancesDeg1, historyDistancesDeg2, historyDistances1, historyDistances2, historyDistanceTimes1, historyDistanceTimes2
    global distanceDeg1, distanceDeg2, distance1, distance2, avgDistance1, avgDistance2, distanceTimestamp, deltaDistance1, deltaDistance2
    global deltaTime, lastDistanceReceivedTime
    global received

    def addToHistoryWithTime(value, valueTime, history, historyTimes, maxTime):
        history.append(value)
        historyTimes.append(valueTime)

        while len(historyTimes) > 0 and historyTimes[0] < valueTime - maxTime:
            del history[0]
            del historyTimes[0]

        if len(history) > 1:
            return value - history[len(history) - 2], sum(history) / len(history)
        else:
            return 0, 0

    def sanitise(distance):
        # distance -= 100
        if distance < 2:
            distance = 2
        return distance

    def toFloatString(f):
        r = str(round(f, 1))
        if "." not in r:
            return r + ".0"
        return r

    receivedTime = time.time()

    split = message.split(",")
    deg1 = -1
    val1 = -1
    deg2 = -1
    val2 = -1

    i = 0
    for s in split:
        kv = s.split(":")
        if kv[0] == "timestamp":
            distanceTimestamp = float(kv[1])
        else:
            distances[toFloatString(float(kv[0]))] = sanitise(float(kv[1]))

            deg = int(float(kv[0]))
            val = int(float(kv[1]))

            if i == 0:
                deg1 = deg
                val1 = val
            elif i == 1:
                deg2 = deg
                val2 = val

            i += 1

    distanceDeg1 = deg1
    distance1 = val1
    distanceDeg2 = deg2
    distance2 = val2

    if deg1 > deg2:
        tmp = deg2
        deg2 = deg1
        deg1 = tmp

        tmp = distanceDeg2
        distanceDeg2 = distanceDeg1
        distanceDeg1 = tmp

    if historyDistancesDeg1 != deg1 or historyDistancesDeg2 != deg2:
        historyDistances1 = []
        historyDistanceTimes1 = []
        historyDistancesDeg1 = deg1

        historyDistances2 = []
        historyDistanceTimes2 = []
        historyDistancesDeg2 = deg2

    deltaDistance1, avgDistance1 = addToHistoryWithTime(distance1, receivedTime, historyDistances1, historyDistanceTimes1, DISTANCE_AVG_TIME)
    deltaDistance2, avgDistance2 = addToHistoryWithTime(distance2, receivedTime, historyDistances2, historyDistanceTimes2, DISTANCE_AVG_TIME)

    deltaTime = receivedTime - lastDistanceReceivedTime
    lastDistanceReceivedTime = receivedTime

    received = True
    # if nextState is not None:
    #     nextState()

    doDistance()


def handleGyroData(topic, message, groups):
    global gyroAngle, gyroDeltaAngle, gyroDeltaTime, lastGyroReceivedTime

    data = message.split(",")

    gyroChange = float(data[2])

    gyroDeltaAngle = gyroChange

    gyroAngle += gyroChange

    gyroDeltaTime = float(data[3])

    lastGyroReceivedTime = time.time()

    doGyro()


def stop():
    global run, doDistance, doGyro
    doDistance = doNothing
    doGyro = doNothing

    print("Stoping...")
    setAlgorithm(doNothing)
    run = False
    pyroslib.publish("move/stop", "stop")
    print("Stopped.")


def start():
    global run, turned, justScanWidth
    print("Starting...")
    run = True
    turned = False
    justScanWidth = False

    preStartInitiateLeftScan()


def quickstart():
    global run, turned, justScanWidth, scanTime
    print("Quick Starting...")
    run = True
    turned = False
    justScanWidth = False

    scanTime = time.time() + SCAN_TIME
    pyroslib.publish("sensor/distance/read", str(0))
    setAlgorithm(preStart)


def scanWidth():
    global run, turned, justScanWidth
    print("Scanning width...")
    run = True
    turned = False
    justScanWidth = True

    preStartInitiateLeftScan()


def steer(steerDistance, speed):
    pyroslib.publish("move/steer", str(int(steerDistance)) + " " + str(int(speed)))


def drive(angle, speed):
    pyroslib.publish("move/drive", str(int(angle)) + " " + str(int(speed)))


def requestDistanceAtAngle(angle):
    pyroslib.publish("sensor/distance/deg", str(angle))


def normalise(value, maxValue):
    if value > maxValue:
        value = maxValue
    if value < -maxValue:
        value = -maxValue

    return value / maxValue


def sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0


def resetPid(pidValues):
    pidValues[ERROR_INDEX] = 0
    pidValues[PREVIOUS_ERROR_INDEX] = 0
    pidValues[DERIVATIVE_INDEX] = 0
    pidValues[INTEGRAL_INDEX] = 0
    pidValues[DELTA_TIME_INDEX] = 0


def preStartInitiateLeftScan():
    global scanTime
    scanTime = time.time() + SCAN_TIME
    setAlgorithm(preStartLeftScan)
    pyroslib.publish("sensor/distance/read", str(0))


def preStartLeftScan():
    global leftDistance
    if time.time() > scanTime:
        leftDistance = avgDistance2
        log(DEBUG_LEVEL_INFO, "LeftDistance = " + str(leftDistance))
        preStartInitiateRightScan()


def preStartInitiateRightScan():
    global scanTime
    scanTime = time.time() + SCAN_TIME
    setAlgorithm(preStartRightScan)
    pyroslib.publish("sensor/distance/read", str(90))


def preStartRightScan():
    global rightDistance
    if time.time() > scanTime:
        rightDistance = avgDistance1
        log(DEBUG_LEVEL_INFO, "RightDistance = " + str(rightDistance))
        preStartWarmUp()


def preStartWarmUp():
    global corridorWidth, idealDistance, scanTime

    scanTime = time.time() + SCAN_TIME

    if justScanWidth:
        pyroslib.publish("sensor/distance/read", str(0))
        setAlgorithm(doNothing)
    else:
        pyroslib.publish("sensor/distance/read", str(45))
        setAlgorithm(preStart)

    corridorWidth = leftDistance + rightDistance

    idealDistance = (corridorWidth / 2)  # * SQRT2

    log(DEBUG_LEVEL_INFO, "Corridor is " + str(corridorWidth) + "mm wide. Ideal distance=" + str(idealDistance))

    pyroslib.publish("maze/data/corridor", str(corridorWidth))
    pyroslib.publish("maze/data/idealDistance", str(idealDistance))

    pyroslib.publish("sensor/distance/continuous", "start")


def preStartWarmUp():
    global corridorWidth, idealDistance, scanTime

    scanTime = time.time() + SCAN_TIME

    if justScanWidth:
        pyroslib.publish("sensor/distance/read", str(0))
        setAlgorithm(doNothing)
    else:
        pyroslib.publish("sensor/distance/read", str(45))
        setAlgorithm(preStart)

    corridorWidth = leftDistance + rightDistance
    idealDistance = (corridorWidth / 2)  # * SQRT2

    log(DEBUG_LEVEL_INFO, "Corridor is " + str(corridorWidth) + "mm wide. Ideal distance=" + str(idealDistance))

    pyroslib.publish("maze/data/corridor", str(corridorWidth))
    pyroslib.publish("maze/data/idealDistance", str(idealDistance))

    # pyroslib.publish("sensor/distance/continuous", "start")


def preStart():
    if time.time() > scanTime:
        setAlgorithm(doNothing)
        followLeftWall()


# def goForward():
#     global doDistance
#     # doDistance = goForwardDistanceHandler
#     # followLeftWall()


def followSide(forwardDistance, forwardDelta, sideDistance, sideDelta, direction, dt):
    global stopCountdown, lastActionTime, sideAngleAccum, sideAngleAccumCnt, lastAngle
    global forwardIntegral, lastForwardSpeed, lastForwardDelta, accumSideDelta
    global turned

    def log1(*msg):
        logArgs(*((formatArgL("  dt", round(dt, 3), 5),
                   formatArgR("  fd", forwardDistance, 5), formatArgR("  fdd", forwardDelta, 5),
                   formatArgR("  sd", sideDistance, 5), formatArgR("  sdd", sideDelta, 5)) + msg))

    # if stopCountdown > 0:
    #     log1(formatArgR("s", round(0, 1), 4), formatArgR("a", round(0, 1), 3))
    #     drive(0, 0)
    #     stopCountdown -= 1
    #     if stopCountdown == 0:
    #         stop()
    #
    if forwardDistance < corridorWidth * 0.8:
        if turned:
            log1(" LEFT90 ", formatArgR("cw", round(corridorWidth * 0.8, 1), 5))
            turnLeft90()
        else:
            log1(" RIGHT90 ", formatArgR("cw", round(corridorWidth * 0.8, 1), 5))
            turnRight90()
    elif sideDistance > corridorWidth:
        turned = True
        # turnLeft180()

        log1(" T180 ", formatArgR("cw", round(corridorWidth, 1), 5))
        followRightWall()

    else:
        if forwardDistance > 1000:
            forwardDelta = - MAX_FORWARD_DELTA

        if abs(forwardDelta) > MAX_FORWARD_DELTA:
            forwardDelta = sign(forwardDelta) * MAX_FORWARD_DELTA

        if abs(forwardDelta) < 20:
            forwardIntegral += forwardDelta
        else:
            forwardIntegral = 0

        # forwardError = forwardDistance - STOP_DISTANCE
        # forwardSpeed = forwardGains[KGAIN_INDEX] * (forwardError * forwardGains[KpI] + forwardIntegral * forwardGains[KiI] + (forwardDelta / dt) * forwardGains[KdI])
        # forwardSpeed = normalise(forwardSpeed, MAX_FORWARD_SPEED) * MAX_FORWARD_SPEED

        angle = sideGains[KGAIN_INDEX] * ((sideDistance - idealDistance) * sideGains[KpI] + (sideDelta / dt) * sideGains[KdI])
        angle = - direction * normalise(angle, MAX_ANGLE) * MAX_ANGLE

        lastActionTime -= deltaTime

        if sideAngleAccumCnt > 0:
            saa = sideAngleAccum / sideAngleAccumCnt
        else:
            saa = sideAngleAccum

        if lastActionTime < 0:
            if abs(saa) > 12.5:
                nextAction = ACTION_TURN
            else:
                nextAction = ACTION_DRIVE

            lastActionTime = 0.5
            sideAngleAccum = 0
            sideAngleAccumCnt = 0
        else:
            nextAction = ACTION_DRIVE
            sideAngleAccum += angle
            sideAngleAccumCnt += 1

        angle = (sideDistance - idealDistance) * sideGains[KpI] + (sideDelta / dt) * sideGains[KdI]
        angle = - direction * normalise(angle, MAX_ANGLE) * MAX_ANGLE
        lastAngle = angle
        accumSideDelta += sideDelta

        if nextAction == ACTION_DRIVE:
            log1(" DRIV ", formatArgR("i", round(forwardIntegral, 1), 6), formatArgR("s", round(speed, 1), 6), formatArgR("a", round(angle, 1), 5), formatArgR("saa", round(saa), 6))
            drive(angle, speed)
        else:
            turnDirection = -1
            if accumSideDelta < 0:
                turnDirection = 1

            if forwardDelta == 0:
                forwardDelta = -MAX_FORWARD_DELTA  # moving forward

            forwardDelta = (lastForwardDelta + forwardDelta) / 2

            angleR = saa / 180

            fudgeFactor = 3

            steerDistance = fudgeFactor * turnDirection * forwardDelta / abs(angleR)

            log1(" TURN ", formatArgR("s", round(speed, 1), 6), formatArgR("sd", round(steerDistance, 1), 5), formatArgR("saa", round(saa), 6), formatArgR("asd", round(accumSideDelta), 6), formatArgR("fwd", round(forwardDelta), 6))
            steer(steerDistance, speed)

            accumSideDelta = 0

        # lastForwardSpeed = forwardSpeed
        lastForwardDelta = forwardDelta
        lastSideDelta = sideDelta


def setupFollowSide():
    global stopCountdown, sideAngleAccum, sideAngleAccumCnt, lastActionTime, forwardIntegral, lastForwardSpeed, lastForwardDelta, accumSideDelta

    setAlgorithm(doNothing)
    # resetPid(forwardPid)
    resetPid(sidePid)
    forwardIntegral = 0
    stopCountdown = 0
    sideAngleAccum = 0
    sideAngleAccumCnt = 0
    lastActionTime = 0.5
    lastForwardSpeed = 0
    lastForwardDelta = 0
    accumSideDelta = 0


def followLeftWall():
    global doDistance, doGyro

    def followSideHandleDistance():
        followSide(distance1, deltaDistance1, distance2, deltaDistance2, 1, deltaTime)

    log(DEBUG_LEVEL_DEBUG, "Following left wall")
    requestDistanceAtAngle("0")
    setupFollowSide()
    doDistance = followSideHandleDistance
    doGyro = doNothing


# follow right wall
def followRightWall():
    global doDistance, doGyro

    def followSideHandleDistance():
        followSide(distance2, deltaDistance2, distance1, deltaDistance1, -1, deltaTime)

    log(DEBUG_LEVEL_DEBUG, "Following right wall")
    setupFollowSide()
    requestDistanceAtAngle("90")
    doDistance = followSideHandleDistance
    doGyro = doNothing


def turnForAngle(angle):
    global doDistance

    def handleDistance():
        global doDistance

        if turned:
            forwardDistance = distance2
            forwardDelta = deltaDistance2
            sideDistance = distance1
            sideDelta = deltaDistance1
        else:
            forwardDistance = distance1
            forwardDelta = deltaDistance1
            sideDistance = distance2
            sideDelta = deltaDistance2

        logArgs(*((formatArgL("  dt", round(deltaTime, 3), 5),
                   formatArgR("  fd", forwardDistance, 5), formatArgR("  fdd", forwardDelta, 5),
                   formatArgR("  sd", sideDistance, 5), formatArgR("  sdd", sideDelta, 5))))

        if forwardDistance > corridorWidth * 2:
            if turned:
                log(DEBUG_LEVEL_INFO, "Go to following right wall after turn")
                followRightWall()
            else:
                log(DEBUG_LEVEL_INFO, "Go to following left wall")
                followLeftWall()
        else:
            if angle < 0:
                steer(-idealDistance, speed)
            else:
                steer(idealDistance, speed)

    doDistance = handleDistance


def turnForAngleX(angle):
    global gyroAngle, gyroStartAngle, doGyro, gyroIntegral

    def log1(*msg):
        logArgs(*((formatArgL("  dt", round(gyroDeltaTime, 3), 5),
                formatArgR("  ga", round(gyroAngle, 3), 5), formatArgR("  gda", round(gyroDeltaAngle, 3), 5)) + msg))

    def handleGyroRorate():
        global gyroAngle, gyroStartAngle, stopCountdown, gyroIntegral

        gyroError = gyroAngle - angle
        if (angle < 0 and gyroAngle < angle) or (angle >= 0 and gyroAngle > angle):
            gyroError = 0

        gyroIntegral = 0

        control = - gyroGains[KGAIN_INDEX] * (gyroError * gyroGains[KpI] + gyroIntegral * gyroDeltaTime * gyroGains[KiI] + (gyroDeltaAngle / gyroDeltaTime) * gyroGains[KdI])
        control = normalise(control, 1)

        if sign(control) != sign(angle):
            if turned:
                log(DEBUG_LEVEL_INFO, "Go to following right wall after turn")
                followRightWall()
            else:
                log(DEBUG_LEVEL_INFO, "Go to following left wall")
                followLeftWall()
        else:
            # gyroError = gyroAngle - angle
            #
            # if abs(gyroDeltaAngle) < 2.5:
            #     gyroIntegral += gyroError
            #     if gyroIntegral > MAX_ROTATE_SPEED / (gyroGains[KiI] * gyroDeltaTime):
            #         gyroIntegral = MAX_ROTATE_SPEED / (gyroGains[KiI] * gyroDeltaTime)
            # else:
            #     gyroIntegral = 0
            #
            # speed = - gyroGains[KGAIN_INDEX] * (gyroError * gyroGains[KpI] + gyroIntegral * gyroDeltaTime * gyroGains[KiI] + (gyroDeltaAngle / gyroDeltaTime) * gyroGains[KdI])
            # speed = normalise(speed, MAX_ROTATE_SPEED) * MAX_ROTATE_SPEED

            log1(formatArgR("c", round(control, 1), 5), formatArgR("i", round(gyroIntegral, 1), 5), formatArgR("s", round(speed, 1), 5))
            if angle > 0:
                steer(idealDistance, speed)
            else:
                steer(-idealDistance, speed)

    log(DEBUG_LEVEL_DEBUG, "Rotating for " + str(angle))
    gyroAngle = 0
    gyroIntegral = 0
    gyroStartAngle = 0
    setAlgorithm(doNothing)
    resetPid(gyroPid)
    doDistance = doNothing
    doGyro = handleGyroRorate


def turnRight90():
    turnForAngle(90)


def turnLeft90():
    turnForAngle(-90)


def turnLeft180():
    turnForAngle(-180)


def connected():
    stop()


def handleMazeSpeed(topic, message, groups):
    global speed

    speed = int(message)
    log(DEBUG_LEVEL_INFO, "  Got turning speed of " + str(speed))


def handleMazeGain(topic, message, groups):
    global gain

    gain = float(message)
    log(DEBUG_LEVEL_INFO, "  Got turning gain of " + str(gain))


def handleMazeCommand(topic, message, groups):
    if message == "start":
        start()
    elif message == "quickstart":
        quickstart()
    elif message == "stop":
        stop()
    elif message == "scan":
        scanWidth()


def loop():
    global renewContinuous, digestTime

    thisTime = time.time()

    if thisTime > renewContinuous:
        renewContinuous = time.time() + 1
        if readingDistanceContinuous:
            pyroslib.publish("sensor/distance/continuous", "continue")
        if readingGyroContinuous:
            pyroslib.publish("sensor/gyro/continuous", "continue")

    if algorithm is not None:
        algorithm()

    if thisTime > digestTime:
        pyroslib.publish("maze/data/distances", str(distanceDeg1) + ":" + str(distance1) + ";" + str(avgDistance1) + "," + str(distanceDeg2) + ":" + str(distance2) + ";" + str(avgDistance2))
        pyroslib.publish("maze/data/gyro", str(gyroAngle))
        digestTime = thisTime + 0.1


if __name__ == "__main__":
    try:
        print("Starting maze agent...")

        pyroslib.subscribe("sensor/distance", handleDistances)
        pyroslib.subscribe("sensor/gyro", handleGyroData)

        pyroslib.subscribe("maze/command", handleMazeCommand)
        pyroslib.subscribe("maze/speed", handleMazeSpeed)
        pyroslib.subscribe("maze/gain", handleMazeGain)

        pyroslib.init("maze-agent", unique=True)

        print("Started maze agent.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
