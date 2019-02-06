#!/usr/bin/python

# MIT License
#
# Copyright (c) 2019 Richard Gemmell
# Based on the driver by John Bryan Moore copyright c) 2017
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import ctypes
import os
import site
import glob
from ctypes import *
from ctypes import util

from smbus2 import SMBus, i2c_msg


# Load the C library and define functions
C_LIBRARY = CDLL(ctypes.util.find_library('libc'))
C_LIBRARY.free.argtypes = [ctypes.c_void_p]
C_LIBRARY.free.restype = None

# Load the VL53L1X driver library
_POSSIBLE_LIBRARY_LOCATIONS = [os.path.dirname(os.path.realpath(__file__))]
try:
    _POSSIBLE_LIBRARY_LOCATIONS += site.getsitepackages()
except AttributeError:
    pass
try:
    _POSSIBLE_LIBRARY_LOCATIONS += [site.getusersitepackages()]
except AttributeError:
    pass

for lib_location in _POSSIBLE_LIBRARY_LOCATIONS:
    files = glob.glob(os.path.join(lib_location, "gcc_vl53l1x*.so"))
    if len(files) > 0:
        VL53L1X_C_LIBRARY = CDLL(files[0])
        # print("VL53L1X loaded gcc_vl53l1x library from {}".format(lib_location))
        break
else:
    raise OSError('VL53L1X: Could not find gcc_vl53l1x*.so library')


class VL53L1X_I2C:
    """Manages I2C communications for all sensors on the same I2C bus."""
    def __init__(self, i2c_bus=1):
        self._i2c_bus = i2c_bus
        self._i2c = SMBus(1)
        self.debug = False
        self.devices = []

    def open(self):
        """Opens the I2C bus"""
        self._i2c.open(bus=self._i2c_bus)
        self._configure_i2c_library_functions()
        if self.debug:
            print('VL53L1X: Opened I2C bus {}'.format(self._i2c_bus))

    def close(self):
        """Closes the I2C bus"""
        self._i2c.close()
        if self.debug:
            print('VL53L1X: Closed I2C bus {}'.format(self._i2c_bus))
        for device in self.devices:
            device.close()
        self.devices.clear()

    def is_device_at(self, address: int) -> bool:
        """
        :param address: an I2C address
        :returns true if there is an I2C device at this address
        """
        try:
            self._i2c.read_byte(address)
            return True
        except OSError:
            return False

    def _configure_i2c_library_functions(self):
        # Read/write function pointer types.
        _I2C_READ_FUNC = CFUNCTYPE(c_int, c_ubyte, c_ubyte, POINTER(c_ubyte), c_ubyte)
        _I2C_WRITE_FUNC = CFUNCTYPE(c_int, c_ubyte, c_ubyte, POINTER(c_ubyte), c_ubyte)

        # I2C bus read callback for low level library.
        def _i2c_read(address, reg, data_p, length):
            msg_w = i2c_msg.write(address, [reg >> 8, reg & 0xff])
            msg_r = i2c_msg.read(address, length)

            try:
                self._i2c.i2c_rdwr(msg_w, msg_r)
            except:
                print("VL53L1X: Cannot read on 0x%x I2C bus, reg: %d" % (address, reg))

            for index in range(length):
                data_p[index] = ord(msg_r.buf[index])
            return 0

        # I2C bus write callback for low level library.
        def _i2c_write(address, reg, data_p, length):
            data = [reg >> 8, reg & 0xff]
            for index in range(length):
                data.append(data_p[index])

            msg_w = i2c_msg.write(address, data)

            try:
                self._i2c.i2c_rdwr(msg_w)
            except:
                print("VL53L1X: Cannot write on 0x%x I2C bus, reg: %d" % (address, reg))
            return 0

        # Pass i2c read/write function pointers to VL53L1X library.
        self._i2c_read_func = _I2C_READ_FUNC(_i2c_read)
        self._i2c_write_func = _I2C_WRITE_FUNC(_i2c_write)
        VL53L1X_C_LIBRARY.VL53L1_set_i2c(self._i2c_read_func, self._i2c_write_func)


class VL53L1XError(RuntimeError):
    def __init__(self, error_code: int):
        message = ctypes.create_string_buffer(VL53L1X_C_LIBRARY.getMaxStringLength())
        err = VL53L1X_C_LIBRARY.VL53L1_GetPalErrorString(error_code, byref(message))
        if err:
            raise RuntimeError("VL53L1X: Failed to lookup error code")
        super().__init__(message.value.decode())


