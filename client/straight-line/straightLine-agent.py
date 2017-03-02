
import time
import traceback
import pyroslib

leftDeg = 0
rightDeg = 0

proportionalError = 0
integratedError = 0
derivativeError = 0

calibrationStartedTime = 0
calibrationAverage = 0
calibratingCounts = 0

lastContGyroTime = 0
lastTimeGyroRead = 0
thisTimeGyroRead = 0

leftSideSpeed = 75
rightSideSpeed = 75

gyroCentre = 0
gyroMin = 0
gyroMax = 0

driving = False
calibrating = False
driveAfterCalibrate = False


def connected():
    pyroslib.publish("sensor/gyro/continuous", "")


def handleStraight(topic, message, groups):
    global integratedError, driving, calibrating

    if message == "forward":
        startDriving()
    elif message == "calibrate-and-go":
        startCalibratingAndGo()
    elif message == "calibrate":
        startCalibrating()
    elif message == "stop":
        stopDriving()


def wheelDeg(wheelName, angle):
    topic = "wheel/" + wheelName + "/deg"
    pyroslib.publish(topic, str(angle))


def startDriving():
    global driveAfterCalibrate, driving, calibrating, leftSideSpeed, rightSideSpeed, leftDeg, rightDeg, integratedError, derivativeError

    print("DRIVE DIRVE DRIVE!")
    calibrating = False
    driveAfterCalibrate = False
    driving = True
    leftSideSpeed = 75
    rightSideSpeed = 75
    integratedError = 0
    derivativeError = 0


def startCalibratingAndGo():
    global driveAfterCalibrate

    startCalibrating()
    driveAfterCalibrate = True


def startCalibrating():
    global driveAfterCalibrate, driving, calibrating, leftSideSpeed, rightSideSpeed, leftDeg, rightDeg, calibrationStartedTime

    print("CALIBRATING!")
    calibrating = True
    driveAfterCalibrate = False
    driving = False
    leftSideSpeed = 0
    rightSideSpeed = 0
    leftDeg = 0
    rightDeg = 0
    calibrationStartedTime = time.time()


def stopDriving():
    global leftSideSpeed, rightSideSpeed, driving, calibrating
    print("STOP STOP STOP!")
    leftSideSpeed = 0
    rightSideSpeed = 0

    driving = False
    calibrating = False


def getError(gyroAngle):
    if gyroAngle > gyroMax or gyroAngle < gyroMin:
        return gyroAngle - gyroCentre

    return 0.0


SPEED = 250

SPEED_GAIN = 0.3  # 0.4
SPEED_MAX_CONTROL = 75

CONTROL_STEERING = True
CONTROL_MOTORS = False

CONTROL_TYPE = CONTROL_STEERING

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

wheelDeg("fl", 0)
wheelDeg("fr", 0)
wheelDeg("bl", 0)
wheelDeg("br", 0)


def handleGyro(topic, message, groups):
    global driving, calibrating
    global proportionalError, integratedError, derivativeError
    global leftDeg, rightDeg
    global rightSideSpeed, leftSideSpeed
    global gyroCentre, gyroMin, gyroMax, calibrationStartedTime, calibratingCounts, calibrationAverage

    previousError = 0
    control = 0

    data = message.split(",")
    z = float(data[2])
    dt = float(data[3])

    thisTimeGyroRead2 = time.time()
    if driving:

        integratedError *= integralFadeOut

        proportionalError = getError(z)
        integratedError += proportionalError  # * dt

        if dt == 0:
            derivativeError = 0
        else:
            derivativeError = (proportionalError - previousError)  # / dt

        previousError = proportionalError

        control = pGain * proportionalError + iGain * integratedError + dGain * derivativeError

        controlSpeed = int(control * SPEED_GAIN)

        if controlSpeed > SPEED_MAX_CONTROL:
            controlSpeed = SPEED_MAX_CONTROL
        elif controlSpeed < -SPEED_MAX_CONTROL:
            controlSpeed = -SPEED_MAX_CONTROL

        controlSteer = control * steerGain
        if controlSteer > steerMaxControl:
            controlSteer = steerMaxControl
        elif controlSteer < -steerMaxControl:
            controlSteer = -steerMaxControl

        if CONTROL_TYPE == CONTROL_MOTORS:
            rightSideSpeed = SPEED - controlSpeed
            leftSideSpeed = SPEED + controlSpeed
        else:
            rightSideSpeed = SPEED
            leftSideSpeed = SPEED

        if CONTROL_TYPE == CONTROL_STEERING:
            leftDeg = int(-controlSteer)
            rightDeg = int(-controlSteer)
        else:
            leftDeg = 1
            rightDeg = 1
    elif calibrating:
        now = time.time()
        if now - calibrationStartedTime > 1:
            calibrating = False
            gyroCentre = calibrationAverage / 50.0
            print("CALIBRATED:   centre: {0:>12}  min: {1:>12}  max: {2:>12}".format(
                str(round(gyroCentre, 5)),
                str(round(gyroMin, 5)),
                str(round(gyroMax, 5))
            ))
            if driveAfterCalibrate:
                startDriving()
                print("DRIVE!--------------------------->")
        else:
            calibratingCounts += 1
            calibrationAverage += z

            if z > gyroMax:
                gyroMax = z
            if z < gyroMin:
                gyroMin = z

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

    print(mode + " g:{0:>8} d:{1:>8} c:{2:>8} p:{3:>8} i:{4:>8} d:{5:>8} 7:{6:>8}".format(
          str(round(z, 3)),
          str(round(leftDeg, 1)),
          str(round(control, 3)),
          str(round(proportionalError, 3)),
          str(round(integratedError, 3)),
          str(round(derivativeError, 3)),
          str(round(dt, 3))))


def loop():
    global lastContGyroTime

    now = time.time()

    if now - lastTimeGyroRead > 1:
        pyroslib.publish("sensor/gyro/continuous", "")
        lastContGyroTime = now

    pyroslib.publish("wheel/fl/speed", leftSideSpeed)
    pyroslib.publish("wheel/bl/speed", leftSideSpeed)
    pyroslib.publish("wheel/fr/speed", rightSideSpeed)
    pyroslib.publish("wheel/br/speed", rightSideSpeed)

    wheelDeg("fl", str(int(leftDeg)))
    wheelDeg("fr", str(int(rightDeg)))
    wheelDeg("bl", 0)
    wheelDeg("br", 0)


if __name__ == "__main__":
    try:
        print("Starting straight-line agent...")

        pyroslib.subscribe("straight", handleStraight)
        pyroslib.subscribe("sensor/gyro", handleGyro)

        pyroslib.init("straight-line-agent", onConnected=connected)

        print("Started straight-line agent.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
