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

DEBUG = True

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

stopVariable = 0
i2cBus = None


def moveServo(angle):
    global lastServoAngle
    # angle is between -90 and 90
    angle += 150
    angle = int(angle)

    f = open("/dev/servoblaster", 'w')
    f.write(str(SERVO_NUMBER) + "=" + str(angle) + "\n")
    f.close()

    angleDistance = abs(lastServoAngle - angle)
    sleepAmount = SERVO_SPEED * angleDistance / 60.0

    if DEBUG:
        print("Moved servo to angle " + str(angle) + " for distance " + str(angleDistance) + " so sleepoing for " + str(sleepAmount))

    # wait for servo to reach the destination
    time.sleep(sleepAmount)

    lastServoAngle = angle


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

    if DEBUG:
        print("    Initiating read...")
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

    if DEBUG:
        # if status == 0:
        #     print("    Data OK!")
        if status == 0x01:
            print("    VCSEL CONTINUITY TEST FAILURE!")
        if status == 0x02:
            print("    VCSEL WATCHDOG TEST FAILURE!")
        if status == 0x03:
            print("    NO VHV VALUE FOUND!")
        if status == 0x04:
            print("    MSRC NO TARGET!")
        if status == 0x05:
            print("    SNR CHECK!")
        if status == 0x06:
            print("    RANGE PHASE CHECK!")
        if status == 0x07:
            print("    SIGMA THRESHOLD CHECK!")
        if status == 0x08:
            print("    TCC!")
        if status == 0x09:
            print("    PHASE CONSISTENCY!")
        if status == 0x0A:
            print("    MIN CLIP!")
        # if status == 0x0B:
        #     print("    RANGE COMPLETE!")
        if status == 0x0C:
            print("    ALGO UNDERFLOW!")
        if status == 0x0D:
            print("    ALGO OVERFLOW!")
        if status == 0x0E:
            print("    RANGE IGNORE THRESHOLD!")

        print("    Got result after " + str(count) + " checks. Status " + bin(status))

    if status == 0x0B or status == 0:
        distance = makeuint16(data[11], data[10])
    else:
        distance = -1

    if DEBUG:
        print("  Distance is " + str(distance) + "mm")

    return distance


def handleRead(topic, payload, groups):
    angle = float(payload)
    if DEBUG:
        print("Got read - moving to angle " + str(angle))

    moveServo(angle)
    distance = readDistance()
    # print ("   distance =" + str(distance))
    pyroslib.publish("sensor/distance", str(angle) + ":" + str(distance))


def handleScan(topic, payload, groups):
    startScan = True

    if DEBUG:
        print("  Got scan...")

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


if __name__ == "__main__":
    try:
        print("Starting vl53l0x sensor service...")

        initVL53L0X()

        moveServo(lastServoAngle)

        time.sleep(1)

        pyroslib.subscribe("sensor/distance/read", handleRead)
        pyroslib.subscribe("sensor/distance/scan", handleScan)
        pyroslib.init("vl53l0x-sensor-service")

        print("Started vl53l0x sensor service.")

        pyroslib.forever(0.02)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
