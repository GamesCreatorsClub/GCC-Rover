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

i2c_bus = None

gyroCentre = 0
gyroMin = 0
gyroMax = 0

readGyro = False
continuousMode = False


def initGyro():
    global i2c_bus
    i2c_bus = smbus.SMBus(I2C_BUS)
    i2c_bus.write_byte_data(I2C_ADDRESS, 0x20, 0x0F)  # normal mode and all axes on to control reg1
    i2c_bus.write_byte_data(I2C_ADDRESS, 0x23, 0x20)  # full 2000dps to control reg4


def readGyroZ():
    global lastTimeGyroRead

    # print("        readGyroZ():")
    thisTimeGyroRead = time.time()

    # print("          reading first byte... ")
    i2c_bus.write_byte(I2C_ADDRESS, 0x2C)
    zl = i2c_bus.read_byte(I2C_ADDRESS)
    # print("          reading first byte - zl=" + str(zl))

    i2c_bus.write_byte(I2C_ADDRESS, 0x2D)
    zh = i2c_bus.read_byte(I2C_ADDRESS)
    # print("          reading second byte - zh=" + str(zh))

    zValue = zh << 8 | zl
    if zValue & (1 << 15):
        zValue |= ~65535
    else:
        zValue &= 65535

    degreesPerSecond = zValue * 70.00 / 1000
    degrees = degreesPerSecond * (lastTimeGyroRead - thisTimeGyroRead)

    # degrees = degreesPerSecond

    # print("          done: z=" + str(z) + " degrees=" + str(degrees) + " dps=" + str(degreesPerSecond) + " time=" + str(lastTimeGyroRead - thisTimeGyroRead))

    lastTimeGyroRead = thisTimeGyroRead

    return degrees


def calibrateGyro():
    global gyroCentre, gyroMin, gyroMax

    c = 0
    avg = 0

    minZ = readGyroZ()
    maxZ = readGyroZ()
    while c < 50:
        zValue = readGyroZ()

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
    global readGyro

    readGyro = True
    print("  Got request to start gyro.")


def handleContinuous(topic, message, groups):
    global readGyro, continuousMode, lastTimeReceivedRequestForContMode

    continuousMode = True
    readGyro = True
    print("  Started continuous mode...")
    lastTimeReceivedRequestForContMode = time.time()


def loop():
    global readGyro, lastTimeGyroRead, continuousMode

    if readGyro:
        if time.time() - lastTimeGyroRead > MAX_GYRO_TIMEOUT:
            z = readGyroZ()
            time.sleep(0.02)
        z = readGyroZ()

        pyroslib.publish("sensor/gyro", str(z))

        if continuousMode:
            if time.time() - lastTimeReceivedRequestForContMode > CONTINUOUS_MODE_TIMEOUT:
                continuousMode = False
                print("  Stopped continuous mode.")
        else:
            readGyro = False


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
