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

# TIMING_BUDGET = 16
# INTERMEDIATE_PERIOD = TIMING_BUDGET + 5
# TIMING_BUDGET = 16.5
# INTERMEDIATE_PERIOD = 20
# TIMING_BUDGET = 30
# INTERMEDIATE_PERIOD = 34
# TIMING_BUDGET = 8.5
# INTERMEDIATE_PERIOD = 12

# TIMING_BUDGET = 16.5
# INTERMEDIATE_PERIOD = 21.5
# DISTANCE_MODE = VL53L1X.MEDIUM

TIMING_BUDGET = 8.5
INTERMEDIATE_PERIOD = 12
DISTANCE_MODE = VL53L1X.SHORT

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

SENSORS_ORDER = [90, 45, 180, 135, 270, 225, 0, 315]

sensors = [s for s in SENSORS_ORDER]

sensorsMap = {
    0: {'bus': 2, 'i2c': I2C_VL53L1X_ADDRESS_1, 'name': 'forward', 'adjust': 83, 'vl53l1x': None},
    45: {'bus': 4, 'i2c': I2C_VL53L1X_ADDRESS_2, 'name': 'forward_right', 'adjust': 121, 'vl53l1x': None},
    90: {'bus': 4, 'i2c': I2C_VL53L1X_ADDRESS_1, 'name': 'right', 'adjust': 83, 'vl53l1x': None},
    135: {'bus': 8, 'i2c': I2C_VL53L1X_ADDRESS_2, 'name': 'back_right', 'adjust': 121, 'vl53l1x': None},
    180: {'bus': 8, 'i2c': I2C_VL53L1X_ADDRESS_1, 'name': 'back', 'adjust': 83, 'vl53l1x': None},
    225: {'bus': 1, 'i2c': I2C_VL53L1X_ADDRESS_2, 'name': 'back_left', 'adjust': 121, 'vl53l1x': None},
    270: {'bus': 1, 'i2c': I2C_VL53L1X_ADDRESS_1, 'name': 'left', 'adjust': 83, 'vl53l1x': None},
    315: {'bus': 2, 'i2c': I2C_VL53L1X_ADDRESS_2, 'name': 'forward_right', 'adjust': 121, 'vl53l1x': None}
}

_angle_to_status_position = {0: 0, 45: 1, 90: 2, 135: 3, 180: 4, 225: 5, 270: 6, 315: 7}
radar = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0, 'timestamp': 0.0, 'status': '0000000000000000'}

paused = True


def _switchBus(i2cAddress):
    try:
        i2cBus.write_byte(I2C_MULTIPLEXER_ADDRESS, i2cAddress)
        # print("        switched bus to " + bin(i2cAddress))
    except BaseException as e:
        print("Cannot initialise distance sensors - i2c is not working; " + str(e))
        os._exit(1)


# noinspection PyTypeChecker
def readSensor(angle):
    global i2c_error_detected

    i2c_error_detected = False

    def updateStatus(sensor_angle, status_value):
        global i2c_error_detected
        if status_value == -1 or status_value == 255:
            i2c_error_detected = True

        index = _angle_to_status_position[sensor_angle] * 2
        status_str = hex(status_value)[2:]
        if len(status_str) < 2:
            status_str = "0" + status_str

        old_status_str = radar['status']
        old_status_str = old_status_str[:index] + status_str + old_status_str[index + 2:]
        # print("Replaced status old=" + radar['status'] + " new=" + old_status_str + " index=" + str(index))
        radar['status'] = old_status_str

    def adjustDistance(angle):
        if int(angle) % 90 == 0:
            return 53  # ?! it was supposed to be 83
        else:
            return 91  # ?! it was supposed to be 121

    try:
        sensor = sensorsMap[angle]['vl53l1x']
        adjusted_distance = sensorsMap[angle]['adjust']
        # print(str(time.time()) + " -> " + str(sensor_angle) + ": 1")
        if sensor.data_ready():
            # print(str(time.time()) + " -> " + str(sensor_angle) + ": 2")
            measurement_data = sensor.get_measurement_data()
            # print(str(time.time()) + " -> " + str(sensor_angle) + ": 3")
            sensor.clear_interrupt()
            # print(str(time.time()) + " -> " + str(sensor_angle) + ": 4")

            if measurement_data.is_valid:
                radar[angle] = measurement_data.distance + adjusted_distance
            else:
                print("Measurement error " + sensor.name + ": " + measurement_data.get_range_status_description() + " d=" + str(measurement_data.distance))
                if measurement_data.distance > 0:
                    radar[angle] = measurement_data.distance + adjusted_distance

            # print(str(time.time()) + " -> " + str(sensor_angle) + ": 5")
            updateStatus(angle, measurement_data.range_status)
            # print(str(time.time()) + " -> " + str(sensor_angle) + ": 6")
        else:
            pass
            # print(str(time.time()) + " -> " + str(sensor_angle) + ": 1E")

    except BaseException as e:
        if DEBUG:
            print("Failed to read sensor from i2c multiplexer address " + str(sensorsMap[angle]['bus']) + ":" + str(sensorsMap[angle]['i2c']) + ", " + str(e))


