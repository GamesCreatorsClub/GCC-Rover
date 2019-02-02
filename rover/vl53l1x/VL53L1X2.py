#!/usr/bin/python

# MIT License
#
# Copyright (c) 2017 John Bryan Moore
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
from ctypes import CDLL, CFUNCTYPE, POINTER, c_int, pointer, c_ubyte, c_uint8
from typing import Dict

from smbus2 import SMBus, i2c_msg
import os
import site
import glob


class VL53L1xError(RuntimeError):
    pass


class VL53L1xDistanceMode:
    SHORT = 1
    MEDIUM = 2
    LONG = 3

# Read/write function pointer types.
_I2C_READ_FUNC = CFUNCTYPE(c_int, c_ubyte, c_ubyte, POINTER(c_ubyte), c_ubyte)
_I2C_WRITE_FUNC = CFUNCTYPE(c_int, c_ubyte, c_ubyte, POINTER(c_ubyte), c_ubyte)

# Load VL53L1X shared lib
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
    files = glob.glob(lib_location + "/vl53l1x_python*.so")
    if len(files) > 0:
        lib_file = files[0]
        try:
            _TOF_LIBRARY = CDLL(lib_file)
            # print("Using: " + lib_location + "/vl51l1x_python.so")
            break
        except OSError:
            # print(lib_location + "/vl51l1x_python.so not found")
            pass
else:
    raise OSError('Could not find vl53l1x_python.so')


class VL53L1X:
    """Driver for VL53L1X Time of Flight sensor from ST."""

    def __init__(self, i2c_bus=1):
        self._i2c_bus = i2c_bus
        self._i2c = SMBus(1)
        self._dev_list: Dict[str, any] = dict()

    def open(self):
        self._i2c.open(bus=self._i2c_bus)
        self._configure_i2c_library_functions()

    def close(self):
        for key in self._dev_list:
            self._destroy_sensor(key)
        self._dev_list.clear()
        self._i2c.close()

    def _destroy_sensor(self, sensor_id: str):
        dev = self._get_device(sensor_id)
        _TOF_LIBRARY.destroy(dev)

    def add_sensor(self, sensor_id: str, address: int):
        if sensor_id in self._dev_list:
            raise VL53L1xError('Already added sensor {}'.format(sensor_id))
        self._dev_list[sensor_id] = _TOF_LIBRARY.initialise()
        _TOF_LIBRARY.init_dev(self._dev_list[sensor_id], c_uint8(address))

    def start_ranging(self, sensor_id, mode=VL53L1xDistanceMode.LONG, timing_budget_millis: int = 66, inter_measurement_period_millis: int = 70):
        dev = self._get_device(sensor_id)
        _TOF_LIBRARY.startRanging(dev, mode, timing_budget_millis*1000, inter_measurement_period_millis)

    def stop_ranging(self, sensor_id):
        dev = self._get_device(sensor_id)
        _TOF_LIBRARY.stopRanging(dev)

    def data_ready(self, sensor_id: str) -> bool:
        dev = self._get_device(sensor_id)
        data_ready = _TOF_LIBRARY.isDataReady(dev) > 0
        if data_ready:
            _TOF_LIBRARY.clearInterrupt(dev)
        return data_ready

    def get_distance(self, sensor_id):
        dev = self._get_device(sensor_id)
        return _TOF_LIBRARY.getDistance(dev)

    def get_address(self, sensor_id):
        dev = self._get_device(sensor_id)
        return _TOF_LIBRARY.get_address(dev)

    def change_address(self, sensor_id, new_address):
        dev = self._get_device(sensor_id)
        _TOF_LIBRARY.setDeviceAddress(dev, new_address)

    def _get_device(self, sensor_id: str):
        return self._dev_list[sensor_id]

    def _configure_i2c_library_functions(self):
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
        _TOF_LIBRARY.VL53L1_set_i2c(self._i2c_read_func, self._i2c_write_func)