class Utils:
    @staticmethod
    def check(error_code: int):
        if error_code:
            raise VL53L1XError(error_code)


class OpticalCentreStructure(ctypes.Structure):
    _fields_ = [
        ('x_centre', ctypes.c_uint8),
        ('y_centre', ctypes.c_uint8),
    ]


class OpticalCentre:
    """Wraps raw data"""
    def __init__(self, data: OpticalCentreStructure):
        self.data = data

    @property
    def x(self) -> int:
        """The x co-ordinate in spads. The whole grid is 16x16 spads.
        The x axis is parallel to a line drawn between the two parts of the sensor."""
        return self.data.x_centre >> 4

    @property
    def y(self) -> int:
        """The y co-ordinate in spads. The whole grid is 16x16 spads.
        The y axis is perpendicular to a line drawn between the two parts of the sensor."""
        return self.data.y_centre >> 4


class UserRoiStructure(ctypes.Structure):
    _fields_ = [
        ('left', ctypes.c_uint8),
        ('top', ctypes.c_uint8),
        ('right', ctypes.c_uint8),
        ('bottom', ctypes.c_uint8),
    ]


class UserRoi:
    @staticmethod
    def from_struct(struct: UserRoiStructure):
        return UserRoi(struct.left, struct.top, struct.right, struct.bottom)

    def __init__(self, left: int, top: int, right: int, bottom: int):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self._assert_valid(self.left, "Left")
        self._assert_valid(self.top, "Top")
        self._assert_valid(self.right, "Right")
        self._assert_valid(self.bottom, "Bottom")

    def to_struct(self) -> UserRoiStructure:
        s = UserRoiStructure()
        s.left = c_uint8(self.left)
        s.top =  c_uint8(self.top)
        s.right =  c_uint8(self.right)
        s.bottom =  c_uint8(self.bottom)
        return s

    @staticmethod
    def _assert_valid(value: int, position: str):
        if value < 0 or value > 15:
            raise ValueError("{} out of range. {} must be > 0 and < 16".format(position, value))


class MeasurementDataStructure(ctypes.Structure):
    """Note that with the exception of time_stamp all fields
    defined as c_unit32 are actually in the form FixPoint1616_t
    which is a 32 floating point representation of some kind.
    The STM code says 'Given a floating point value f it's .16 bit point is (int)(f*(1<<16))'
    """
    _fields_ = [
        ('time_stamp', ctypes.c_uint32),
        ('stream_count', ctypes.c_uint8),
        ('ranging_quality_level', ctypes.c_uint8),
        ('signal_rate_rtn_mega_cps', ctypes.c_uint32),
        ('ambient_rate_rtn_mega_cps', ctypes.c_uint32),
        ('effective_spad_rtn_count', ctypes.c_uint16),
        ('sigma_milli_meter', ctypes.c_uint32),
        ('range_milli_meter', ctypes.c_int16),
        ('range_fractional_part', ctypes.c_uint8),
        ('range_status', ctypes.c_uint8),
    ]


class MeasurementData:
    """Wraps raw measurement data"""
    def __init__(self, data: MeasurementDataStructure):
        self.data = data

    @property
    def distance(self) -> int:
        return self.data.range_milli_meter

    @property
    def range_status(self) -> int:
        return self.data.range_status

    @property
    def is_valid(self) -> int:
        return self.data.range_status == 0

    def get_range_status_description(self) -> str:
        message = ctypes.create_string_buffer(VL53L1X_C_LIBRARY.getMaxStringLength())
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_GetRangeStatusString(self.data.range_status, byref(message)))
        return message.value.decode()


