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
libc = CDLL(ctypes.util.find_library('libc'))
libc.free.argtypes = [ctypes.c_void_p]
libc.free.restype = None

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
        lib_file = files[0]
        try:
            lib = CDLL(lib_file)
            print("Loaded gcc_vl53l1x library from {}".format(lib_location))
            break
        except OSError:
            print("Did not find gcc_vl53l1x library in {}".format(lib_location))
            pass
else:
    raise OSError('Could not find gcc_vl53l1x*.so library')


class VL53L1X_I2C:
    """Manages I2C communications for all sensors on the same I2C bus."""
    def __init__(self, i2c_bus=1):
        self._i2c_bus = i2c_bus
        self._i2c = SMBus(1)

    def open(self):
        """Opens the I2C bus"""
        self._i2c.open(bus=self._i2c_bus)
        self._configure_i2c_library_functions()
        print('Opened I2C bus {}'.format(self._i2c_bus))

    def close(self):
        """Closes the I2C bus"""
        self._i2c.close()
        print('Closed I2C bus {}'.format(self._i2c_bus))

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
                print("Cannot read on 0x%x I2C bus, reg: %d" % (address, reg))

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
                print("Cannot write on 0x%x I2C bus, reg: %d" % (address, reg))
            return 0

        # Pass i2c read/write function pointers to VL53L1X library.
        self._i2c_read_func = _I2C_READ_FUNC(_i2c_read)
        self._i2c_write_func = _I2C_WRITE_FUNC(_i2c_write)
        lib.VL53L1_set_i2c(self._i2c_read_func, self._i2c_write_func)


class VL53L1XError(RuntimeError):
    def __init__(self, error_code: int):
        message = ctypes.create_string_buffer(lib.getMaxStringLength())
        err = lib.VL53L1_GetPalErrorString(error_code, byref(message))
        if err:
            raise RuntimeError("Failed to lookup error code")
        super().__init__(message.value.decode())


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
        message = ctypes.create_string_buffer(lib.getMaxStringLength())
        self.check(lib.VL53L1_GetRangeStatusString(self.data.range_status, byref(message)))
        return message.value.decode()

    @staticmethod
    def check(error_code: int):
        if error_code:
            raise VL53L1XError(error_code)


class VL53L1X:
    """A VL53L1X sensor"""
    DEFAULT_ADDRESS = 0x29

    # Valid distance modes
    SHORT = 1
    MEDIUM = 2
    LONG = 3

    @staticmethod
    def check(error_code: int):
        if error_code:
            raise VL53L1XError(error_code)

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
        print("Creating VL53L1X at I2C address 0x{:x}.".format(initial_address))
        self.name = name
        self.address = initial_address
        if not vl53l1x_i2c.is_device_at(initial_address):
            raise ValueError("No device found at I2C address 0x{:x}".format(initial_address))
        self.dev = lib.allocDevice(c_uint8(initial_address))
        if initial_address == VL53L1X.DEFAULT_ADDRESS:
            self.check(lib.VL53L1_software_reset(self.dev))
        # else skip soft reset because it only works with the default I2C address
        self.check(lib.VL53L1_WaitDeviceBooted(self.dev))
        if required_address and required_address != initial_address:
            print("  Changing address to 0x{:x} from 0x{:x}.".format(required_address, initial_address))
            self.check(lib.setAddress(self.dev, c_uint8(required_address)))
            self.address = required_address
        self.check(lib.VL53L1_DataInit(self.dev))
        self.check(lib.VL53L1_StaticInit(self.dev))

    def set_distance_mode(self, distance_mode: int):
        """Sets the distance mode. The default is LONG.
        You can change distance mode whilst ranging.
        SHORT - Up to 1.3 m Better ambient immunity
        MEDIUM - Up to 3 m
        LONG - Up to 4 m Maximum distance
        """
        self.check(lib.VL53L1_SetDistanceMode(self.dev, c_uint8(distance_mode)))

    def set_timing_budget(self, timing_budget_millis: int = 20, inter_measurement_period_millis: int = 30):
        """Sets the timing budget and interval between ranging calls.
        You must read the range during the inter-measurement period.
        This call stops ranging if it is running.
        :param timing_budget_millis valid range is 20 to 1000 ms
        :param inter_measurement_period_millis minimum value is timingBudgetMillis + 4m
        """
        self.stop_ranging()
        self.check(lib.VL53L1_SetMeasurementTimingBudgetMicroSeconds(self.dev, timing_budget_millis * 1000))
        self.check(lib.VL53L1_SetInterMeasurementPeriodMilliSeconds(self.dev, inter_measurement_period_millis))

    def start_ranging(self):
        """Starts continuous range measurements"""
        self.check(lib.VL53L1_StartMeasurement(self.dev))

    def stop_ranging(self):
        """Stops ranging measurements"""
        self.check(lib.VL53L1_StopMeasurement(self.dev))

    def clear_interrupt(self):
        """Resets the interrupt status and interrupt pin"""
        self.check(lib.VL53L1_ClearInterruptAndStartMeasurement(self.dev))

    def data_ready(self) -> bool:
        """Returns true if there is a measurement ready."""
        data_ready = ctypes.c_uint8()
        self.check(lib.VL53L1_GetMeasurementDataReady(self.dev, byref(data_ready)))
        return data_ready.value != 0

    def wait_for_data_ready(self):
        """Blocks until there is a measurement ready."""
        self.check(lib.VL53L1_WaitMeasurementDataReady(self.dev))

    def get_measurement_data(self) -> MeasurementData:
        """Returns the current measurement data in all its glory.
        range_milli_meter contains the actual distance."""
        result = MeasurementDataStructure()
        self.check(lib.VL53L1_GetRangingMeasurementData(self.dev, byref(result)))
        return MeasurementData(result)

    def get_distance(self) -> int:
        """Returns the current range in millimeters whether or not it's valid.
        Use get_measurement_data to check the validity of ranges."""
        return self.get_measurement_data().distance

    def close(self):
        libc.free(self.dev)
