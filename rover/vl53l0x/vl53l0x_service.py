#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import time
import traceback

import smbus
import RPi.GPIO as GPIO
import pyroslib
import vl53l0xWrapper
import vl53l0xPython

USE_PYTHON_IMPL = True

SENSORS_SWITCH_GPIO = 4

CONTINUOUS_MODE_TIMEOUT = 3  # 5 seconds before giving up on sending accel data out
MAX_TIMEOUT = 0.05  # 0.02 is 50 times a second so this is 20 times a second

DEBUG_LEVEL_OFF = 0
DEBUG_LEVEL_INFO = 1
DEBUG_LEVEL_ALL = 2
DEBUG_LEVEL = DEBUG_LEVEL_INFO

SERVO_NUMBER = 8
SERVO_SPEED = 0.14 * 2  # 0.14 seconds per 60 (expecting servo to be twice as slow as per specs

timing = 100

lastServoAngle = 0
newServoAngle = 0

stopVariable = 0

doReadSensor = False
continuousMode = False
lastTimeRead = 0
lastTimeReceivedRequestForContMode = 0
started = time.time()

tof = None
lastRead = time.time()

twoSensorsMode = False
initialised = False

haveFirstSensor = False
haveSecondSensor = False

FIRST_SENSOR_I2C_ADDRESS = vl53l0xPython.I2C_ADDRESS + 2
SECOND_SENSOR_I2C_ADDRESS = vl53l0xPython.I2C_ADDRESS + 1
ORIGINAL_SENSOR_I2C_ADDRESS = vl53l0xPython.I2C_ADDRESS


def log(level, where, what):
    if level <= DEBUG_LEVEL:
        t = round(time.time() - started, 4)
        print("{0:>18} {1}: {2}".format(t, where, what))


def moveServo(angle):
    global lastServoAngle, newServoAngle

    angleDistance = abs(lastServoAngle - angle)
    sleepAmount = SERVO_SPEED * angleDistance / 60.0

    lastServoAngle = angle
    newServoAngle = lastServoAngle

    # angle is between -90 and 90
    angle += 150
    angle = int(angle)

    with open("/dev/servoblaster", 'w') as f:
        f.write(str(SERVO_NUMBER) + "=" + str(angle) + "\n")

    log(DEBUG_LEVEL_ALL, "Servo", "Moved servo to angle " + str(angle) + " for distance " + str(angleDistance) + " so sleepoing for " + str(sleepAmount))

    # wait for servo to reach the destination
    time.sleep(sleepAmount)


def secondSensorOn():
    GPIO.output(SENSORS_SWITCH_GPIO, 1)


def secondSensorOff():
    GPIO.output(SENSORS_SWITCH_GPIO, 0)


def initWrapper():
    global tof, timing, initialised

    tof = vl53l0xWrapper.VL53L0X()
    # tof.start_ranging(vl53l0xapi.VL53L0X_HIGH_SPEED_MODE)
    tof.start_ranging(vl53l0xWrapper.VL53L0X_BETTER_ACCURACY_MODE)

    timing = tof.get_timing()
    if timing < 20000:
        timing = 20000
        print("Capped timing to 20000!")

    print("Timing %d ms" % (timing/1000))


def initI2CSensor(address):
    vl53l0xPython.initVL53L0X(address)
    vl53l0xPython.setMeasurementTimingBudget(address, 50000)
    vl53l0xPython.startContinuous(address, 0)


def testI2C(bus, address):
    bus.read_byte_data(address, vl53l0xPython.VL53L0X_REG_RESULT_RANGE_STATUS)


