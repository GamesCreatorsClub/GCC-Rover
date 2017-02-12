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

BW_RATE_1600HZ = 0x0F
BW_RATE_800HZ = 0x0E
BW_RATE_400HZ = 0x0D
BW_RATE_200HZ = 0x0C
BW_RATE_100HZ = 0x0B
BW_RATE_50HZ = 0x0A
BW_RATE_25HZ = 0x09

RANGE_2G = 0x00
RANGE_4G = 0x01
RANGE_8G = 0x02
RANGE_16G = 0x03

MEASURE = 0x08
AXES_DATA = 0x32


lastTimeAccelRead = 0
lastTimeReceivedRequestForContMode = 0

i2c_bus = None

readAccel = False
continuousMode = False


def initAccel():
    global i2c_bus
    i2c_bus = smbus.SMBus(I2C_BUS)

    setBandwidthRate(BW_RATE_50HZ)
    setRange(RANGE_2G)
    enableMeasurement()


def enableMeasurement():
    i2c_bus.write_byte_data(I2C_ADDRESS, POWER_CTL, MEASURE)


def setBandwidthRate(rate_flag):
    i2c_bus.write_byte_data(I2C_ADDRESS, BW_RATE, rate_flag)


# set the measurement range for 10-bit readings
def setRange(range_flag):
    value = i2c_bus.read_byte_data(I2C_ADDRESS, DATA_FORMAT)

    value &= ~0x0F
    value |= range_flag
    value |= 0x08

    i2c_bus.write_byte_data(I2C_ADDRESS, DATA_FORMAT, value)


# returns the current reading from the sensor for each axis
#
# parameter gforce:
#    False (default): result is returned in m/s^2
#    True           : result is returned in gs
def getAxes(gforce=False):
    global lastTimeAccelRead

    readBytes = i2c_bus.read_i2c_block_data(I2C_ADDRESS, AXES_DATA, 6)

    x = readBytes[0] | (readBytes[1] << 8)
    if x & (1 << 16 - 1):
        x -= (1 << 16)

    y = readBytes[2] | (readBytes[3] << 8)
    if y & (1 << 16 - 1):
        y -= (1 << 16)

    z = readBytes[4] | (readBytes[5] << 8)
    if z & (1 << 16 - 1):
        z -= (1 << 16)

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

    return {"x": x, "y": y, "z": z, "t": elapsedTime}


def handleRead(topic, message, groups):
    global readAccel

    readAccel = True
    print("  Got request to start accel.")


def handleContinuous(topic, message, groups):
    global readAccel, continuousMode, lastTimeReceivedRequestForContMode

    continuousMode = True
    readAccel = True
    print("  Started continuous mode...")
    lastTimeReceivedRequestForContMode = time.time()


def loop():
    global readAccel, lastTimeAccelRead, continuousMode

    if readAccel:
        if time.time() - lastTimeAccelRead > MAX_ACCEL_TIMEOUT:
            accelData = getAxes()
            time.sleep(0.02)
        accelData = getAxes()

        pyroslib.publish("sensor/accel", str(accelData.x) + "," + str(accelData.y) + "," + str(accelData.z) + "," + str(accelData.t))

        if continuousMode:
            if time.time() - lastTimeReceivedRequestForContMode > CONTINUOUS_MODE_TIMEOUT:
                continuousMode = False
                print("  Stopped continuous mode.")
        else:
            readAccel = False


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
