#!/usr/bin/python3

import time
import traceback
import pyroslib
import VL53L0X

# VL53L0X sensor service
#
# Based on https://raw.githubusercontent.com/popunder/VL53L0X/master/VL53L0Xtest.py
#
# This service is responsible reading distance.
#

CONTINUOUS_MODE_TIMEOUT = 3  # 5 seconds before giving up on sending accel data out
MAX_TIMEOUT = 0.05  # 0.02 is 50 times a second so this is 50% longer

DEBUG_LEVEL_OFF = 0
DEBUG_LEVEL_INFO = 1
DEBUG_LEVEL_ALL = 2
DEBUG_LEVEL = DEBUG_LEVEL_INFO

I2C_BUS = 1
I2C_ADDRESS = 0x29

VL53L0X_REG_IDENTIFICATION_MODEL_ID = 0xc0
VL53L0X_REG_IDENTIFICATION_REVISION_ID = 0xc2
VL53L0X_REG_PRE_RANGE_CONFIG_VCSEL_PERIOD = 0x50
VL53L0X_REG_FINAL_RANGE_CONFIG_VCSEL_PERIOD = 0x70
VL53L0X_REG_SYSRANGE_START = 0x0

VL53L0X_REG_SYSTEM_INTERRUPT_CLEAR = 0x0B

VL53L0X_REG_RESULT_INTERRUPT_STATUS = 0x13
VL53L0X_REG_RESULT_RANGE_STATUS = 0x14

SERVO_NUMBER = 8
SERVO_SPEED = 0.14 * 2  # 0.14 seconds per 60 (expecting servo to be twice as slow as per specs

timing = 100

lastServoAngle = 0
newServoAngle = 0

stopVariable = 0
i2cBus = None

doReadSensor = False
continuousMode = False
lastTimeRead = 0
lastTimeReceivedRequestForContMode = 0
started = time.time()

tof = None
lastRead = time.time()


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

    f = open("/dev/servoblaster", 'w')
    f.write(str(SERVO_NUMBER) + "=" + str(angle) + "\n")
    f.close()

    log(DEBUG_LEVEL_ALL, "Servo", "Moved servo to angle " + str(angle) + " for distance " + str(angleDistance) + " so sleepoing for " + str(sleepAmount))

    # wait for servo to reach the destination
    time.sleep(sleepAmount)


def initVL53L0X():
    global tof, timing
    tof = VL53L0X.VL53L0X()
    tof.start_ranging(VL53L0X.VL53L0X_BETTER_ACCURACY_MODE)
    timing = tof.get_timing()
    if timing < 20000:
        timing = 20000
        print("Capped timing to 20000!")

    print("Timing %d ms" % (timing/1000))


def readDistance():
    global lastRead

    now = time.time()
    if now - lastRead < timing/1000000.00:
        time.sleep(timing / 1000000.00)
        log(DEBUG_LEVEL_ALL, "Read", "Slept for " + str(timing / 1000000.00) + "s")

    distance = tof.get_distance()
    log(DEBUG_LEVEL_INFO, "Read", "Got distance " + str(distance) + "mm")

    lastRead = time.time()

    # if distance > 10:
    #     distance -= 10

    return distance


def handleRead(topic, payload, groups):
    angle = float(payload)
    log(DEBUG_LEVEL_INFO, "Message", "Got read - moving to angle " + str(angle))

    moveServo(angle)
    distance = readDistance()
    pyroslib.publish("sensor/distance", str(round(angle, 1)) + ":" + str(int(distance)))


def handleScan(topic, payload, groups):
    startScan = True

    log(DEBUG_LEVEL_INFO, "Message", "  Got scan...")

    distances = {}
    angle = -90
    while angle <= 90:
        moveServo(float(angle))
        distance = readDistance()
        if distance < 0:
            distance = 2000
        distances[angle] = distance
        angle += 22.5

    angle = 90
    while angle >= -90:
        moveServo(float(angle))
        distance = readDistance()
        if distance < 0:
            distance = 2000
            distances[angle] = 2000
        elif distance < distances[angle]:
            distances[angle] = distance
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


def loop():
    global doReadSensor, lastTimeRead, continuousMode, newServoAngle

    if doReadSensor:
        if lastServoAngle != newServoAngle:
            moveServo(newServoAngle)
            log(DEBUG_LEVEL_INFO, "Loop", "  Moved to the new angle " + str(newServoAngle))

        count = 0
        distance = -1
        while count < 3 and distance == -1:
            distance = readDistance()
            if distance == -1:
                pyroslib.sleep(0.001)

        if distance != -1:
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

        initVL53L0X()

        moveServo(lastServoAngle)

        time.sleep(1)

        pyroslib.subscribe("sensor/distance/deg", handleDeg)
        pyroslib.subscribe("sensor/distance/read", handleRead)
        pyroslib.subscribe("sensor/distance/scan", handleScan)
        pyroslib.subscribe("sensor/distance/continuous", handleContinuousMode)
        pyroslib.init("vl53l0x-sensor-service")

        print("Started vl53l0x sensor service.")

        pyroslib.forever(0.01, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
