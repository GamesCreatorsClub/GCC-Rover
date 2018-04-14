#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import time
import traceback
import smbus
import pyroslib
import math

#
# MPU 9250 sensor service
#
# Based on https://github.com/FaBoPlatform/FaBo9AXIS-MPU9250-Python/blob/master/FaBo9Axis_MPU9250/MPU9250.py
#
# This service is responsible reading gyroscope and accelerometer.
#

# also http://ozzmaker.com/guide-to-interfacing-a-gyro-and-accelerometer-with-a-raspberry-pi/
# https://github.com/micropython-IMU/micropython-mpu9x50/blob/master/mpu9250.py


DEBUG = True

CONTINUOUS_MODE_TIMEOUT = 5  # 5 seconds before giving up on sending accel data out
MAX_TIMEOUT = 0.05  # 0.02 is 50 times a second so this is 50% longer

I2C_BUS = 1
I2C_ADDRESS = 0x68
AK8963_ADDRESS = 0x0C

EARTH_GRAVITY_MS2 = 9.80665

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
AXES = ["x", "y", "z"]

gyroResolution = GYRO_RESOLUTION_250_DPS
accelResolution = ACCEL_RESOUTION_2G

gyroResolutionRecp = 1.0/GYRO_RESOLUTION_250_DPS
accelResolutionRecp = 1.0/ACCEL_RESOUTION_2G


lastTimeAccelRead = 0
lastTimeGyroRead = 0
lastTimeReceivedRequestForContAccelMode = 0
lastTimeReceivedRequestForContGyroMode = 0

i2cBus = None

doReadGyro = False
doReadAccel = False
continuousModeGyro = False
continuousModeGyroCalibrate = False
continuousModeAccel = False
continuousModeAccelCalibrate = False

gyroCalibrationDataPoints = 0
gyroCalibrationReadots = []

accelCalibrationDataPoints = 0
accelCalibrationReadots = []

gyroCalibrationData = [{"offset": 0.0}, {"offset": 0.0}, {"offset": 0.0}]
accelCalibrationData = [{"offset": 0.0}, {"offset": 0.0}, {"offset": 0.0}]


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
    global magXcoef, magYcoef, magZcoef
    i2cBus = smbus.SMBus(I2C_BUS)
    # i2cBus.write_byte_data(I2C_ADDRESS, 0x6B, 0x01)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x6B, 0x00)
    time.sleep(0.1)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x6B, 0x01)
    time.sleep(0.1)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x1A, GYRO_LOW_PASS_FILTER_CUTOFF_41Hz)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x19, 0x04)

    # i2cBus.write_byte_data(I2C_ADDRESS, 0x1A, GYRO_LOW_PASS_FILTER_CUTOFF_92Hz)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x1B, GYRO_RANGE_250_DPS << 3)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x1C, ACCEL_RANGE_2G << 3)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x1D, ACCEL_LOW_PASS_FILTER_CUTOFF_41Hz)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x37, PASS_THROUGH_ON)

    time.sleep(0.1)

    # AK8963_ADDRESS

    i2cBus.write_byte_data(AK8963_ADDRESS, 0x0A, 0x00)
    time.sleep(0.1)

    i2cBus.write_byte_data(AK8963_ADDRESS, 0x0A, 0x0F)  # fuse ROM access mode
    time.sleep(0.1)

    # Correction values
    data = i2cBus.read_i2c_block_data(AK8963_ADDRESS, 0x10, 3)

    magXcoef = (data[0] - 128) / 256.0 + 1.0
    magYcoef = (data[1] - 128) / 256.0 + 1.0
    magZcoef = (data[2] - 128) / 256.0 + 1.0
    if DEBUG:
        print(str(float(magXcoef))+", "+str(float(magYcoef))+" ,"+str(float(magZcoef)))

    time.sleep(0.1)

    i2cBus.write_byte_data(AK8963_ADDRESS, 0x0A, 0x00)  # Power down mode (AK8963 manual 6.4.6)
    time.sleep(0.1)

    i2cBus.write_byte_data(AK8963_ADDRESS, 0x0A, 0x16)  # 16 bit (0.15uT/LSB not 0.015), mode 2 : 100Hz
    # i2cBus.write_byte_data(AK8963_ADDRESS, 0x0A, 0x12)  # 16 bit (0.15uT/LSB not 0.015), mode 1 :8Hz
    time.sleep(0.1)


