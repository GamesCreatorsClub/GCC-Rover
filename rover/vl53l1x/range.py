#!/usr/bin/python3

import time

from RPi import GPIO

from GCC_VL53L1X import VL53L1X_I2C, VL53L1X, Utils, VL53L1X_C_LIBRARY


class TimeOfFlightTester:
    @staticmethod
    def clear_interrupt(sensor: VL53L1X):
        """This method demonstrates that you can call the C library directly
        if necessary. This is handy when you need to call an STM API method
        that I haven't exposed via Python"""
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_ClearInterruptAndStartMeasurement(sensor.dev))

    def __init__(self):
        # I2C addresses for each sensor
        self.address_1 = 0x31
        # GPIO pin for XSHUT
        self.xshut_pin = 17

    def init_gpio(self):
        # Setup the GPIO pins for SHUTX
        # XSHUT is connected to only half the sensors
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.xshut_pin, GPIO.OUT)

    def cleanup_gpio(self):
        GPIO.cleanup(channel=self.xshut_pin)

    def main(self):
        # self.reset()  # Force reset if necessary
        i2c = VL53L1X_I2C()
        i2c.debug = True    # Show log messages
        try:
            i2c.open()

            # Change the I2C address just to show that we can
            if i2c.is_device_at(self.address_1):
                sensor = VL53L1X(i2c, initial_address=self.address_1, required_address=VL53L1X.DEFAULT_ADDRESS)
            else:
                sensor = VL53L1X(i2c, required_address=self.address_1, name='Sensor1')

            # Configure the sensor.
            # SHORT range is good for 1.3 meters.
            sensor.set_distance_mode(VL53L1X.SHORT)
            # The sensor is very sensitive to the timing budget values.
            # See the method documentation for details.
            sensor.set_timing_budget(10.5, 16)

            # Gather some data
            sensor.start_ranging()
            start = time.time()
            total = 0
            num_samples = 20
            for _ in range(0, num_samples):
                # while not sensor.data_ready():   # Check for new data without blocking the thread.
                #     time.sleep(0.0002)
                sensor.wait_for_data_ready()  # Block until data ready.
                measurement_data = sensor.get_measurement_data()
                sensor.clear_interrupt()
                distance = measurement_data.distance
                total += distance
                status = measurement_data.get_range_status_description()
                print("{}: {} mm ({})".format(sensor.name, distance, status))
            sensor.stop_ranging()
            duration = time.time() - start
            print("{} samples at {:.1f} Hz. Average distance {} mm.".format(num_samples, num_samples/duration, int(total/num_samples)))
        finally:
            # You must call close() to prevent memory leaks.
            i2c.close()

    def reset(self):
        """Resets the sensor by toggling the XSHUT pin. This won't work
        unless the sensor's XSHUT is connected to the correct GPIO pin."""
        GPIO.output(self.xshut_pin, GPIO.LOW)
        time.sleep(0.002)
        GPIO.output(self.xshut_pin, GPIO.HIGH)
        time.sleep(0.002)


if __name__ == '__main__':
    tof = TimeOfFlightTester()
    tof.init_gpio()
    try:
        tof.main()
    finally:
        tof.cleanup_gpio()
