#!/usr/bin/python3

from GCC_VL53L1X import VL53L1X_I2C, VL53L1X, UserRoi


class SetRegionOfInterest:
    """This example shows how to set the sensor's region or interest.
    This determines its field of view."""
    def main(self):
        print("********************************************************************************")
        print("The sensor consists of a grid of 16x16 spads.")
        print("The x axis is parallel to a line drawn between the two parts of the sensor.")
        print("The y axis is perpendicular to a line drawn between the two parts of the sensor.")
        print("********************************************************************************")

        i2c = VL53L1X_I2C()
        i2c.debug = True    # Show log messages
        try:
            i2c.open()

            # Create a sensor and set basic configuration
            sensor = VL53L1X(i2c)
            sensor.set_distance_mode(VL53L1X.SHORT)
            sensor.set_timing_budget(10.5, 16)

            # Make the region of interest narrower
            centre = sensor.get_optical_centre()
            print("The optical centre is at x:{}, y:{}.".format(centre.x, centre.y))

            original_roi = sensor.get_region_of_interest()
            print("The region of interest is ({}, {}), ({}, {}) (left,top),(right,bottom).".format(original_roi.left, original_roi.top, original_roi.right, original_roi.bottom))

            sensor.set_region_of_interest(UserRoi(1, 12, 12, 1))
            try:
                roi = sensor.get_region_of_interest()
                print("The region of interest is now ({}, {}), ({}, {}) (left,top),(right,bottom)).".format(roi.left, roi.top, roi.right, roi.bottom))

                # Gather some data
                sensor.start_ranging()
                num_samples = 5
                for _ in range(0, num_samples):
                    sensor.wait_for_data_ready()  # Block until data ready.
                    measurement_data = sensor.get_measurement_data()
                    sensor.clear_interrupt()
                    distance = measurement_data.distance
                    status = measurement_data.get_range_status_description()
                    print("{}: {} mm ({})".format(sensor.name, distance, status))
                sensor.stop_ranging()
            finally:
                sensor.set_region_of_interest(original_roi)
                roi = sensor.get_region_of_interest()
                print("Restored ROI to ({}, {}), ({}, {}) (left,top),(right,bottom)).".format(roi.left, roi.top, roi.right, roi.bottom))


        finally:
            # You must call close() to prevent memory leaks.
            i2c.close()


if __name__ == '__main__':
    example = SetRegionOfInterest()
    example.main()
