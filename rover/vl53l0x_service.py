#!/usr/bin/python3

import time
import traceback
import pyroslib
import smbus

# VL53L0X sensor service
#
# Based on https://raw.githubusercontent.com/popunder/VL53L0X/master/VL53L0Xtest.py
#
# This service is responsible reading distance.
#

CONTINUOUS_MODE_TIMEOUT = 5  # 5 seconds before giving up on sending accel data out
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
SERVO_SPEED = 0.14 * 2  # 0.14 seconds per 60º (expecting servo to be twice as slow as per specs

lastServoAngle = 0
newServoAngle = 0

stopVariable = 0
i2cBus = None

doReadSensor = False
continuousMode = False
lastTimeRead = 0
lastTimeReceivedRequestForContMode = 0
started = time.time()

def log(level, where, what):
    if level <= DEBUG_LEVEL:
        t = round(time.time() - started, 4)
        print("{0:>18} {1}: {2}".format(t, where, what))


def moveServo(angle):
    global lastServoAngle, newServoAngle

    lastServoAngle = angle
    newServoAngle = lastServoAngle

    # angle is between -90 and 90
    angle += 150
    angle = int(angle)

    f = open("/dev/servoblaster", 'w')
    f.write(str(SERVO_NUMBER) + "=" + str(angle) + "\n")
    f.close()

    angleDistance = abs(lastServoAngle - angle)
    sleepAmount = SERVO_SPEED * angleDistance / 60.0

    log(DEBUG_LEVEL_ALL, "Servo", "Moved servo to angle " + str(angle) + " for distance " + str(angleDistance) + " so sleepoing for " + str(sleepAmount))

    # wait for servo to reach the destination
    time.sleep(sleepAmount)



def initVL53L0X():
    global i2cBus, stopVariable

    i2cBus = smbus.SMBus(I2C_BUS)

    stopVariable = i2cBus.read_byte_data(I2C_ADDRESS, 0x91)


def readDistance():
    def makeuint16(lsb, msb):
        return ((msb & 0xFF) << 8) | (lsb & 0xFF)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x80, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x91, stopVariable)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x80, 0x00)

    log(DEBUG_LEVEL_ALL, "Read", "    Initiating read...")
    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSRANGE_START, 0x01)

    count = 0
    while count < 10:  # 0.1 second waiting time max
        time.sleep(0.010)
        val = i2cBus.read_byte_data(I2C_ADDRESS, VL53L0X_REG_RESULT_RANGE_STATUS)
        if val & 0x01:
            break
        count += 1

    data = i2cBus.read_i2c_block_data(I2C_ADDRESS, 0x14, 12)

    status = ((data[0] & 0x78) >> 3)

    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSTEM_INTERRUPT_CLEAR, 0x01)

    if DEBUG_LEVEL > DEBUG_LEVEL_OFF:
        # if status == 0:
        #     print("    Data OK!")
        if status == 0x01:
            log(DEBUG_LEVEL_INFO, "Read", "    VCSEL CONTINUITY TEST FAILURE!")
        if status == 0x02:
            log(DEBUG_LEVEL_INFO, "Read", "    VCSEL WATCHDOG TEST FAILURE!")
        if status == 0x03:
            log(DEBUG_LEVEL_INFO, "Read", "    NO VHV VALUE FOUND!")
        if status == 0x04:
            log(DEBUG_LEVEL_INFO, "Read", "    MSRC NO TARGET!")
        if status == 0x05:
            log(DEBUG_LEVEL_INFO, "Read", "    SNR CHECK!")
        if status == 0x06:
            log(DEBUG_LEVEL_INFO, "Read", "    RANGE PHASE CHECK!")
        if status == 0x07:
            log(DEBUG_LEVEL_INFO, "Read", "    SIGMA THRESHOLD CHECK!")
        if status == 0x08:
            log(DEBUG_LEVEL_INFO, "Read", "    TCC!")
        if status == 0x09:
            log(DEBUG_LEVEL_INFO, "Read", "    PHASE CONSISTENCY!")
        if status == 0x0A:
            log(DEBUG_LEVEL_INFO, "Read", "    MIN CLIP!")
        # if status == 0x0B:
        #     log("Read", "    RANGE COMPLETE!")
        if status == 0x0C:
            log(DEBUG_LEVEL_INFO, "Read", "    ALGO UNDERFLOW!")
        if status == 0x0D:
            log(DEBUG_LEVEL_INFO, "Read", "    ALGO OVERFLOW!")
        if status == 0x0E:
            log(DEBUG_LEVEL_INFO, "Read", "    RANGE IGNORE THRESHOLD!")


    if status == 0x0B or status == 0:
        distance = makeuint16(data[11], data[10])
    else:
        distance = -1

    log(DEBUG_LEVEL_INFO, "Read", "  Distance is " + str(distance) + "mm. Got result after " + str(count) + " checks. Status " + bin(status))

    return distance


def handleRead(topic, payload, groups):

    angle = float(payload)
    log(DEBUG_LEVEL_INFO, "Message", "Got read - moving to angle " + str(angle))

    moveServo(angle)
    distance = readDistance()
    pyroslib.publish("sensor/distance", str(angle) + ":" + str(distance))


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

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