def init():
    global twoSensorsMode, initialised, haveFirstSensor, haveSecondSensor

    if USE_PYTHON_IMPL:
        i2cBus = smbus.SMBus(vl53l0xPython.I2C_BUS)

        haveFirstSensor = False
        haveSecondSensor = False

        try:
            testI2C(i2cBus, FIRST_SENSOR_I2C_ADDRESS)
            initI2CSensor(FIRST_SENSOR_I2C_ADDRESS)
            print("    got first sensor")

            haveFirstSensor = True

            try:
                testI2C(i2cBus, SECOND_SENSOR_I2C_ADDRESS)
                initI2CSensor(SECOND_SENSOR_I2C_ADDRESS)
                print("    got second sensor")

                haveSecondSensor = True
                twoSensorsMode = True
                initialised = True
                print("  initialised two sensors")
            except:
                print("    second sensor missing")
                secondSensorOn()

                try:
                    testI2C(i2cBus, ORIGINAL_SENSOR_I2C_ADDRESS)
                    print("    found defalt address sensor (1)")
                    vl53l0xPython.setAddress(ORIGINAL_SENSOR_I2C_ADDRESS, SECOND_SENSOR_I2C_ADDRESS)
                    initI2CSensor(SECOND_SENSOR_I2C_ADDRESS)
                    print("    second sensor address set")

                    haveSecondSensor = True
                    twoSensorsMode = True
                    initialised = True
                    print("  initialised two sensors")
                except:
                    print("    no default sensor found (1)")
                    haveSecondSensor = False
                    twoSensorsMode = False
                    initialised = True
                    print("  initialised one sensor")

        except BaseException as x:
            print("    first sensor missing, " + str(x))
            secondSensorOff()
            try:
                testI2C(i2cBus, ORIGINAL_SENSOR_I2C_ADDRESS)
                print("    found defalt address sensor (2)")
                vl53l0xPython.setAddress(ORIGINAL_SENSOR_I2C_ADDRESS, FIRST_SENSOR_I2C_ADDRESS)
                print("    first sensor address set")
                initI2CSensor(FIRST_SENSOR_I2C_ADDRESS)
                haveFirstSensor = True

                secondSensorOn()
                time.sleep(0.1)
                try:
                    testI2C(i2cBus, ORIGINAL_SENSOR_I2C_ADDRESS)
                    print("    found defalt address sensor (3)")
                    vl53l0xPython.setAddress(ORIGINAL_SENSOR_I2C_ADDRESS, SECOND_SENSOR_I2C_ADDRESS)
                    initI2CSensor(SECOND_SENSOR_I2C_ADDRESS)
                    print("    second sensor address set")

                    haveSecondSensor = True
                    twoSensorsMode = True
                    initialised = True
                    print("  initialised two sensors")
                except BaseException as x:
                    print("    second sensor missing, no default address sensor found " + str(x))
                    haveSecondSensor = False
                    twoSensorsMode = False
                    initialised = True
                    print("  initialised one sensor")
            except BaseException as x:
                print("    no default sensor found (2) " + str(x))
                haveFirstSensor = False
                haveSecondSensor = False
                twoSensorsMode = False
                initialised = False
                print("  no sensors available")

    else:
        twoSensorsMode = False
        initWrapper()


def stopRangingWrapper():
    if tof is not None:
        tof.stop_ranging()


def stopRangingPython():
    if haveFirstSensor:
        vl53l0xPython.stopContinuous(FIRST_SENSOR_I2C_ADDRESS)
    if haveSecondSensor:
        vl53l0xPython.stopContinuous(SECOND_SENSOR_I2C_ADDRESS)


def stopRanging():
    if USE_PYTHON_IMPL:
        stopRangingPython()
    else:
        stopRangingWrapper()


