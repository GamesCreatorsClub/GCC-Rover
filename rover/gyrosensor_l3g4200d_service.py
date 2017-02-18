#!/usr/bin/python3

import time
import traceback
import smbus
import pyroslib


CONTINUOUS_MODE_TIMEOUT = 5  # 5 seconds before giving up on sending gyro data out
MAX_GYRO_TIMEOUT = 0.05  # 0.02 is 50 times a second so this is 50% longer

I2C_BUS = 1
I2C_ADDRESS = 0x69

lastTimeGyroRead = 0
lastTimeReceivedRequestForContMode = 0

i2cBus = None

gyroCentre = 0
gyroMin = 0
gyroMax = 0

doReadGyro = False
continuousMode = False


def initGyro():
    global i2cBus
    i2cBus = smbus.SMBus(I2C_BUS)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x20, 0x0F)  # normal mode and all axes on to control reg1
    i2cBus.write_byte_data(I2C_ADDRESS, 0x23, 0x20)  # full 2000dps to control reg4


def readGyro():
    global lastTimeGyroRead

    thisTimeGyroRead = time.time()

    i2cBus.write_byte(I2C_ADDRESS, 0x2C)
    zl = i2cBus.read_byte(I2C_ADDRESS)

    i2cBus.write_byte(I2C_ADDRESS, 0x2D)
    zh = i2cBus.read_byte(I2C_ADDRESS)

    z = zh << 8 | zl
    if z & (1 << 15):
        z |= ~65535
    else:
        z &= 65535

    degreesPerSecond = z * 70.00 / 1000
    degrees = degreesPerSecond * (lastTimeGyroRead - thisTimeGyroRead)

    # degrees = degreesPerSecond
    # print("          done: z=" + str(z) + " degrees=" + str(degrees) + " dps=" + str(degreesPerSecond) + " time=" + str(lastTimeGyroRead - thisTimeGyroRead))
    elapsedTime = thisTimeGyroRead - lastTimeGyroRead
    lastTimeGyroRead = thisTimeGyroRead

    return 0, 0, degrees, elapsedTime


def calibrateGyro():
    global gyroCentre, gyroMin, gyroMax

    c = 0
    avg = 0

    minZ = readGyro()[2]
    maxZ = readGyro()[2]
    while c < 50:
        zValue = readGyro()[2]

        avg += zValue

        c += 1
        if zValue > maxZ:
            maxZ = zValue
        if zValue < minZ:
            minZ = zValue

        time.sleep(0.02)

    gyroCentre = avg / 50.0
    gyroMin = minZ
    gyroMax = maxZ


def handleRead(topic, message, groups):
    global doReadGyro

    doReadGyro = True
    print("  Got request to start gyro.")


def handleContinuous(topic, message, groups):
    global doReadGyro, continuousMode, lastTimeReceivedRequestForContMode

    continuousMode = True
    doReadGyro = True
    print("  Started continuous mode...")
    lastTimeReceivedRequestForContMode = time.time()


def loop():
    global doReadGyro, lastTimeGyroRead, continuousMode

    if readGyro:
        if time.time() - lastTimeGyroRead > MAX_GYRO_TIMEOUT:
            readGyro()
            time.sleep(0.02)
        gyroData = readGyro()

        pyroslib.publish("sensor/gyro", str(gyroData[0]) + "," + str(gyroData[1]) + "," + str(gyroData[2]) + "," + str(gyroData[3]))

        if continuousMode:
            if time.time() - lastTimeReceivedRequestForContMode > CONTINUOUS_MODE_TIMEOUT:
                continuousMode = False
                print("  Stopped continuous mode.")
        else:
            doReadGyro = False


if __name__ == "__main__":
    try:
        print("Starting gyro sensor service...")

        initGyro()

        calibrateGyro()

        print("  Calibrated gyro offset=" + str(gyroCentre) + " min=" + str(gyroMin) + " max=" + str(gyroMax))

        pyroslib.subscribe("sensor/gyro/read", handleRead)
        pyroslib.subscribe("sensor/gyro/continuous", handleContinuous)
        pyroslib.init("gyro-sensor-service")

        print("Started gyro sensor service.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