def readAccel():
    global lastTimeAccelRead

    data = i2cBus.read_i2c_block_data(I2C_ADDRESS, 0x3B, 6)

    now = time.time()
    deltaTime = now - lastTimeAccelRead

    x = dataConv(data[1], data[0])
    y = dataConv(data[3], data[2])
    z = dataConv(data[5], data[4])

    x = round(x * accelResolution * EARTH_GRAVITY_MS2, 3)
    y = round(y * accelResolution * EARTH_GRAVITY_MS2, 3)
    z = round(z * accelResolution * EARTH_GRAVITY_MS2, 3)

    # x = x * accelResolution * EARTH_GRAVITY_MS2
    # y = y * accelResolution * EARTH_GRAVITY_MS2
    # z = z * accelResolution * EARTH_GRAVITY_MS2

    AccXangle = math.degrees(math.atan2(y, z) + math.pi)
    AccYangle = math.degrees(math.atan2(z, x) + math.pi)
    AccZangle = math.degrees(math.atan2(x, y) + math.pi)

    lastTimeAccelRead = now
    return x, y, z, deltaTime, AccXangle, AccYangle, AccZangle


def readGyro():
    global lastTimeGyroRead

    data = i2cBus.read_i2c_block_data(I2C_ADDRESS, 0x43, 6)

    now = time.time()
    deltaTime = now - lastTimeGyroRead

    x = dataConv(data[1], data[0])
    y = dataConv(data[3], data[2])
    z = dataConv(data[5], data[4])

    # x = round(x * gyroResolution, 3) * deltaTime
    # y = round(y * gyroResolution, 3) * deltaTime
    # z = round(z * gyroResolution, 3) * deltaTime

    x = deltaTime * x / gyroResolutionRecp
    y = deltaTime * y / gyroResolutionRecp
    z = deltaTime * z / gyroResolutionRecp

    lastTimeGyroRead = now

    return x, y, -z, deltaTime


def readMagno():
    global magXcoef, magYcoef, magZcoef

    x = 0
    y = 0
    z = 0

    # check data ready
    drdy = i2cBus.read_byte_data(AK8963_ADDRESS, 0x02)  # increments mag_stale_count - AK8963_ST1
    if drdy & 0x01:
        data = i2cBus.read_i2c_block_data(AK8963_ADDRESS, 0x03, 7)  # AK8963_MAGNET_OUT
        # dataX = i2cBus.read_byte_data(AK8963_ADDRESS, 0x09) # ST2
        # check overflow
        if (data[6] & 0x08) != 0x08:
            print("raw data "+ ' '.join(str(x) for x in data), end="\t")
            x = dataConv(data[0], data[1])
            y = dataConv(data[2], data[3])
            z = dataConv(data[4], data[5])

            scale = 0.15  # scale is 0.15uT/LSB

            x = round(x * scale * magXcoef, 3)
            y = round(y * scale * magYcoef, 3)
            z = round(z * scale * magZcoef, 3)

    return x,y,z


def initialCalibrate():
    global gyroCalibrationReadots, accelCalibrationReadots

    del gyroCalibrationReadots[:]
    del accelCalibrationReadots[:]

    readGyro()
    readAccel()
    time.sleep(0.02)

    c = 0
    while c < 50:
        gyroData = readGyro()
        gyroCalibrationReadots.append(gyroData)

        accelData = readAccel()
        accelCalibrationReadots.append(accelData)
        c += 1

    calcGyroCalibrationData()
    calcAccelCalibrationData()