def readDistancePython():
    global lastRead, lastReadSensor, initialised

    if not initialised:
        init()

    if not initialised:
        return -1

    now = time.time()
    if now - lastRead < timing/1000000.00:
        time.sleep(timing / 1000000.00)
        log(DEBUG_LEVEL_ALL, "Read", "Slept for " + str(timing / 1000000.00) + "s")

    if twoSensorsMode:
        timeout_start_ms = time.time()
        distance1 = -1
        distance2 = -1
        lastReadSensor = 1

        try:
            budget = vl53l0xPython.getMeasurementTimingBudget(FIRST_SENSOR_I2C_ADDRESS)
            timeout = (budget / 1000000) * 2 + MAX_TIMEOUT
            while (distance1 <= 0 or distance2 <= 0) and time.time() - timeout_start_ms < timeout:
                if distance1 <= 0:
                    distance1 = vl53l0xPython.readRangeContinuousMillimetersFastFail(FIRST_SENSOR_I2C_ADDRESS)
                if distance2 <= 0:
                    distance2 = vl53l0xPython.readRangeContinuousMillimetersFastFail(SECOND_SENSOR_I2C_ADDRESS)

            log(DEBUG_LEVEL_INFO, "Read", "Got distances " + str(distance1) + "mm and " + str(distance2) + "mm after "
                + str(time.time() - timeout_start_ms) + "s, budget " + str(budget))
        except:
            initialised = False
            distance1 = -1
            distance2 = -1

        # try:
        #     distance1 = vl53l0xPython.readRangeContinuousMillimeters(FIRST_SENSOR_I2C_ADDRESS)
        #     distance2 = vl53l0xPython.readRangeContinuousMillimeters(SECOND_SENSOR_I2C_ADDRESS)
        # except:
        #     initialised = False
        #     distance1 = -1
        #     distance2 = -1

        # log(DEBUG_LEVEL_INFO, "Read", "Got distances " + str(distance1) + "mm and " + str(distance2) + "mm after "
        #     + str(time.time() - timeout_start_ms) + "s")

        lastRead = time.time()

        return distance1, distance2

    else:
        distance = vl53l0xPython.readRangeContinuousMillimeters(FIRST_SENSOR_I2C_ADDRESS)
        log(DEBUG_LEVEL_INFO, "Read", "Got distance " + str(distance) + "mm")

        lastRead = time.time()

        return distance


def readDistanceWrapper():
    global lastRead

    now = time.time()
    if now - lastRead < timing/1000000.00:
        time.sleep(timing / 1000000.00)
        log(DEBUG_LEVEL_ALL, "Read", "Slept for " + str(timing / 1000000.00) + "s")

    distance = tof.get_distance()
    log(DEBUG_LEVEL_INFO, "Read", "Got distance " + str(distance) + "mm")

    lastRead = time.time()

    return distance


def readDistance():
    if USE_PYTHON_IMPL:
        return readDistancePython()
    else:
        return readDistanceWrapper()


def handleRead(topic, payload, groups):
    angle = float(payload)
    log(DEBUG_LEVEL_INFO, "Message", "Got read - moving to angle " + str(angle))

    if lastServoAngle != angle:
        moveServo(angle)

    distance = readDistance()
    if twoSensorsMode:
        distance1 = distance[0]
        distance2 = distance[1]
        if distance1 > 0 or distance2 > 0:
            message = ""
            if distance1 > 0:
                message = message + str(round(angle, 1)) + ":" + str(int(distance1))

            if distance2 > 0:
                if distance1 > 0:
                    message = message + ","
                message = message + str(round(angle - 90.0, 1)) + ":" + str(int(distance2))

            pyroslib.publish("sensor/distance", message)

    else:
        if distance > 0:
            pyroslib.publish("sensor/distance", str(round(angle, 1)) + ":" + str(int(distance)))
        elsew(DEBUG_LEVEL_INFO, "handleRead", "Failed reading - got " + str(distance))


def handleScan(topic, payload, groups):
    distances = {}

    def update(a, d):
        if d <= 0:
            if a not in distances:
                distances[a] = 2000
        else:
            if a not in distances:
                distances[a] = d
            elif d < distances[a]:
                distances[a] = d

    startScan = True

    log(DEBUG_LEVEL_INFO, "Message", "  Got scan...")

    if twoSensorsMode:
        startAngle = 0
        finalAngle = 90
    else:
        startAngle = -90
        finalAngle = 90

    angle = startAngle
    while angle <= finalAngle:
        moveServo(float(angle))
        distance = readDistance()
        if twoSensorsMode:
            distance1 = distance[0]
            distance2 = distance[1]
            update(angle, distance1)
            update(angle - 90.0, distance2)
        else:
            update(angle, distance)
        angle += 22.5

    angle = finalAngle
    while angle >= startAngle:
        moveServo(float(angle))
        distance = readDistance()
        if twoSensorsMode:
            distance1 = distance[0]
            distance2 = distance[1]
            update(angle, distance1)
            update(angle - 90.0, distance2)

        else:
            update(angle, distance)
        angle -= 22.5

    angles = list(distances.keys())
    angles.sort()

    distancesList = []
    for angle in angles:
        distancesList.append(str(angle) + ":" + str(distances[angle]))

    # print ("   distance =" + str(distance))
    pyroslib.publish("sensor/distance", str(",".join(distancesList)))


