#!/usr/bin/env python3

#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import RPi.GPIO as GPIO

import os
import pyroslib
import smbus
import time
import traceback

from GCC_VL53L1X import VL53L1X, VL53L1X_I2C, UserRoi

#
# vl53l1x service
#
#
# This service is responsible for reading 8 vl53l1x sensors.
#

DEBUG = False

TIMING_BUDGET = 16
INTERMEDIATE_PERIOD = TIMING_BUDGET + 5
# TIMING_BUDGET = 8.5
# INTERMEDIATE_PERIOD = 12

ROI_TOP = 0
ROI_BOTTOM = 5
ROI_LEFT = 0
ROI_RIGHT = 15


I2C_BUS = 1
I2C_MULTIPLEXER_ADDRESS = 0x70
I2C_VL53L1X_ADDRESS_1 = 0x31
I2C_VL53L1X_ADDRESS_2 = 0x32
XSHUT_PIN = 4

i2cBus = smbus.SMBus(I2C_BUS)
vl53l1x_i2c = VL53L1X_I2C()

sensorsMap = {
    1: {'s1_name': 'left', 's2_name': 'back_left'},
    2: {'s1_name': 'forward', 's2_mame': 'forward_right'},
    4: {'s1_mame': 'right', 's2_name': 'forward_right'},
    8: {'s1_name': 'back', 's2_name': 'back_right'}
}


# noinspection PyTypeChecker
def readSensors(i2c_address):

    def readOneSensor(sensor: VL53L1X, sensor_id):
        if sensor.data_ready():
            measurement_data = sensor.get_measurement_data()
            sensor.clear_interrupt()

            if measurement_data.is_valid:
                sensorsMap[i2c_address][sensor_id] = measurement_data.distance
            else:
                print("Measurement error " + sensor.name + ": " + measurement_data.get_range_status_description() + " d=" + str(measurement_data.distance))
                if measurement_data.distance > 0:
                    sensorsMap[i2c_address][sensor_id] = measurement_data.distance
                return measurement_data.distance

        return sensorsMap[i2c_address][sensor_id]

    try:
        i2cBus.write_byte(I2C_MULTIPLEXER_ADDRESS, i2c_address)

        d1 = readOneSensor(sensorsMap[i2c_address]['vl53l1x_1'], 'd1')
        d2 = readOneSensor(sensorsMap[i2c_address]['vl53l1x_2'], 'd2')

        return d1, d2

    except BaseException as e:
        if DEBUG:
            print("Failed to read sensor from i2c multiplexer address " + str(i2c_address) + ", " + str(e))

    return -1, -1


def readAllSensors():
    d270, d225 = readSensors(1)
    d0, d335 = readSensors(2)
    d90, d45 = readSensors(4)
    d180, d135 = readSensors(8)

    message = ",".join([str(f) for f in [time.time(), d0, d45, d90, d135, d180, d225, d270, d335]])
    pyroslib.publish("distance/deg", message)


