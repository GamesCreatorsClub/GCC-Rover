
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import sys
import time
import traceback
import pyroslib

DEBUG = True

MAX_TIMEOUT = 5

run = False
lastPing = time.time()

leftDeg = 0
rightDeg = 0

proportionalError = 0
integratedError = 0
derivativeError = 0

calibrationStartedTime = 0

lastContGyroTime = 0
lastTimeGyroRead = 0
thisTimeGyroRead = 0

leftSideSpeed = 75
rightSideSpeed = 75

driving = False
calibrating = True
driveAfterCalibrate = False

STEER_GAIN = 3
STEER_MAX_CONTROL = 30
# INTEGRAL_FADE_OUT = 0.95
INTEGRAL_FADE_OUT = 1

# P_GAIN = 0.9 and I_GAIN = 0.1
# P_GAIN = 0.7, I_GAIN = 0.3, GAIN = 2

P_GAIN = 0.70
I_GAIN = 0.30
D_GAIN = 0.00

steerGain = STEER_GAIN
pGain = P_GAIN
iGain = I_GAIN
dGain = D_GAIN
integralFadeOut = INTEGRAL_FADE_OUT
steerMaxControl = STEER_MAX_CONTROL


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

    print("DRIVE DIRVE DRIVE!")
    calibrating = False
    driving = True
    # leftSideSpeed = 75
    # rightSideSpeed = 75
    leftSideSpeed = 0
    rightSideSpeed = 0
    integratedError = 0
    derivativeError = 0
    pyroslib.publish("sensor/gyro/continuous", "start")


def stopDriving():
    global leftSideSpeed, rightSideSpeed, driving, calibrating
    print("STOP STOP STOP!")
    leftSideSpeed = 0
    rightSideSpeed = 0

    driving = False
    calibrating = True
    pyroslib.publish("sensor/gyro/continuous", "calibrate,50")


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
    elif calibrating:
        mode = "Calibrating:"
    else:
        mode = "Idle:       "

    if DEBUG:
        print(mode + " g:{0:>8} d:{1:>8} c:{2:>8} p:{3:>8} i:{4:>8} d:{5:>8} 7:{6:>8}".format(
              str(round(z, 3)),
              str(round(leftDeg, 1)),
              str(round(control, 3)),
              str(round(proportionalError, 3)),
              str(round(integratedError, 3)),
              str(round(derivativeError, 3)),
              str(round(dt, 3))))


def handlePing(topic, message, groups):
    global lastPing
    lastPing = time.time()


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


def loop():
    global lastContGyroTime

    now = time.time()

    if now - lastTimeGyroRead > 1:
        if calibrating:
            pyroslib.publish("sensor/gyro/continuous", "calibrate,50")
        else:
            pyroslib.publish("sensor/gyro/continuous", "start")

        lastContGyroTime = now

    pyroslib.publish("wheel/fl/speed", leftSideSpeed)
    pyroslib.publish("wheel/bl/speed", leftSideSpeed)
    pyroslib.publish("wheel/fr/speed", rightSideSpeed)
    pyroslib.publish("wheel/br/speed", rightSideSpeed)

    wheelDeg("fl", str(int(leftDeg)))
    wheelDeg("fr", str(int(rightDeg)))
    wheelDeg("bl", 0)
    wheelDeg("br", 0)

    if now - lastPing > MAX_TIMEOUT:
        print("** Didn't receive ping for more than " + str(now - lastPing) + "s. Leaving...")
        pyroslib.publish("sensor/gyro/continuous", "stop")
        sys.exit(0)


if __name__ == "__main__":
    try:
        print("Starting straight-line agent...")

        pyroslib.subscribe("sensor/gyro", handleGyro)
        pyroslib.subscribe("straight", handleStraight)
        pyroslib.subscribe("straight/ping", handlePing)
        pyroslib.subscribe("straight/steerGain", handleSteerGain)
        pyroslib.subscribe("straight/pGain", handlePGain)
        pyroslib.subscribe("straight/iGain", handleIGain)
        pyroslib.subscribe("straight/dGain", handleDGain)

        pyroslib.init("straight-line-agent", onConnected=connected)

        print("Started straight-line agent.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