def handleContinuousMode(topic, message, groups):
    global doReadSensor, continuousMode, lastTimeReceivedRequestForContMode

    if message.startswith("stop"):
        continuousMode = False
        doReadSensor = False

    else:
        if not continuousMode:
            continuousMode = True
            doReadSensor = True
            log(DEBUG_LEVEL_INFO, "Message", "  Started continuous mode...")

        lastTimeReceivedRequestForContMode = time.time()


def handleDeg(topic, message, groups):
    global newServoAngle

    newServoAngle = float(message)
    log(DEBUG_LEVEL_INFO, "Message", "  Got new angle " + message)


def handleConf(topic, message, groups):
    global twoSensorsMode

    split = message.split(";")
    for conf in split:
        # log(DEBUG_LEVEL_INFO, "Config", "Config segment: " + conf)
        kv = conf.split("=")
        if len(kv) > 1:
            if kv[0].lower() == "twosensormode":
                newTwoSensorsMode = kv[1].lower() in ("yes", "true", "t", "1")
                log(DEBUG_LEVEL_INFO, "Config", "Set two sensor mode to " + str(twoSensorsMode))
                if newTwoSensorsMode != twoSensorsMode:
                    stopRanging()
                    twoSensorsMode = newTwoSensorsMode
                    init()


def loop():
    global doReadSensor, lastTimeRead, continuousMode, newServoAngle

    if doReadSensor:
        if lastServoAngle != newServoAngle:
            moveServo(newServoAngle)
            log(DEBUG_LEVEL_INFO, "Loop", "  Moved to the new angle " + str(newServoAngle))

        distance = readDistance()
        if twoSensorsMode:
            distance1 = distance[0]
            distance2 = distance[1]
            if distance1 > 0 or distance2 > 0:
                message = ""
                if distance1 > 0:
                    message = message + str(round(lastServoAngle, 1)) + ":" + str(int(distance1))

                if distance2 > 0:
                    if distance1 > 0:
                        message = message + ","
                    message = message + str(round(lastServoAngle - 90.0, 1)) + ":" + str(int(distance2))

                pyroslib.publish("sensor/distance", message)
        else:
            if distance > 0:
                pyroslib.publish("sensor/distance", str(lastServoAngle) + ":" + str(distance))

        if continuousMode:
            if time.time() - lastTimeReceivedRequestForContMode > CONTINUOUS_MODE_TIMEOUT:
                continuousMode = False
                log(DEBUG_LEVEL_INFO, "Message", "  Stopped continuous mode.")
        else:
            doReadSensor = False


if __name__ == "__main__":
    try:
        print("Starting vl53l0x sensor service...")

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SENSORS_SWITCH_GPIO, GPIO.OUT)

        init()

        moveServo(lastServoAngle)

        time.sleep(1)

        pyroslib.subscribe("sensor/distance/deg", handleDeg)
        pyroslib.subscribe("sensor/distance/read", handleRead)
        pyroslib.subscribe("sensor/distance/scan", handleScan)
        pyroslib.subscribe("sensor/distance/conf", handleConf)
        pyroslib.subscribe("sensor/distance/continuous", handleContinuousMode)
        pyroslib.init("vl53l0x-sensor-service")

        print("Started vl53l0x sensor service.")

        pyroslib.forever(0.01, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
