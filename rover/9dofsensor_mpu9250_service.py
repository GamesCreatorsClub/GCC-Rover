#!/usr/bin/python3

import time
import traceback
import smbus
import pyroslib


#
# Accelerometer sensor service
#
# Based on https://github.com/FaBoPlatform/FaBo9AXIS-MPU9250-Python/blob/master/FaBo9Axis_MPU9250/MPU9250.py
#
# This service is responsible reading accelerometer.
#

CONTINUOUS_MODE_TIMEOUT = 5  # 5 seconds before giving up on sending accel data out
MAX_TIMEOUT = 0.05  # 0.02 is 50 times a second so this is 50% longer

I2C_BUS = 1
I2C_ADDRESS = 0x68

GYRO_RANGE_250_DPS = 0
GYRO_RANGE_500_DPS = 1
GYRO_RANGE_1000_DPS = 2
GYRO_RANGE_2000_DPS = 3

GYRO_RESOLUTION_250_DPS = 250.0/32768.0
GYRO_RESOLUTION_500_DPS = 500.0/32768.0
GYRO_RESOLUTION_1000_DPS = 1000.0/32768.0
GYRO_RESOLUTION_2000_DPS = 2000.0/32768.0

GYRO_LOW_PASS_FILTER_CUTOFF_250Hz = 0
GYRO_LOW_PASS_FILTER_CUTOFF_184Hz = 1
GYRO_LOW_PASS_FILTER_CUTOFF_92Hz = 2
GYRO_LOW_PASS_FILTER_CUTOFF_41Hz = 3
GYRO_LOW_PASS_FILTER_CUTOFF_20Hz = 4
GYRO_LOW_PASS_FILTER_CUTOFF_10Hz = 5
GYRO_LOW_PASS_FILTER_CUTOFF_5Hz = 6
GYRO_LOW_PASS_FILTER_CUTOFF_3600Hz = 7

ACCEL_RANGE_2G = 0
ACCEL_RANGE_4G = 1
ACCEL_RANGE_8G = 2
ACCEL_RANGE_16G = 3

ACCEL_RESOUTION_2G = 2.0/32768.0
ACCEL_RESOUTION_4G = 4.0/32768.0
ACCEL_RESOUTION_8G = 8.0/32768.0
ACCEL_RESOUTION_16G = 16.0/32768.0

ACCEL_LOW_PASS_FILTER_CUTOFF_460Hz = 0
ACCEL_LOW_PASS_FILTER_CUTOFF_184Hz = 1
ACCEL_LOW_PASS_FILTER_CUTOFF_92Hz = 2
ACCEL_LOW_PASS_FILTER_CUTOFF_41Hz = 3
ACCEL_LOW_PASS_FILTER_CUTOFF_20Hz = 4
ACCEL_LOW_PASS_FILTER_CUTOFF_10Hz = 5
ACCEL_LOW_PASS_FILTER_CUTOFF_5Hz = 6
# ACCEL_LOW_PASS_FILTER_CUTOFF_460Hz = 7

PASS_THROUGH_ON = 2
PASS_THROUGH_OFF = 0

SAMPLE_RATE = 50

gyroResolution = GYRO_RESOLUTION_2000_DPS
accelResolution = ACCEL_RESOUTION_2G

lastTimeAccelRead = 0
lastTimeGyroRead = 0
lastTimeReceivedRequestForContAccelMode = 0
lastTimeReceivedRequestForContGyroMode = 0

i2cBus = None

doReadGyro = False
doReadAccel = False
continuousModeGyro = False
continuousModeAccel = False


def bytesToInt(msb, lsb):
    if not msb & 0x80:
        return msb << 8 | lsb
    return - (((msb ^ 255) << 8) | (lsb ^ 255) + 1)


def dataConv(data1, data2):
    value = data1 | (data2 << 8)
    if value & (1 << 16 - 1):
        value -= (1 << 16)
    return value


def initMPU():
    global i2cBus
    i2cBus = smbus.SMBus(I2C_BUS)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x6B, 0x01)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x6B, 0x00)
    time.sleep(0.1)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x6B, 0x01)
    time.sleep(0.1)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x19, 0x04)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x1A, GYRO_LOW_PASS_FILTER_CUTOFF_41Hz)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x1A, GYRO_LOW_PASS_FILTER_CUTOFF_92Hz)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x1B, GYRO_RANGE_2000_DPS << 3)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x1C, ACCEL_RANGE_2G << 3)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x1D, ACCEL_LOW_PASS_FILTER_CUTOFF_41Hz)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x37, PASS_THROUGH_ON)