def calcGyroCalibrationData():

    minV = [1000, 1000, 1000]
    maxV = [-1000, -1000, -1000]
    avg = [0, 0, 0]

    if DEBUG:
        print("    Calibrating with " + str(len(gyroCalibrationReadots)) + " data points")

    c = 0
    for data in gyroCalibrationReadots:

        for i in range(0, 3):
            if data[i] < minV[i]:
                minV[i] = data[i]
            if data[i] > maxV[i]:
                maxV[i] = data[i]
            avg[i] += data[i]
            # avg[i] += (minV[i]+maxV[i])/2

        c += 1
        time.sleep(0.02)

    if DEBUG:
        print("    Finished calibration for gyro " + str(c) + " data points")
    for i in range(0, 3):
        gyroCalibrationData[i] = {
            "offset": avg[i] / c,
            "min": minV[i],
            "max": maxV[i]
        }
        if DEBUG:
            print("    Calibrated gyro axis " + AXES[i] + " offset,min,max as " + str(gyroCalibrationData[i]["offset"]) + ", " + str(gyroCalibrationData[i]["min"]) + ", " + str(gyroCalibrationData[i]["max"]))


def calcAccelCalibrationData():

    minV = [1000, 1000, 1000]
    maxV = [-1000, -1000, -1000]
    avg = [0, 0, 0]

    c = 0
    for data in accelCalibrationReadots:

        for i in range(0, 3):
            if data[i] < minV[i]:
                minV[i] = data[i]
            if data[i] > maxV[i]:
                maxV[i] = data[i]
            avg[i] += data[i]
            # avg[i] += (minV[i]+maxV[i])/2

        c += 1
        time.sleep(0.02)

    if DEBUG:
        print("    Finished calibration for accel " + str(c) + " data points")
    for i in range(0, 3):
        accelCalibrationData[i] = {
            "offset": avg[i] / c,
            "min": minV[i],
            "max": maxV[i]
        }
        if DEBUG:
            print("    Calibrated accel axis " + AXES[i] + " offset as " + str(accelCalibrationData[i]["offset"]))


def handleReadAccel(topic, message, groups):
    global doReadAccel

    doReadAccel = True
    if DEBUG:
        print("  Got request to start accel.")


def handleReadGyro(topic, message, groups):
    global doReadGyro

    doReadGyro = True
    if DEBUG:
        print("  Got request to start gyro.")


def handleContinuousAccel(topic, message, groups):
    global doReadAccel, continuousModeAccel, continuousModeAccelCalibrate, accelCalibrationDataPoints, lastTimeReceivedRequestForContAccelMode

    if message.startswith("calibrate"):
        if continuousModeAccel:
            continuousModeAccel = False

        if not continuousModeAccelCalibrate:
            continuousModeAccelCalibrate = True
            doReadAccel = True

            if DEBUG:
                print("  Started freewheel accel calibration...")
            split = message.split(",")
            if len(split) > 1:
                accelCalibrationDataPoints = int(split[1])
            accelCalibrationReadots.clear()
    elif message.startswith("stop"):
        continuousModeAccel = False
        doReadAccel = False

        if continuousModeAccelCalibrate:
            calcAccelCalibrationData()
            continuousModeAccelCalibrate = False

    else:
        if continuousModeAccelCalibrate:
            calcAccelCalibrationData()
            continuousModeAccelCalibrate = False

        if not continuousModeAccel:
            continuousModeAccel = True
            doReadAccel = True
            if DEBUG:
                print("  Started continuous accel mode...")

    lastTimeReceivedRequestForContAccelMode = time.time()


def handleContinuousGyro(topic, message, groups):
    global doReadGyro, continuousModeGyro, continuousModeGyroCalibrate, gyroCalibrationDataPoints, lastTimeReceivedRequestForContGyroMode

    if message.startswith("calibrate"):
        if continuousModeGyro:
            continuousModeGyro = False

        if not continuousModeGyroCalibrate:
            continuousModeGyroCalibrate = True
            doReadGyro = True

            if DEBUG:
                print("  Started freewheel calibration...")
            split = message.split(",")
            if len(split) > 1:
                gyroCalibrationDataPoints = int(split[1])
            gyroCalibrationReadots.clear()
    elif message.startswith("stop"):
        continuousModeGyro = False
        doReadGyro = False

        if continuousModeGyroCalibrate:
            calcGyroCalibrationData()
            continuousModeGyroCalibrate = False

    else:
        if continuousModeGyroCalibrate:
            calcGyroCalibrationData()
            continuousModeGyroCalibrate = False

        if not continuousModeGyro:
            continuousModeGyro = True
            doReadGyro = True
            if DEBUG:
                print("  Started continuous gyro mode...")

    lastTimeReceivedRequestForContGyroMode = time.time()


