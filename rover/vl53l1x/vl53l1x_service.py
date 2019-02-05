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
import threading
import traceback

from GCC_VL53L1X import VL53L1X, VL53L1X_I2C

#
# vl53l1x service
#
#
# This service is responsible for reading 8 vl53l1x sensors.
#

DEBUG = False

I2C_BUS = 1
I2C_MULTIPLEXER_ADDRESS = 0x70
I2C_VL53L1X_ADDRESS_1 = 0x31
I2C_VL53L1X_ADDRESS_2 = 0x32
XSHUT_PIN = 4

i2cBus = smbus.SMBus(I2C_BUS)
vl53l1x_i2c = VL53L1X_I2C()

sensorsMap = { 1: {}, 2: {}, 4: {}, 8: {}}


def readSensor(i2c_address):
    try:
        i2cBus.write_byte(I2C_MULTIPLEXER_ADDRESS, i2c_address)

        sensor1 = sensorsMap[i2c_address]['vl53l1x_1']
        sensor2 = sensorsMap[i2c_address]['vl53l1x_2']

        # now = time.time()
        if sensor1.data_ready():
            # data_ready_time = time.time() - now
            measurement_data1 = sensor1.get_measurement_data()
            # measurement_time = time.time() - now
            d1 = measurement_data1.distance
            sensor1.clear_interrupt()
            sensorsMap[i2c_address]['d1'] = d1
            # print("data_ready_time " + str(data_ready_time) + " measurement_time " + str(measurement_time - data_ready_time) + " total " + str(measurement_time))
        else:
            # data_ready_time = time.time() - now
            # print("data_ready_time only " + str(data_ready_time))
            d1 = sensorsMap[i2c_address]['d1']

        if sensor2.data_ready():
            measurement_data2 = sensor2.get_measurement_data()
            d2 = measurement_data2.distance
            sensor2.clear_interrupt()
            sensorsMap[i2c_address]['d2'] = d2
        else:
            d2 = sensorsMap[i2c_address]['d2']

        return d1, d2

    except BaseException as e:
        if DEBUG:
            print("Failed to read sensor from i2c multiplexer address " + str(i2c_address) + ", " + str(e))

    return -1, -1


def readSensors():
    d270, d225 = readSensor(1)
    d0, d335 = readSensor(2)
    d90, d45 = readSensor(4)
    d180, d135 = readSensor(8)

    message = ",".join([str(f) for f in [time.time(), d0, d45, d90, d135, d180, d225, d270, d335]])
    pyroslib.publish("distance/deg", message)


def initDistanceSensors():

    # noinspection PyProtectedMember
    def switchBus(i2cAddress):
        try:
            i2cBus.write_byte(I2C_MULTIPLEXER_ADDRESS, i2cAddress)
            print("        switched bus to " + bin(i2cAddress))
        except BaseException as e:
            print("Cannot initialise distance sensors - i2c is not working; " + str(e))
            os._exit(1)

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

            sensor1 = VL53L1X(vl53l1x_i2c, initial_address=I2C_VL53L1X_ADDRESS_1, name="mux" + str(i2c_address) + '-s1')
        else:
            print("        " + str(i2c_address) + ": configuring first sensor to " + hex(I2C_VL53L1X_ADDRESS_1))
            sensor1 = VL53L1X(vl53l1x_i2c, required_address=I2C_VL53L1X_ADDRESS_1, name="mux" + str(i2c_address) + '-s1')

        sensor1.stop_ranging()
        sensor1.set_distance_mode(VL53L1X.SHORT)
        sensor1.set_timing_budget(8, 16)
        sensorsMap[i2c_address]['vl53l1x_1'] = sensor1

    if need_to_init_xshut:
        GPIO.output(XSHUT_PIN, GPIO.HIGH)
        time.sleep(0.002)
        for i2c_address in sensors:
            switchBus(i2c_address)

            print("        " + str(i2c_address) + ": configuring XSHUT sensor to " + hex(I2C_VL53L1X_ADDRESS_2))
            sensor2 = VL53L1X(vl53l1x_i2c, required_address=I2C_VL53L1X_ADDRESS_2, name="mux" + str(i2c_address) + '-s2')
            sensor2.stop_ranging()
            sensor2.set_distance_mode(VL53L1X.SHORT)
            sensor2.set_timing_budget(8, 16)
            sensorsMap[i2c_address]['vl53l1x_2'] = sensor2
    else:
        for i2c_address in sensors:
            switchBus(i2c_address)
            print("        configuring XSHUT sensor on " + hex(I2C_VL53L1X_ADDRESS_2))
            sensor2 = VL53L1X(vl53l1x_i2c, initial_address=I2C_VL53L1X_ADDRESS_2, name="mux" + str(i2c_address) + '-s2')
            sensor2.stop_ranging()
            sensor2.set_distance_mode(VL53L1X.SHORT)
            sensor2.set_timing_budget(8, 16)
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

        pyroslib.forever(0.02, readSensors)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