def readAccel():
    global lastTimeAccelRead

    data = i2cBus.read_i2c_block_data(I2C_ADDRESS, 0x3B, 6)
    x = dataConv(data[1], data[0])
    y = dataConv(data[3], data[2])
    z = dataConv(data[5], data[4])

    x = round(x * accelResolution, 3)
    y = round(y * accelResolution, 3)
    z = round(z * accelResolution, 3)

    now = time.time()
    elapsedTime = now - lastTimeAccelRead

    lastTimeAccelRead = now
    return x, y, z, elapsedTime


def readGyro():
    global lastTimeGyroRead

    data = i2cBus.read_i2c_block_data(I2C_ADDRESS, 0x43, 6)

    x = dataConv(data[1], data[0])
    y = dataConv(data[3], data[2])
    z = dataConv(data[5], data[4])

    x = round(x * gyroResolution, 3)
    y = round(y * gyroResolution, 3)
    z = round(z * gyroResolution, 3)

    now = time.time()
    elapsedTime = now - lastTimeGyroRead

    lastTimeGyroRead = now
    return x, y, z, elapsedTime


def handleReadAccel(topic, message, groups):
    global doReadAccel

    doReadAccel = True
    print("  Got request to start accel.")


def handleReadGyro(topic, message, groups):
    global doReadGyro

    doReadGyro = True
    print("  Got request to start gyro.")


def handleContinuousAccel(topic, message, groups):
    global doReadAccel, continuousModeAccel, lastTimeReceivedRequestForContAccelMode

    continuousModeAccel = True
    doReadAccel = True
    print("  Started continuous accel mode...")
    lastTimeReceivedRequestForContAccelMode = time.time()


def handleContinuousGyro(topic, message, groups):
    global doReadGyro, continuousModeGyro, lastTimeReceivedRequestForContGyroMode

    continuousModeGyro = True
    doReadGyro = True
    print("  Started continuous gyro mode...")
    lastTimeReceivedRequestForContGyroMode = time.time()


def loop():
    global doReadGyro, doReadAccel, lastTimeGyroRead, lastTimeAccelRead, continuousModeGyro, continuousModeAccel

    if doReadAccel:
        if time.time() - lastTimeAccelRead > MAX_TIMEOUT:
            accelData = readAccel()
            time.sleep(0.02)
        accelData = readAccel()

        pyroslib.publish("sensor/accel", str(accelData[0]) + "," + str(accelData[1]) + "," + str(accelData[2]) + "," + str(accelData[3]))

        if continuousModeAccel:
            if time.time() - lastTimeReceivedRequestForContAccelMode > CONTINUOUS_MODE_TIMEOUT:
                continuousModeAccel = False
                print("  Stopped continuous mode accel.")
        else:
            doReadAccel = False

    if doReadGyro:
        if time.time() - lastTimeGyroRead > MAX_TIMEOUT:
            gyroData = readGyro()
            time.sleep(0.02)
        gyroData = readGyro()

        pyroslib.publish("sensor/gyro", str(gyroData[0]) + "," + str(gyroData[1]) + "," + str(gyroData[2]) + "," + str(gyroData[3]))

        if continuousModeGyro:
            if time.time() - lastTimeReceivedRequestForContGyroMode > CONTINUOUS_MODE_TIMEOUT:
                continuousModeGyro = False
                print("  Stopped continuous mode gyro.")
        else:
            doReadGyro = False


if __name__ == "__main__":
    try:
        print("Starting 9dof sensor service...")

        initMPU()

        pyroslib.subscribe("sensor/accel/read", handleReadAccel)
        pyroslib.subscribe("sensor/accel/continuous", handleContinuousAccel)
        pyroslib.subscribe("sensor/gyro/read", handleReadGyro)
        pyroslib.subscribe("sensor/gyro/continuous", handleContinuousGyro)
        pyroslib.init("9dof-sensor-service")

        print("Started 9dof sensor service.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
