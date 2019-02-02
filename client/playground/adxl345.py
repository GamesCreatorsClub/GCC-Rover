# ADXL345 Python library for Raspberry Pi
#
# author:  Jonathan Williamson
# license: BSD, see LICENSE.txt included in this package
#
# This is a Raspberry Pi Python implementation to help you get started with
# the Adafruit Triple Axis ADXL345 breakout board:
# http://shop.pimoroni.com/products/adafruit-triple-axis-accelerometer

import smbus
import time
import paho.mqtt.client as mqtt
import sys

bus = smbus.SMBus(1)

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


class ADXL345:
    address = None

    def __init__(self, address=0x53):
        self.address = address
        self.setBandwidthRate(BW_RATE_50HZ)
        self.setRange(RANGE_2G)
        self.enableMeasurement()

    def enableMeasurement(self):
        bus.write_byte_data(self.address, POWER_CTL, MEASURE)

    def setBandwidthRate(self, rate_flag):
        bus.write_byte_data(self.address, BW_RATE, rate_flag)

    # set the measurement range for 10-bit readings
    def setRange(self, range_flag):
        value = bus.read_byte_data(self.address, DATA_FORMAT)

        value &= ~0x0F
        value |= range_flag
        value |= 0x08

        bus.write_byte_data(self.address, DATA_FORMAT, value)

    # returns the current reading from the sensor for each axis
    #
    # parameter gforce:
    #    False (default): result is returned in m/s^2
    #    True           : result is returned in gs
    def getAxes(self, gforce=False):
        bytes = bus.read_i2c_block_data(self.address, AXES_DATA, 6)

        x = bytes[0] | (bytes[1] << 8)
        if x & (1 << 16 - 1):
            x = x - (1 << 16)

        y = bytes[2] | (bytes[3] << 8)
        if y & (1 << 16 - 1):
            y = y - (1 << 16)

        z = bytes[4] | (bytes[5] << 8)
        if z & (1 << 16 - 1):
            z = z - (1 << 16)

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

        return {"x": x, "y": y, "z": z}


client = mqtt.Client("Accelerometer")
client.connect("localhost", 1883, 60)


adxl345 = ADXL345()

c = 0
posY = 0.0
oldVY = 0.0

avgAccY = 0.0
avgVelY = 0.0

print("Starting...")
print(" Collecting offset...")
while c < 100:
    axes = adxl345.getAxes(False)
    accY = axes["y"]
    avgAccY = avgAccY + accY
    c += 1
    time.sleep(0.02)

offsetY = avgAccY / 100.0
offsetY = round(offsetY, 4)

print("  Initial offset is " + str(offsetY))

print("Started.")

accYs = []
c = 0
while True:
    c += 1

    axes = adxl345.getAxes(False)
    # accY = axes["y"] - offsetY
    accY = axes["y"]
    avgAccY = avgAccY + accY

    newVY = 0.04 * accY + oldVY
    # print("Acc=" + str(accY) + ", newVY=" + str(newVY))

    avgVY = (oldVY + newVY) / 2.0
    avgVelY = avgVelY + avgVY

    newPY = posY + 0.04 * avgVY

    posY = newPY
    oldVY = newVY

    if c >= 50:
        c = 0
        print("y = " + str(round(posY, 4)) + ", avg acc: " + str(round((avgAccY / 25.0))) + ", avg vel: " + str(round((avgVelY / 25.0))))

    if len(accYs) > 3000:
        client.publish("accel/log", "\n".join(accYs))
        del accYs[:]
    else:
        accYs.append(str(accY))
        sys.exit(0)

    avgAccY = 0

    time.sleep(0.02)