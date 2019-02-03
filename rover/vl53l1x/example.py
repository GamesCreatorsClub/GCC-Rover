import time
from datetime import datetime

from RPi import GPIO

from GCC_VL53L1X import VL53L1X_I2C, VL53L1X


class TimeOfFlightTester:
    def __init__(self):
        # I2C addresses for each sensor
        self.address_1 = 0x31
        self.address_2 = 0x32
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
        try:
            i2c.open()

            # Which addresses are available
            print('0x{:x} occupied {}'.format(VL53L1X.DEFAULT_ADDRESS, i2c.is_device_at(VL53L1X.DEFAULT_ADDRESS)))
            print('0x{:x} occupied {}'.format(self.address_1, i2c.is_device_at(self.address_1)))
            print('0x{:x} occupied {}'.format(self.address_2, i2c.is_device_at(self.address_2)))

            # Swap addresses on each run
            if i2c.is_device_at(self.address_1):
                sensor1 = VL53L1X(i2c, initial_address=self.address_1, required_address=VL53L1X.DEFAULT_ADDRESS)
            else:
                sensor1 = VL53L1X(i2c, required_address=self.address_1, name='Sensor1')

            # Configure it
            sensor1.set_distance_mode(VL53L1X.SHORT)
            sensor1.set_timing_budget(8, 16)

            # Range
            sensor1.start_ranging()
            start = time.time()
            num_samples = 20
            for _ in range(0, num_samples):
                # while not sensor1.data_ready():
                #     time.sleep(0.00001)
                sensor1.wait_for_data_ready()
                measurement_data = sensor1.get_measurement_data()
                sensor1.clear_interrupt()
                distance = measurement_data.distance
                status = measurement_data.get_range_status_description()
                print("{} Time: {}: {} mm  ({})".format(sensor1.name, datetime.utcnow().strftime("%S.%f"), distance, status))
            sensor1.stop_ranging()
            duration = time.time() - start
            print("{:.1f} Hz. ({} samples in {:.2f}s)".format(num_samples/duration, num_samples, duration))

            sensor1.close()
        finally:
            i2c.close()

    def reset(self):
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
