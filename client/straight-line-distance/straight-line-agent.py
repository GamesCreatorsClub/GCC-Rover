
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import math
import time
import traceback
import pyroslib

DEBUG = True

MAX_TIMEOUT = 5

run = False

leftDeg = 0
rightDeg = 0

proportionalError = 0
integratedError = 0
derivativeError = 0

calibrationStartedTime = 0

digestTime = 0
lastDriverTime = 0
lastTimeGyroRead = 0
thisTimeGyroRead = 0
renewContinuous = 0

leftSideSpeed = 75
rightSideSpeed = 75

driving = False
calibrating = True
driveAfterCalibrate = False

MAX_SPEED = 150
SPEED_RAMPUP = 20
SPEED_RAMPUP_MAX = 300
STEER_GAIN = 0.5
STEER_MAX_CONTROL = 30
# INTEGRAL_FADE_OUT = 0.95
INTEGRAL_FADE_OUT = 1

# P_GAIN = 0.9 and I_GAIN = 0.1
# P_GAIN = 0.7, I_GAIN = 0.3, GAIN = 2

P_GAIN = 0.70
I_GAIN = 0.25
D_GAIN = 0.06

steerGain = STEER_GAIN
pGain = P_GAIN
iGain = I_GAIN
dGain = D_GAIN
integralFadeOut = INTEGRAL_FADE_OUT
steerMaxControl = STEER_MAX_CONTROL


drivingWithGyro = False
drivingWithDistance = True

DISTANCE_AVG_TIME = 0.5

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
lastDeltaDistance = 0


def sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0


def connected():
    pyroslib.publish("sensor/gyro/continuous", "calibrate,50")


def handleStraight(topic, message, groups):
    global integratedError, driving, calibrating

    if message == "forward":
        startDriving()
    elif message == "stop":
        stopDriving()


def wheelDeg(wheelName, angle):
    topic = "wheel/" + wheelName + "/deg"
    pyroslib.publish(topic, str(angle))


wheelDeg("fl", 0)
wheelDeg("fr", 0)
wheelDeg("bl", 0)
wheelDeg("br", 0)


def startDriving():
    global driveAfterCalibrate, driving, calibrating, leftSideSpeed, rightSideSpeed, leftDeg, rightDeg, integratedError, derivativeError
    global lastDeltaDistance

    print("DRIVE DIRVE DRIVE!")
    calibrating = False
    driving = True
    # leftSideSpeed = 75
    # rightSideSpeed = 75
    leftSideSpeed = 0
    rightSideSpeed = 0
    integratedError = 0
    derivativeError = 0
    lastDeltaDistance = 0
    pyroslib.publish("sensor/gyro/continuous", "start")


def stopDriving():
    global leftSideSpeed, rightSideSpeed, driving, calibrating
    print("STOP STOP STOP!")
    leftSideSpeed = 0
    rightSideSpeed = 0

    driving = False
    calibrating = True
    pyroslib.publish("sensor/gyro/continuous", "calibrate,50")


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


def handleDistances(topic, message, groups):
    global historyDistancesDeg1, historyDistancesDeg2, historyDistances1, historyDistances2, historyDistanceTimes1, historyDistanceTimes2
    global distanceDeg1, distanceDeg2, distance1, distance2, avgDistance1, avgDistance2, distanceTimestamp, deltaDistance1, deltaDistance2
    global deltaTime, lastDistanceReceivedTime

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
    doDriving()


def handleGyro(topic, message, groups):
    global driving, calibrating
    global proportionalError, integratedError, derivativeError
    global leftDeg, rightDeg
    global rightSideSpeed, leftSideSpeed
    global calibrationStartedTime

    previousError = 0
    control = 0

    data = message.split(",")
    z = float(data[2])
    dt = float(data[3])

    thisTimeGyroRead2 = time.time()
    if drivingWithGyro:
        if driving:

            integratedError *= integralFadeOut

            proportionalError = z
            integratedError += proportionalError  # * dt

            if dt == 0:
                derivativeError = 0
            else:
                derivativeError = (proportionalError - previousError)  # / dt

            previousError = proportionalError

            control = pGain * proportionalError + iGain * integratedError + dGain * derivativeError

            controlSteer = control * steerGain
            if controlSteer > steerMaxControl:
                controlSteer = steerMaxControl
            elif controlSteer < -steerMaxControl:
                controlSteer = -steerMaxControl

            leftDeg = int(-controlSteer)
            rightDeg = int(-controlSteer)

            if leftSideSpeed < 50:
                leftSideSpeed += 25
                rightSideSpeed += 25
            elif leftSideSpeed < 300:
                leftSideSpeed += 50
                rightSideSpeed += 50
            else:
                leftSideSpeed = 300
                rightSideSpeed = 300

        elif calibrating:

            leftDeg = 0
            rightDeg = 0

            rightSideSpeed = 0
            leftSideSpeed = 0

        else:
            leftDeg = 0
            rightDeg = 0

            proportionalError = 0
            integratedError = 0
            derivativeError = 0

            previousError = 0
            control = 0

            rightSideSpeed = 0
            leftSideSpeed = 0

        if driving:
            mode = "Driving:    "
            if DEBUG:
                print(mode + " g:{0:>8} d:{1:>8} c:{2:>8} p:{3:>8} i:{4:>8} d:{5:>8} 7:{6:>8}".format(
                    str(round(z, 3)),
                    str(round(leftDeg, 1)),
                    str(round(control, 3)),
                    str(round(proportionalError, 3)),
                    str(round(integratedError, 3)),
                    str(round(derivativeError, 3)),
                    str(round(dt, 3))))
        elif calibrating:
            mode = "Calibrating:"
        else:
            mode = "Idle:       "

        # if DEBUG:
        #     print(mode + " g:{0:>8} d:{1:>8} c:{2:>8} p:{3:>8} i:{4:>8} d:{5:>8} 7:{6:>8}".format(
        #           str(round(z, 3)),
        #           str(round(leftDeg, 1)),
        #           str(round(control, 3)),
        #           str(round(proportionalError, 3)),
        #           str(round(integratedError, 3)),
        #           str(round(derivativeError, 3)),
        #           str(round(dt, 3))))