def readAllSensors():
    global i2c_error_detected

    if not paused:

        current_bus = None
        for angle in sensors:
            bus = sensorsMap[angle]['bus']
            if bus != current_bus:
                current_bus = bus
                _switchBus(bus)

            readSensor(angle)

        for angle in SENSORS_ORDER:
            if angle not in sensors:
                radar[angle] = 1

        radar['timestamp'] = time.time()

        pyroslib.publish("sensor/distance", " ".join([":".join([str(v) for v in kv]) for kv in radar.items()]))

        if i2c_error_detected:
            initDistanceSensors()
            i2c_error_detected = False


# noinspection PyTypeChecker
def initDistanceSensors():

    # noinspection PyProtectedMember
    def configureSensor(sensor):
        sensor.stop_ranging()
        sensor.set_distance_mode(DISTANCE_MODE)
        sensor.set_timing_budget(TIMING_BUDGET, INTERMEDIATE_PERIOD)
        sensor.set_region_of_interest(UserRoi(ROI_TOP, ROI_RIGHT, ROI_BOTTOM, ROI_LEFT))

    vl53l1x_i2c.open()

    GPIO.setup(XSHUT_PIN, GPIO.OUT)
    GPIO.output(XSHUT_PIN, GPIO.HIGH)

    need_to_init_xshut = False
    buses = [1, 2, 4, 8]
    i = 0
    while i < len(buses) and not need_to_init_xshut:
        bus = buses[i]
        _switchBus(bus)

        if not vl53l1x_i2c.is_device_at(I2C_VL53L1X_ADDRESS_2):
            print("        " + str(bus) + ": not present on " + hex(I2C_VL53L1X_ADDRESS_2))
            need_to_init_xshut = True
        else:
            print("        " + str(bus) + ": present on " + hex(I2C_VL53L1X_ADDRESS_2))

        i += 1

    if need_to_init_xshut:
        print("        Need to configure XSHUT sensors")
        GPIO.output(XSHUT_PIN, GPIO.LOW)
    else:
        print("        All XSHUT sensors already configured")

    for angle in SENSORS_ORDER:
        i2c_addres = sensorsMap[angle]['i2c']
        if i2c_addres == I2C_VL53L1X_ADDRESS_1:
            _switchBus(sensorsMap[angle]['bus'])
            name = sensorsMap[angle]['name']

            if vl53l1x_i2c.is_device_at(I2C_VL53L1X_ADDRESS_1):
                print("        " + str(name) + ": first sensor already present on " + hex(I2C_VL53L1X_ADDRESS_1))
                sensor1 = VL53L1X(vl53l1x_i2c, initial_address=I2C_VL53L1X_ADDRESS_1, name=name)
            else:
                print("        " + str(name) + ": configuring first sensor to " + hex(I2C_VL53L1X_ADDRESS_1))
                sensor1 = VL53L1X(vl53l1x_i2c, required_address=I2C_VL53L1X_ADDRESS_1, name=name)

            configureSensor(sensor1)
            sensorsMap[angle]['vl53l1x'] = sensor1

    if need_to_init_xshut:
        GPIO.output(XSHUT_PIN, GPIO.HIGH)
        time.sleep(0.002)
        for angle in SENSORS_ORDER:
            i2c_addres = sensorsMap[angle]['i2c']
            if i2c_addres == I2C_VL53L1X_ADDRESS_2:
                _switchBus(sensorsMap[angle]['bus'])
                name = sensorsMap[angle]['name']

                print("        " + str(name) + ": configuring XSHUT sensor to " + hex(I2C_VL53L1X_ADDRESS_2))
                sensor2 = VL53L1X(vl53l1x_i2c, required_address=I2C_VL53L1X_ADDRESS_2, name=name)
                configureSensor(sensor2)
                sensorsMap[angle]['vl53l1x'] = sensor2
    else:
        for angle in SENSORS_ORDER:
            i2c_addres = sensorsMap[angle]['i2c']
            if i2c_addres == I2C_VL53L1X_ADDRESS_2:
                _switchBus(sensorsMap[angle]['bus'])
                name = sensorsMap[angle]['name']

                print("        " + str(name) + ": configuring XSHUT sensor on " + hex(I2C_VL53L1X_ADDRESS_2))
                sensor2 = VL53L1X(vl53l1x_i2c, initial_address=I2C_VL53L1X_ADDRESS_2, name=name)
                configureSensor(sensor2)
                sensorsMap[angle]['vl53l1x'] = sensor2

    current_bus = None
    for angle in SENSORS_ORDER:
        bus = sensorsMap[angle]['bus']
        if bus != current_bus:
            current_bus = bus
            _switchBus(bus)

        name = sensorsMap[angle]['name']
        print("        " + str(name) + ": starting ranging")
        sensor = sensorsMap[angle]['vl53l1x']
        sensor.start_ranging()


def handleFocus(topic, message, groups):
    global sensors

    selected = [int(s) for s in message.split(" ")]

    sensors = [s for s in SENSORS_ORDER if s in selected]
    print("Got focus " + str(selected) + " and selected in order " + str(sensors))


def handlePause(topic, message, groups):
    global paused

    paused = True


def handleResume(topic, message, groups):
    global paused, sensors

    paused = False
    sensors = [s for s in SENSORS_ORDER]


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

        pyroslib.subscribe("sensor/distance/pause", handlePause)
        pyroslib.subscribe("sensor/distance/resume", handleResume)
        pyroslib.subscribe("sensor/distance/focus", handleFocus)

        print("Started vl53l1x service.")

        pyroslib.forever(0.02, readAllSensors)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