class VL53L1X:
    """A VL53L1X sensor"""
    DEFAULT_ADDRESS = 0x29

    # Valid distance modes
    SHORT = 1
    MEDIUM = 2
    LONG = 3

    def __init__(self,
                 vl53l1x_i2c: VL53L1X_I2C,
                 initial_address: int = DEFAULT_ADDRESS,
                 required_address: int = None,
                 name: str = 'VL53L1X'):
        """
        Connects to a VL53L1X at the given address and changes the address if required
        :param initial_address: the current I2C address of the sensor
        :param required_address: the desired I2C address of the sensor
        """
        self.closed = False
        self.debug = vl53l1x_i2c.debug
        if self.debug:
            print("VL53L1X: Creating sensor at I2C address 0x{:x}.".format(initial_address))
        self.name = name
        self.address = initial_address
        if not vl53l1x_i2c.is_device_at(initial_address):
            raise ValueError("VL53L1X: No device found at I2C address 0x{:x}".format(initial_address))
        self.dev = VL53L1X_C_LIBRARY.allocDevice(c_uint8(initial_address))
        vl53l1x_i2c.devices.append(self)
        if initial_address == VL53L1X.DEFAULT_ADDRESS:
            Utils.check(VL53L1X_C_LIBRARY.VL53L1_software_reset(self.dev))
        # else skip soft reset because it only works with the default I2C address
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_WaitDeviceBooted(self.dev))
        if required_address and required_address != initial_address:
            if self.debug:
                print("  Changing sensor address to 0x{:x} from 0x{:x}.".format(required_address, initial_address))
            Utils.check(VL53L1X_C_LIBRARY.setAddress(self.dev, c_uint8(required_address)))
            self.address = required_address
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_DataInit(self.dev))
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_StaticInit(self.dev))

    def set_distance_mode(self, distance_mode: int):
        """Sets the distance mode. The default is LONG.
        You can change distance mode whilst ranging.
        SHORT - Up to 1.3 m Better ambient immunity
        MEDIUM - Up to 3 m
        LONG - Up to 4 m Maximum distance
        """
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_SetDistanceMode(self.dev, c_uint8(distance_mode)))

    def set_timing_budget(self, timing_budget_millis: float = 20, inter_measurement_period_millis: int = 26):
        """Sets the timing budget and interval between ranging calls.
        The sensor will stop generating new samples if inter_measurement_period_millis
        is too small. If in doubt use timing_budget_millis + 6 milliseconds.
        The choice of values can have large and unpredictable effects on the output data rate.
        This call stops ranging if it is running.
        :param timing_budget_millis valid range is 6 to 1000 ms
        :param inter_measurement_period_millis minimum value is timingBudgetMillis + 3.5 millis
        """
        self.stop_ranging()
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_SetMeasurementTimingBudgetMicroSeconds(self.dev, int(timing_budget_millis * 1000)))
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_SetInterMeasurementPeriodMilliSeconds(self.dev, inter_measurement_period_millis))

    def start_ranging(self):
        """Starts continuous range measurements"""
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_StartMeasurement(self.dev))

    def stop_ranging(self):
        """Stops ranging measurements"""
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_StopMeasurement(self.dev))

    def clear_interrupt(self):
        """Resets the interrupt status and interrupt pin"""
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_ClearInterruptAndStartMeasurement(self.dev))

    def data_ready(self) -> bool:
        """Returns true if there is a measurement ready."""
        data_ready = ctypes.c_uint8()
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_GetMeasurementDataReady(self.dev, byref(data_ready)))
        return data_ready.value != 0

    def wait_for_data_ready(self):
        """Blocks until there is a measurement ready."""
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_WaitMeasurementDataReady(self.dev))

    def get_measurement_data(self) -> MeasurementData:
        """Returns the current measurement data in all its glory.
        range_milli_meter contains the actual distance."""
        result = MeasurementDataStructure()
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_GetRangingMeasurementData(self.dev, byref(result)))
        return MeasurementData(result)

    def get_distance(self) -> int:
        """Returns the current range in millimeters whether or not it's valid.
        Use get_measurement_data to check the validity of ranges."""
        return self.get_measurement_data().distance

    def get_optical_centre(self) -> OpticalCentre:
        """Returns the optical centre of the sensor from the most recent
        calibration. This may be the factory calibration. This is important
        when setting the field of view."""
        result = OpticalCentreStructure()
        Utils.check(VL53L1X_C_LIBRARY.getOpticalCentre(self.dev, byref(result)))
        return OpticalCentre(result)

    def set_region_of_interest(self, roi: UserRoi):
        """Gets the sensors region of interest"""
        value = roi.to_struct()
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_SetUserROI(self.dev, byref(value)))

    def get_region_of_interest(self) -> UserRoi:
        """Gets the sensors region of interest"""
        result = UserRoiStructure()
        Utils.check(VL53L1X_C_LIBRARY.VL53L1_GetUserROI(self.dev, byref(result)))
        return UserRoi.from_struct(result)

    def close(self):
        """Frees up C memory assocated with this sensor. Closing
        the VL53L1X_I2C instance will call this method for you."""
        if not self.closed:
            C_LIBRARY.free(self.dev)
            self.closed = True