def handleSteerGain(topic, message, groups):
    global steerGain

    steerGain = float(message)


def handlePGain(topic, message, groups):
    global pGain

    pGain = float(message)


def handleIGain(topic, message, groups):
    global iGain

    iGain = float(message)


def handleDGain(topic, message, groups):
    global dGain

    dGain = float(message)


def requestDistanceAtAngle(angle):
    pyroslib.publish("sensor/distance/deg", str(angle))


def doDriving():
    global leftSideSpeed, rightSideSpeed, leftDeg, rightDeg, leftSideSpeed, rightSideSpeed, lastDeltaDistance

    error = distance2 - distance1
    if abs(error) < 1:
        deltaDistance = 0
    else:
        deltaDistance = math.log(abs(error)) * sign(error)

    deltaDeltaDistance = (lastDeltaDistance - deltaDistance)

    lastDeltaDistance = deltaDeltaDistance

    control = pGain * deltaDistance + dGain * deltaDeltaDistance

    if drivingWithDistance:
        if driving:
            controlSteer = deltaDistance * steerGain
            if controlSteer > steerMaxControl:
                controlSteer = steerMaxControl
            elif controlSteer < -steerMaxControl:
                controlSteer = -steerMaxControl

            leftDeg = int(-controlSteer)
            rightDeg = int(-controlSteer)

            if leftSideSpeed < SPEED_RAMPUP_MAX:
                leftSideSpeed += SPEED_RAMPUP
                rightSideSpeed += SPEED_RAMPUP
            elif leftSideSpeed < MAX_SPEED:
                leftSideSpeed += SPEED_RAMPUP * 2
                rightSideSpeed += SPEED_RAMPUP * 2
            else:
                leftSideSpeed = MAX_SPEED
                rightSideSpeed = MAX_SPEED

            if leftSideSpeed > MAX_SPEED:
                leftSideSpeed = MAX_SPEED
            if rightSideSpeed > MAX_SPEED:
                rightSideSpeed = MAX_SPEED

        else:
            leftDeg = 0
            rightDeg = 0

            rightSideSpeed = 0
            leftSideSpeed = 0

        if driving:
            mode = "Driving:    "
            if DEBUG:
                print(mode + " d1:{0:>8} d2:{1:>8} dd:{2:>8} ddd:{3:>8} c:{4:>8} a:{5:>8}".format(
                    str(round(distance1, 1)),
                    str(round(distance2, 1)),
                    str(round(deltaDistance, 1)),
                    str(round(deltaDeltaDistance, 1)),
                    str(round(control, 3)),
                    str(round(leftDeg, 3))))
        elif calibrating:
            mode = "Calibrating:"
        else:
            mode = "Idle:       "



def loop():
    global renewContinuous, lastDriverTime, digestTime

    now = time.time()

    if now > renewContinuous:
        renewContinuous = time.time() + 1

        if calibrating:
            pyroslib.publish("sensor/gyro/continuous", "calibrate,50")
        else:
            pyroslib.publish("sensor/gyro/continuous", "start")

        pyroslib.publish("sensor/distance/continuous", "continue")

    if now - lastDriverTime > 0.02:

        pyroslib.publish("wheel/all",
                         "fld:" + str(int(leftDeg)) + " frd:" + str(int(rightDeg)) + " bld:" + str(0) + " brd:" + str(0) + " fls:" + str(leftSideSpeed) + " frs:" + str(rightSideSpeed) + " bls:" + str(leftSideSpeed) + " brs:" + str(rightSideSpeed))

        # pyroslib.publish("wheel/fl/speed", leftSideSpeed)
        # pyroslib.publish("wheel/bl/speed", leftSideSpeed)
        # pyroslib.publish("wheel/fr/speed", rightSideSpeed)
        # pyroslib.publish("wheel/br/speed", rightSideSpeed)
        #
        # wheelDeg("fl", str(int(leftDeg)))
        # wheelDeg("fr", str(int(rightDeg)))
        # wheelDeg("bl", 0)
        # wheelDeg("br", 0)

        lastDriverTime = now

    if now > digestTime:
        pyroslib.publish("straightline/distances", str(distanceDeg1) + ":" + str(distance1) + ";" + str(avgDistance1) + "," + str(distanceDeg2) + ":" + str(distance2) + ";" + str(avgDistance2))
        digestTime = now + 0.1


if __name__ == "__main__":
    try:
        print("Starting straight-line agent...")

        pyroslib.subscribe("sensor/gyro", handleGyro)
        pyroslib.subscribe("sensor/distance", handleDistances)
        pyroslib.subscribe("straight", handleStraight)
        pyroslib.subscribe("straight/steerGain", handleSteerGain)
        pyroslib.subscribe("straight/pGain", handlePGain)
        pyroslib.subscribe("straight/iGain", handleIGain)
        pyroslib.subscribe("straight/dGain", handleDGain)

        pyroslib.init("straight-line-agent", onConnected=connected)

        print("Started straight-line agent.")

        requestDistanceAtAngle(45)

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