def loop():
    global doReadGyro, doReadAccel, lastTimeGyroRead, lastTimeAccelRead
    global continuousModeGyro, continuousModeGyroCalibrate, continuousModeAccel, continuousModeAccelCalibrate
    global data

    if DEBUG:
        rawData = readMagno()
        if rawData[0] != 0:
            print("magno data "+ str(rawData[0]) + ", "+ str(rawData[1]) + ", "+ str(rawData[2]), end="\t")
            print("heading "+ str(180 * math.atan2(rawData[2], rawData[1])/math.pi) )

    if doReadAccel:
        if time.time() - lastTimeAccelRead > MAX_TIMEOUT:
            rawData = readAccel()
            time.sleep(0.02)

        rawData = readAccel()
        data = []
        for i in range(0, 3):
            data.append(rawData[i] - accelCalibrationData[i]["offset"])
        data += rawData[3:]

        # if DEBUG:
        #     print("accel XY data "+ str(data[4]) + ", "+ str(data[5]) + ", "+ str(data[6]))

        pyroslib.publish("sensor/accel", str(data[0]) + "," + str(data[1]) + "," + str(data[2]) + "," + str(data[3]) + "," + str(data[4]) + "," + str(data[5]) + "," + str(data[6]))


        if continuousModeAccelCalibrate:
            accelCalibrationReadots.append(rawData)

            if len(accelCalibrationReadots) > accelCalibrationDataPoints:
                del accelCalibrationReadots[0]

            if time.time() - lastTimeReceivedRequestForContAccelMode > CONTINUOUS_MODE_TIMEOUT:
                continuousModeAccelCalibrate = False
                if DEBUG:
                    print("  Stopped continuous mode calibration.")
        elif continuousModeAccel:
            if time.time() - lastTimeReceivedRequestForContAccelMode > CONTINUOUS_MODE_TIMEOUT:
                continuousModeAccel = False
                if DEBUG:
                    print("  Stopped continuous mode accel.")
        else:
            doReadAccel = False

    if doReadGyro:
        if time.time() - lastTimeGyroRead > MAX_TIMEOUT:
            rawData = readGyro()
            time.sleep(0.02)

        rawData = readGyro()
        data = []
        for i in range(0, 3):
            data.append(rawData[i] - gyroCalibrationData[i]["offset"])
        data.append(rawData[3])

        pyroslib.publish("sensor/gyro", str(data[0]) + "," + str(data[1]) + "," + str(data[2]) + "," + str(data[3]))
        # if DEBUG:
        #     print("gyro Z data "+ str(data[2]) + ", "+ str(gyroCalibrationData[2]["min"]) + ", "+ str(gyroCalibrationData[2]["max"]))

        if continuousModeGyroCalibrate:
            gyroCalibrationReadots.append(rawData)

            if len(gyroCalibrationReadots) > gyroCalibrationDataPoints:
                del gyroCalibrationReadots[0]

            if time.time() - lastTimeReceivedRequestForContGyroMode > CONTINUOUS_MODE_TIMEOUT:
                continuousModeGyroCalibrate = False
                if DEBUG:
                    print("  Stopped continuous mode calibration.")
        elif continuousModeGyro:
            if time.time() - lastTimeReceivedRequestForContGyroMode > CONTINUOUS_MODE_TIMEOUT:
                continuousModeGyro = False
                if DEBUG:
                    print("  Stopped continuous mode gyro.")
        else:
            doReadGyro = False


if __name__ == "__main__":
    try:
        print("Starting 9dof sensor service...")

        initMPU()

        initialCalibrate()

        pyroslib.subscribe("sensor/accel/read", handleReadAccel)
        pyroslib.subscribe("sensor/accel/continuous", handleContinuousAccel)
        pyroslib.subscribe("sensor/gyro/read", handleReadGyro)
        pyroslib.subscribe("sensor/gyro/continuous", handleContinuousGyro)
        pyroslib.init("9dof-sensor-service")

        print("Started 9dof sensor service.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