# noinspection PyTypeChecker
def initDistanceSensors():

    # noinspection PyProtectedMember
    def switchBus(i2cAddress):
        try:
            i2cBus.write_byte(I2C_MULTIPLEXER_ADDRESS, i2cAddress)
            print("        switched bus to " + bin(i2cAddress))
        except BaseException as e:
            print("Cannot initialise distance sensors - i2c is not working; " + str(e))
            os._exit(1)

    def configureSensor(sensor):
        sensor.stop_ranging()
        sensor.set_distance_mode(VL53L1X.SHORT)
        sensor.set_timing_budget(TIMING_BUDGET, INTERMEDIATE_PERIOD)
        sensor.set_region_of_interest(UserRoi(ROI_TOP, ROI_RIGHT, ROI_BOTTOM, ROI_LEFT))

    vl53l1x_i2c.open()

    GPIO.setup(XSHUT_PIN, GPIO.OUT)
    GPIO.output(XSHUT_PIN, GPIO.HIGH)

    need_to_init_xshut = False
    sensors = [1, 2, 4, 8]
    i = 0
    while i < len(sensors) and not need_to_init_xshut:
        i2c_address = sensors[i]
        switchBus(i2c_address)
        if not vl53l1x_i2c.is_device_at(I2C_VL53L1X_ADDRESS_2):
            print("        " + str(i2c_address) + ": not present on " + hex(I2C_VL53L1X_ADDRESS_2))
            need_to_init_xshut = True
        else:
            print("        " + str(i2c_address) + ": present on " + hex(I2C_VL53L1X_ADDRESS_2))

        i += 1

    if need_to_init_xshut:
        print("        Need to configure XSHUT sensors")
        GPIO.output(XSHUT_PIN, GPIO.LOW)
    else:
        print("        All XSHUT sensors already configured")

    for i2c_address in sensors:
        switchBus(i2c_address)

        if vl53l1x_i2c.is_device_at(I2C_VL53L1X_ADDRESS_1):
            print("        " + str(i2c_address) + ": first sensor already present on " + hex(I2C_VL53L1X_ADDRESS_1))

            sensor1 = VL53L1X(vl53l1x_i2c, initial_address=I2C_VL53L1X_ADDRESS_1, name=sensorsMap[i2c_address]['s1_mame'])
        else:
            print("        " + str(i2c_address) + ": configuring first sensor to " + hex(I2C_VL53L1X_ADDRESS_1))
            sensor1 = VL53L1X(vl53l1x_i2c, required_address=I2C_VL53L1X_ADDRESS_1, name=sensorsMap[i2c_address]['s1_mame'])

        configureSensor(sensor1)
        sensorsMap[i2c_address]['vl53l1x_1'] = sensor1

    if need_to_init_xshut:
        GPIO.output(XSHUT_PIN, GPIO.HIGH)
        time.sleep(0.002)
        for i2c_address in sensors:
            switchBus(i2c_address)

            print("        " + str(i2c_address) + ": configuring XSHUT sensor to " + hex(I2C_VL53L1X_ADDRESS_2))
            sensor2 = VL53L1X(vl53l1x_i2c, required_address=I2C_VL53L1X_ADDRESS_2, name=sensorsMap[i2c_address]['s2_mame'])
            configureSensor(sensor2)
            sensorsMap[i2c_address]['vl53l1x_2'] = sensor2
    else:
        for i2c_address in sensors:
            switchBus(i2c_address)
            print("        configuring XSHUT sensor on " + hex(I2C_VL53L1X_ADDRESS_2))
            sensor2 = VL53L1X(vl53l1x_i2c, initial_address=I2C_VL53L1X_ADDRESS_2, name=sensorsMap[i2c_address]['s2_mame'])
            configureSensor(sensor2)
            sensorsMap[i2c_address]['vl53l1x_2'] = sensor2

    for i2c_address in sensors:
        switchBus(i2c_address)
        print("        " + str(i2c_address) + ": starting ranging for both sensors")
        sensor1 = sensorsMap[i2c_address]['vl53l1x_1']
        sensor2 = sensorsMap[i2c_address]['vl53l1x_2']
        sensor1.start_ranging()
        sensor2.start_ranging()
        sensorsMap[i2c_address]['d1'] = -1
        sensorsMap[i2c_address]['d2'] = -1


if __name__ == "__main__":
    try:
        print("Starting vl53l1x service...")
        print("    initialising wheels...")

        print("    setting GPIOs...")
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        print("    sbscribing to topics...")
        pyroslib.init("vl53l1x-service", unique=True)

        print("  Loading storage details...")

        print("  Initialising distance sensors...")
        initDistanceSensors()
        print("  Distance sensors initiated")

        print("Started vl53l1x service.")

        pyroslib.forever(0.02, readAllSensors)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
