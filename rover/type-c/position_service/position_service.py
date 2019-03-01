#!/usr/bin/env python3

#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import threading
import traceback
import pyroslib

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rover_position_rjg.data.data_pump.process_data_pump import ProcessDataPump
from rover_position_rjg.mqtt.mqtt_client import MqttClient
from rover_position_rjg.position.calibration.decawave.decawave_range_scaler import DecawaveRangeScaler
from rover_position_rjg.position.calibration.decawave.two_way_ranging_calibration import TwoWayRangingCalibration
from rover_position_rjg.sensors.decawave.decawave_data_provider import DecawaveDataProvider
from rover_position_rjg.sensors.decawave.fixed_position_data_provider import FixedPositionDataProvider
from rover_position_rjg.sensors.imu.imu_data_provider import ImuDataProvider
from rover_position_rjg.services.position.position_service import PositionService

decawave_data_frequency = 10


def create_dummy_decawave_provider():
    return FixedPositionDataProvider(decawave_data_frequency)

#
# position service
#
# This service is providing positioning.
#

DEBUG = False


def stopCallback():
    print("Asked to stop!")
    position_serivce.quit()


if __name__ == "__main__":
    try:
        print("Starting position service...")

        pyroslib.init("echo-service", onStop=stopCallback)

        print("Position started. (PID {})".format(os.getpid()))
        imu_data_frequency = 230.8  # 119 or 238 or 476 are ODR for accelerometer and gyro
        start = time.time()
        local_g = 9.81255  # Wolston
        # gc.set_debug(gc.DEBUG_STATS)

        # TODO Get these from a config file
        anchor_calibrations = [
            TwoWayRangingCalibration('1A85', 2, 0),
            TwoWayRangingCalibration('812E', 4, 53),
            TwoWayRangingCalibration('559C', 0, 125),
            TwoWayRangingCalibration('DB08', -2, 75),
        ]
        decawave_range_scaler = DecawaveRangeScaler(6.4, anchor_calibrations)
        ambient_temp = 10

        # Choose the calibration files
        dir_name = os.path.join(os.path.dirname(__file__), 'rover_1_35')
        imu_calibration_filename = os.path.join(dir_name, 'imu_calibration.json')
        decawave_calibration_filename = os.path.join(dir_name, 'decawave_calibration.json')

        # g = 9.81265 # Cambridge
        position_serivce = PositionService(
            imu_data_frequency,
            local_g,
            0.15,  # std dev of decawave measurement
            0.01,  # std dev of odometer
            0.01,  # std dev of acceleration measurements
            imu_calibration_filename,
            decawave_calibration_filename,
            decawave_range_scaler,
            ambient_temp,
            ProcessDataPump(ImuDataProvider, 1.5 / imu_data_frequency, 'IMU', samples_to_reject=15),
            # ProcessDataPump(DecawaveDataProvider, 1.5/decawave_data_frequency, 'Decawave'),
            ProcessDataPump(create_dummy_decawave_provider, 2 / decawave_data_frequency, 'Decawave'),
            MqttClient('position', 'position', 0.01)
        )
        threading.Thread(target=position_serivce.run, daemon=True).start()
        print("Position finished in {:.1f} seconds".format(time.time() - start))

        print("Started position service.")
        pyroslib.forever(0.5)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
