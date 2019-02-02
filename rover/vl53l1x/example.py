import sys

sys.path.append('.')
# from vl53l1x_driver import *
import time
from datetime import datetime

from RPi import GPIO
from VL53L1X2 import *


class TimeOfFlightTester:
    def main(self):
        # I2C addresses for each sensor
        ADDRESS_1 = 0x31
        ADDRESS_2 = 0x32

        # GPIO pins connected to the sensors SHUTX pins
        SHUTX_PIN_1 = 4

        # Arbitrary sensor id-s, should be unique for each sensor
        sensor_id_1 = 1
        sensor_id_2 = 2

        # GPIO.setwarnings(False)

        # Setup GPIO for shutdown pins on
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SHUTX_PIN_1, GPIO.OUT)

        # Init VL53L1X sensor
        tof = VL53L1X()
        tof.open()
        GPIO.output(SHUTX_PIN_1, GPIO.LOW)
        tof.add_sensor(sensor_id_1, ADDRESS_1)
        GPIO.output(SHUTX_PIN_1, GPIO.HIGH)
        tof.add_sensor(sensor_id_2, ADDRESS_2)

        print('Start ranging')
        # Start ranging, 1 = Short Range, 2 = Medium Range, 3 = Long Range
        tof.start_ranging(sensor_id_1, VL53L1xDistanceMode.SHORT, 16, 20)

        for _ in range(0, 100):
            while not tof.data_ready(sensor_id_1):
                time.sleep(0.00001)
            distance_mm_1 = tof.get_distance(sensor_id_1)
            print("Time: {}\tSensor 1: {} mm".format(datetime.utcnow().strftime("%S.%f"), distance_mm_1))

        # Halt sensor
        time.sleep(0.001)
        tof.stop_ranging(sensor_id_1)

        # Clean-up
        # tof.remove_sensor(sensor_id_1)
        tof.close()

        # Cleanup GPIO
        # GPIO.output(SHUTX_PIN_1, GPIO.LOW)
        GPIO.cleanup(channel=SHUTX_PIN_1)


if __name__ == '__main__':
    TimeOfFlightTester().main()
