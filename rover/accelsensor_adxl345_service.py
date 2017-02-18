#!/usr/bin/python3

import time
import traceback
import smbus
import pyroslib


#
# Accelerometer sensor service
#
# Based on https://github.com/pimoroni/adxl345-python/blob/master/adxl345.py
#
# This service is responsible reading accelerometer.
#

CONTINUOUS_MODE_TIMEOUT = 5  # 5 seconds before giving up on sending accel data out
MAX_ACCEL_TIMEOUT = 0.05  # 0.02 is 50 times a second so this is 50% longer

I2C_BUS = 1
I2C_ADDRESS = 0x53

# ADXL345 constants
EARTH_GRAVITY_MS2 = 9.80665
SCALE_MULTIPLIER = 0.004

DATA_FORMAT = 0x31
BW_RATE = 0x2C
POWER_CTL = 0x2D

BW_RATE_1600HZ = 0x0E
BW_RATE_800HZ = 0x0D
BW_RATE_400HZ = 0x0C
BW_RATE_200HZ = 0x0B
BW_RATE_100HZ = 0x0A
BW_RATE_50HZ = 0x09
BW_RATE_25HZ = 0x08
BW_RATE_12HZ = 0x07

RANGE_2G = 0x00
RANGE_4G = 0x01
RANGE_8G = 0x02
RANGE_16G = 0x03

MEASURE = 0x08
AXES_DATA = 0x32


lastTimeAccelRead = 0
lastTimeReceivedRequestForContMode = 0

i2cBus = None

doReadAccel = False
continuousMode = False


def initAccel():
    global i2cBus
    i2cBus = smbus.SMBus(I2C_BUS)

    # setBandwidthRate(BW_RATE_50HZ)
    # setRange(RANGE_2G)
    setBandwidthRate(BW_RATE_25HZ)
    setRange(RANGE_16G)
    enableMeasurement()


def enableMeasurement():
    i2cBus.write_byte_data(I2C_ADDRESS, POWER_CTL, MEASURE)


def setBandwidthRate(rate_flag):
    i2cBus.write_byte_data(I2C_ADDRESS, BW_RATE, rate_flag)


# set the measurement range for 10-bit readings
def setRange(range_flag):
    value = i2cBus.read_byte_data(I2C_ADDRESS, DATA_FORMAT)

    value &= ~0x0F
    value |= range_flag
    value |= 0x08

    i2cBus.write_byte_data(I2C_ADDRESS, DATA_FORMAT, value)


def bytesToInt(msb, lsb):
    if not msb & 0x80:
        return msb << 8 | lsb
    return - (((msb ^ 255) << 8) | (lsb ^ 255) + 1)


# returns the current reading from the sensor for each axis
#
# parameter gforce:
#    False (default): result is returned in m/s^2
#    True           : result is returned in gs
def readAccel(gforce=False):
    global lastTimeAccelRead

    readBytes = i2cBus.read_i2c_block_data(I2C_ADDRESS, AXES_DATA, 6)

    x = bytesToInt(readBytes[1], readBytes[0])
    y = bytesToInt(readBytes[3] & 0x03, readBytes[2])
    z = bytesToInt(readBytes[5] & 0x03, readBytes[4])

    x *= SCALE_MULTIPLIER
    y *= SCALE_MULTIPLIER
    z *= SCALE_MULTIPLIER

    if not gforce:
        x *= EARTH_GRAVITY_MS2
        y *= EARTH_GRAVITY_MS2
        z *= EARTH_GRAVITY_MS2

    x = round(x, 4)
    y = round(y, 4)
    z = round(z, 4)

    now = time.time()
    elapsedTime = now - lastTimeAccelRead

    lastTimeAccelRead = now

    return x, y, z, elapsedTime


def handleRead(topic, message, groups):
    global doReadAccel

    doReadAccel = True
    print("  Got request to start accel.")


def handleContinuous(topic, message, groups):
    global doReadAccel, continuousMode, lastTimeReceivedRequestForContMode

    continuousMode = True
    doReadAccel = True
    print("  Started continuous mode...")
    lastTimeReceivedRequestForContMode = time.time()


def loop():
    global doReadAccel, lastTimeAccelRead, continuousMode

    if doReadAccel:
        if time.time() - lastTimeAccelRead > MAX_ACCEL_TIMEOUT:
            readAccel()
            time.sleep(0.02)
        accelData = readAccel()

        pyroslib.publish("sensor/accel", str(accelData[0]) + "," + str(accelData[1]) + "," + str(accelData[2]) + "," + str(accelData[3]))

        if continuousMode:
            if time.time() - lastTimeReceivedRequestForContMode > CONTINUOUS_MODE_TIMEOUT:
                continuousMode = False
                print("  Stopped continuous mode.")
        else:
            doReadAccel = False


if __name__ == "__main__":
    try:
        print("Starting accel sensor service...")

        initAccel()

        pyroslib.subscribe("sensor/accel/read", handleRead)
        pyroslib.subscribe("sensor/accel/continuous", handleContinuous)
        pyroslib.init("accel-sensor-service")

        print("Started accel sensor service.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
