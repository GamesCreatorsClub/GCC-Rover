#!/usr/bin/env python3

#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import RPi.GPIO as GPIO

import copy
import nRF2401
import pyroslib
import smbus
import storagelib
import telemetry
import time
import threading
import traceback

#
# wheels service
#
#
# This service is responsible for moving wheels on the rover.
# Current implementation also handles:
#     - servos
#     - storage map
#

NRF_CHANNEL = 1
NRF_PACKET_SIZE = 17
NRF_DEFAULT_ADDRESS = [ord('W'), ord('H'), ord('L'), ord('0'), ord('0')]

DEBUG = False
DEBUG_SPEED = False
DEBUG_SPEED_VERBOSE = False
DEBUG_READ = False
DEBUG_TURN = False
DBEUG_ERRORS = False

OVERHEAT_PROTECTION = 2.5
OVERHEAT_COOLDOWN = 2.5

MSG_TYPE_STOP_ALL = 0
MSG_TYPE_READ_ONLY = 1
MSG_TYPE_SET_POSITION = 2
MSG_TYPE_SET_SPEED = 3
MSG_TYPE_SET_PID = 4
MSG_TYPE_SET_RAW_BR = 101

STATUS_ERROR_I2C_WRITE = 1
STATUS_ERROR_I2C_READ = 2
STATUS_ERROR_MOTOR_OVERHEAT = 4
STATUS_ERROR_MAGNET_HIGH = 8
STATUS_ERROR_MAGNET_LOW = 16
STATUS_ERROR_MAGNET_NOT_DETECTED = 32
STATUS_ERROR_RX_FAILED = 64
STATUS_ERROR_TX_FAILED = 128

I2C_BUS = 1
I2C_MULTIPLEXER_ADDRESS = 0x70
I2C_AS5600_ADDRESS = 0x36
I2C_VL53L1X_ADDRESS_1 = 0x31
I2C_VL53L1X_ADDRESS_2 = 0x32
XSHUT_PIN = 4

WHEEL_STEER_CURRENT = 300  # mAh
WHEEL_DRIVE_CURRENT = 200  # mAh
WHEEL_IDLE_CURRENT = 150  # mAh

last_status_broadcast = 0
status_broadcast_time = 5  # every 5 seconds
service_started_time = 0
last_time = 0

i2cBus = smbus.SMBus(I2C_BUS)

shutdown = False
all_stop = False

steer_logger = None
drive_logger = None

kp = 0.7
ki = 0.29
kd = 0.01
kg = 1.0

deadband = 1

PROTOTYPE_WHEEL_CALIBRATION = {
    'deg': {
        '0': "160",
        'i2c': 0,
        'dir': 1
    },
    'speed': {
        'addr': "WHL00",
        '0': "0",
        'dir': "1"
    },
    'steer': {
        'en_pin': "0",
        'pwm_pin': "0",
        'dir': "-1"
    }
}

PROTOTYPE_PID_CALIBRATION = {
    'p': 2.0,
    'i': 1.0,
    'd': 0.01,
    'g': 1.0,
    'deadband': 1.0
}

wheelMap = {}
wheelCalibrationMap = {}
wheelMap["servos"] = {}
WHEEL_NAMES = ['fl', 'fr', 'bl', 'br']

STOP_OVERHEAT = bytes('SO', 'ASCII')
STOP_NO_DATA = bytes('SN', 'ASCII')
STOP_REACHED_POSITION = bytes('SK', 'ASCII')
FORWARD = bytes('FO', 'ASCII')
BACK = bytes('BA', 'ASCII')


class PID:
    def __init__(self, _kp, _ki, _kd, gain, dead_band):
        self.set_point = 0.0
        self.p = 0.0
        self.i = 0.0
        self.d = 0.0
        self.kp = _kp
        self.ki = _ki
        self.kd = _kd
        self.kg = gain
        self.dead_band = dead_band
        self.last_error = 0.0
        self.last_time = 0.0
        self.last_output = 0.0
        self.last_delta = 0.0
        self.first = True

    def process(self, set_point, current):
        now = time.time()

        error = angle_difference(set_point, current)
        if abs(error) <= self.dead_band:
            error = 0.0

        if self.first:
            self.first = False
            self.set_point = set_point
            self.last_error = error
            self.last_time = now
            return 0
        else:
            delta_time = now - self.last_time

            self.p = error
            if (self.last_error < 0 and error > 0) or (self.last_error > 0 and error < 0):
                self.i = 0.0
            elif abs(error) <= 0.1:
                self.i = 0.0
            else:
                self.i += error * delta_time

            if delta_time > 0:
                self.d = (error - self.last_error) / delta_time

            output = self.p * self.kp + self.i * self.ki + self.d * self.kd

            output *= self.kg

            self.set_point = set_point
            self.last_output = output
            self.last_error = error
            self.last_time = now
            self.last_delta = delta_time

        return output

    def to_string(self):
        return "p=" + str(self.p * self.kp) + ", i=" + str(self.i * self.ki) + ", d=" + str(self.d * self.kd) + ", last_delta=" + str(self.last_delta)


def normalise_angle(a):
    a = a % 360
    if a < 0:
        a += 360
    return a


def angle_difference(a1, a2):
    diff = a1 - a2
    if diff >= 180:
        return diff - 360
    elif diff <= -180:
        return diff + 360
    return diff


def opposite_angle(a, mod):
    if mod >= 0:
        return a
    return normalise_angle(a + 180)


def smallest_angle_change(old_angle, mod, new_angle):
    real_old_angle = opposite_angle(old_angle, mod)
    angle_diff = angle_difference(new_angle, real_old_angle)
    if angle_diff > 90:
        new_diff = angle_diff - 180
        return normalise_angle(old_angle + new_diff), -mod
    elif angle_diff < -90:
        new_diff = 180 + angle_diff
        return normalise_angle(old_angle + new_diff), -mod
    else:
        return normalise_angle(old_angle + angle_diff), mod


def _update_service_started_time():
    global service_started_time
    with open("/proc/uptime", 'r') as fh:
        uptime = float(float(fh.read().split(" ")[0]))

        service_started_time = time.time() - uptime
        print("  set started time " + str(uptime) + " seconds ago.")


def init_wheel(wheel_name: str):
    wheelMap[wheel_name] = {
        'deg': 0,
        'deg_stop': False,
        'speed': 0,
        's_mod': 1,
        'gen': None,
        'name': wheel_name,
        'pid': PID(0.7, 0.29, 0.01, 1.0, 1),
        'deg_lt': 0,  # deg last time
        'speed_lt': 0,  # speed last time
        'deg_pwm': 0,  # pwm duty cycle
        'speed_pwm': 0,  # pwm
        'dmAh': 0,  # deg mAh
        'smAh': 0   # speed mAh
    }


def init_wheels():
    global wheelCalibrationMap

    if "wheels" not in storagelib.storageMap:
        storagelib.storageMap["wheels"] = {}

    if "cal" not in storagelib.storageMap["wheels"]:
        storagelib.storageMap["wheels"]["cal"] = {}

    wheelCalibrationMap = storagelib.storageMap["wheels"]["cal"]

    for wheel in WHEEL_NAMES:
        init_wheel(wheel)


def init_all_wheels_pid():
    global kp, ki, kd, kg, deadband
    kp = float(wheelCalibrationMap['pid']['p'])
    ki = float(wheelCalibrationMap['pid']['i'])
    kd = float(wheelCalibrationMap['pid']['d'])
    kg = float(wheelCalibrationMap['pid']['g'])
    deadband = int(float(wheelCalibrationMap['pid']['deadband']))

    for wheel_name in WHEEL_NAMES:
        pid = wheelMap[wheel_name]['pid']
        pid.kp = kp
        pid.ki = ki
        pid.kd = kd
        pid.kg = kg
        pid.dead_band = deadband


def check_pids_changed():
    if kp != float(wheelCalibrationMap['pid']['p']) or \
            ki != float(wheelCalibrationMap['pid']['i']) or \
            kd != float(wheelCalibrationMap['pid']['d']) or \
            kg != float(wheelCalibrationMap['pid']['g']) or \
            deadband != float(wheelCalibrationMap['pid']['deadband']):
        init_all_wheels_pid()


def subscribe_wheels():
    for wheel_name in WHEEL_NAMES:
        storagelib.subscribeWithPrototype("wheels/cal/" + wheel_name, PROTOTYPE_WHEEL_CALIBRATION)
    storagelib.subscribeWithPrototype("wheels/cal/pid", PROTOTYPE_PID_CALIBRATION)


def ensure_wheel_data(name: str, motor_enable_pin: int, motor_pwm_pin: int, i2c_address: int, nrf_address: str):
    calibration_map = copy.deepcopy(PROTOTYPE_WHEEL_CALIBRATION)
    calibration_map['steer']['en_pin'] = str(motor_enable_pin)
    calibration_map['steer']['pwm_pin'] = str(motor_pwm_pin)
    calibration_map['speed']['addr'] = str(nrf_address)
    calibration_map['deg']['i2c'] = str(i2c_address)
    storagelib.bulkPopulateIfEmpty("wheels/cal/" + name, calibration_map)


def print_wheel_calibration(wheel_name):
    print("    " + wheel_name + ".deg.i2c: " + str(wheelCalibrationMap[wheel_name]['deg']['i2c']))
    print("    " + wheel_name + ".deg.0: " + str(wheelCalibrationMap[wheel_name]['deg']['0']))
    print("    " + wheel_name + ".speed.addr: " + str(wheelCalibrationMap[wheel_name]['speed']['addr']))
    print("    " + wheel_name + ".steer.en_pin: " + str(wheelCalibrationMap[wheel_name]['steer']['en_pin']))
    print("    " + wheel_name + ".steer.pwm_pin: " + str(wheelCalibrationMap[wheel_name]['steer']['pwm_pin']))


def print_pid_cal():
    print("    pid.p: " + str(wheelCalibrationMap['pid']['p']))
    print("    pid.i: " + str(wheelCalibrationMap['pid']['i']))
    print("    pid.d: " + str(wheelCalibrationMap['pid']['d']))
    print("    pid.g: " + str(wheelCalibrationMap['pid']['g']))
    print("    pid.deadband: " + str(wheelCalibrationMap['pid']['deadband']))


def setup_wheel_with_calibration(wheel_name):
    calibration_map = wheelCalibrationMap[wheel_name]

    en_pin = int(calibration_map['steer']['en_pin'])
    GPIO.setup(en_pin, GPIO.OUT)

    pwm_pin = int(calibration_map['steer']['pwm_pin'])
    GPIO.setup(pwm_pin, GPIO.OUT)
    motor_pwm = GPIO.PWM(pwm_pin, 1000)
    motor_pwm.start(0)
    calibration_map['steer']['pwm'] = motor_pwm

    address = calibration_map['speed']['addr']
    calibration_map['speed']['nrf'] = [ord(address[0]), ord(address[1]), ord(address[2]), ord(address[3]), ord(address[4])]


def load_storage():
    ensure_wheel_data("fr", 12, 16, 1, 'WHL01')
    ensure_wheel_data("fl", 20, 21, 2, 'WHL02')
    ensure_wheel_data("br", 6, 13, 4, 'WHL03')
    ensure_wheel_data("bl", 19, 26, 8, 'WHL04')
    subscribe_wheels()
    storagelib.waitForData()

    for wheel_name in WHEEL_NAMES:
        print_wheel_calibration(wheel_name)
    print_pid_cal()

    for wheel_name in WHEEL_NAMES:
        setup_wheel_with_calibration(wheel_name)
    print("  Storage details loaded.")


def stop_all_wheels():
    stop_wheel('fr')
    stop_wheel('fl')
    stop_wheel('br')
    stop_wheel('bl')


def stop_wheel(wheel_name):
    calibration = wheelCalibrationMap[wheel_name]['steer']
    if "pwm" in calibration:
        en_pin = int(calibration['en_pin'])
        GPIO.output(en_pin, GPIO.LOW)
        motor_pwm = calibration['pwm']
        motor_pwm.ChangeDutyCycle(0)
        print("*** Stopped wheel " + str(wheel_name))


def handle_degrees(wheel, new_angle: float):
    try:
        old_angle = wheel['deg']
        old_mod = wheel['s_mod']

        new_angle, mod = smallest_angle_change(old_angle, old_mod, new_angle)

        wheel['old'] = old_angle
        wheel['deg'] = new_angle
        wheel['s_mod'] = mod

        wheel['deg_stop'] = False
    except Exception:
        wheel['deg_stop'] = True


def handle_speed(wheel, speed_string: str):
    if DEBUG_SPEED_VERBOSE:
        wheel_name = wheel['name']
        print("    got speed " + speed_string + " @ for " + str(wheel_name))

    wheel['speed'] = speed_string


def steer_wheel(wheel_name: str, current_degrees, status):
    def update_current(duty_cycle):
        last_time = wheel['deg_lt']
        t = time.time()
        if t - last_time < 1:
            last_pwm = wheel['deg_pwm']
            milli_amp_hours = (abs(duty_cycle + last_pwm) / 200) * (t - last_time) * WHEEL_STEER_CURRENT / 3600  # 1000 mAh = 1 aH - 1 s = 1/3600h
            wheel['dmAh'] = wheel['dmAh'] + milli_amp_hours
        wheel['deg_lt'] = t
        wheel['deg_pwm'] = duty_cycle

    def stop():
        GPIO.output(en_pin, GPIO.LOW)
        motor_pwm.ChangeDutyCycle(0)
        update_current(0)

    wheel = wheelMap[wheel_name]
    calibration_steer = wheelCalibrationMap[wheel_name]['steer']
    en_pin = int(calibration_steer['en_pin'])
    steer_direction = int(calibration_steer['dir'])
    motor_pwm = calibration_steer['pwm']

    deg = int(wheel['deg'])

    if all_stop:
        stop()
        return

    if 'overheat' in wheel:
        overheat = wheel['overheat']
        now = time.time()
        if now - overheat > OVERHEAT_COOLDOWN:
            del wheel['overheat']
        else:
            stop()
            steer_logger.log(time.time(), bytes(wheel_name, 'ascii'), STOP_OVERHEAT, current_degrees, status | STATUS_ERROR_MOTOR_OVERHEAT, 0, 0, 0, 0, 0, 0, 0)
            return

    deg_stop = wheel['deg_stop']

    if deg_stop or current_degrees is None or deg is None:
        stop()
        steer_logger.log(time.time(), bytes(wheel_name, 'ascii'), STOP_NO_DATA, current_degrees, status, 0, 0, 0, 0, 0, 0, 0)
    else:
        pid = wheel['pid']
        speed = pid.process(deg, current_degrees)

        forward = True
        speed = speed * steer_direction
        original_speed = speed
        if speed < 0:
            forward = False
            speed = -speed

        if speed > 100.0:
            speed = 100.0
        elif speed < 1:
            speed = 0.0
            stop()
            steer_logger.log(time.time(), bytes(wheel_name, 'ascii'), STOP_REACHED_POSITION, current_degrees, status, speed, pid.last_output, pid.last_delta, pid.set_point, pid.i, pid.d, pid.last_error)
            return

        if speed > 50:
            now = time.time()
            if 'thermal' in wheel:
                thermal = wheel['thermal']
                if now - thermal > OVERHEAT_PROTECTION:
                    del wheel['thermal']
                    wheel['overheat'] = now
                    stop()
                    steer_logger.log(time.time(), bytes(wheel_name, 'ascii'), STOP_OVERHEAT, current_degrees, status | STATUS_ERROR_MOTOR_OVERHEAT, speed, pid.last_output, pid.last_delta, pid.set_point,pid.i, pid.d, pid.last_error)
                    return
            else:
                wheel['thermal'] = now
        elif 'thermal' in wheel:
            del wheel['thermal']

        if forward:
            GPIO.output(en_pin, GPIO.LOW)
            motor_pwm.ChangeDutyCycle(speed)
            update_current(speed)
            steer_logger.log(time.time(), bytes(wheel_name, 'ascii'), BACK, current_degrees, status, speed, pid.last_output, pid.last_delta, pid.set_point, pid.i, pid.d, pid.last_error)
            if DEBUG_TURN:
                print(wheel_name.upper() + ": going back; " + str(deg) + "<-->" + str(current_degrees) + ", s=" + str(speed) + " os=" + str(original_speed) + ", " + pid.to_string())
        else:
            GPIO.output(en_pin, GPIO.HIGH)
            motor_pwm.ChangeDutyCycle(100.0 - speed)
            update_current(100.0 - speed)
            steer_logger.log(time.time(), bytes(wheel_name, 'ascii'), FORWARD, current_degrees, status, speed, pid.last_output, pid.last_delta, pid.set_point, pid.i, pid.d, pid.last_error)
            if DEBUG_TURN:
                print(wheel_name.upper() + ": going forward; " + str(deg) + "<-->" + str(current_degrees) + ", s=" + str(speed) + " os=" + str(original_speed) + ", " + pid.to_string())


def read_position(wheel_name: str):
    i2c_address = int(wheelCalibrationMap[wheel_name]['deg']["i2c"])
    try:
        i2cBus.write_byte(I2C_MULTIPLEXER_ADDRESS, i2c_address)
        try:
            pos = i2cBus.read_i2c_block_data(I2C_AS5600_ADDRESS, 0x0B, 5)
            angle = (pos[3] * 256 + pos[4]) * 360 // 4096
            status = pos[0] & 0b00111000 | STATUS_ERROR_MAGNET_NOT_DETECTED

            if DEBUG_READ:
                print("Read wheel " + wheel_name + " @ address " + str(i2c_address) + " pos " + str(angle) + " " + ("MH" if status & 8 else "  ") + " " + ("ML" if status & 16 else "  ") + " " + (
                    "MD" if status & 32 else "  "))

            return angle, status
        except Exception:
            if DEBUG_READ:
                print("Failed to read " + wheel_name + " @ address " + str(i2c_address))

        return 0, STATUS_ERROR_I2C_READ

    except Exception:
        if DEBUG_READ:
            print("Failed to select " + wheel_name + " @ address " + str(i2c_address))

        return 0, STATUS_ERROR_I2C_WRITE


def prepare_and_steer_wheel(wheel_name: str):
    angle, status = read_position(wheel_name)
    if DBEUG_ERRORS and status & 24 != 0:
        print(wheel_name + ": position (raw) " + str(angle) + " " + ("MH" if status & 8 else "  ") + " " + ("ML" if status & 16 else "  ") + " " + ("MD" if status & 32 else "  "))

    degree_calibration = wheelCalibrationMap[wheel_name]['deg']
    pos_dir = int(degree_calibration['dir'])
    if pos_dir < 0:
        angle = 360 - angle

    if status == 1:
        return 0, status

    calibration_offset = int(degree_calibration['0'])
    angle -= calibration_offset
    if angle < 0:
        angle += 360

    steer_wheel(wheel_name, angle, status)

    if 'overheat' in wheelMap[wheel_name]:
        status |= STATUS_ERROR_MOTOR_OVERHEAT

    return angle, status


def prepare_and_drive_wheel(wheel_name: str):
    def update_current(duty_cycle: int):
        last_time = wheel['speed_lt']
        t = time.time()
        if t - last_time < 1:
            last_pwm = wheel['speed_pwm']
            milli_amp_hours = (abs(duty_cycle + last_pwm) / 200) * (t - last_time) * WHEEL_DRIVE_CURRENT / 3600  # 1000 mAh = 1 aH - 1 s = 1/3600h
            wheel['smAh'] = wheel['smAh'] + milli_amp_hours
        wheel['speed_lt'] = t
        wheel['speed_pwm'] = duty_cycle

    wheel = wheelMap[wheel_name]
    wheel_speed_cal_map = wheelCalibrationMap[wheel_name]['speed']

    address = wheel_speed_cal_map['nrf']
    speed_dir_str = wheel_speed_cal_map['dir']

    started_time = time.time()
    nRF2401.setReadPipeAddress(0, address)
    nRF2401.setWritePipeAddress(address)

    if all_stop:
        speed_str = 0
    else:
        speed_str = wheel['speed']
    speed_mod_str = wheel['s_mod']

    try:
        speed = int(float(speed_str)) * int(speed_mod_str) * int(speed_dir_str)
    except:
        speed = None

    if speed is not None:
        update_current(abs(speed))
        send_speed = int(127 - (speed * 127 / 300))

        data = nRF2401.padToSize([MSG_TYPE_SET_RAW_BR, send_speed, send_speed], NRF_PACKET_SIZE)

        status = 0

        nRF2401.swithToTX()
        done = nRF2401.sendDataAndSwitchRx(data, 0.015)
        if done:
            pass
        else:
            # now = time.time()
            # drive_logger.log(now, bytes(wheelName, 'ASCII'), 0, STATUS_ERROR_TX_FAILED, (now - started_time), speed)
            # return 0, STATUS_ERROR_TX_FAILED
            status = status + STATUS_ERROR_TX_FAILED

        wheel_pos = 0

        if nRF2401.poolData(0.0025):  # 1 sec / 50 times a second / 4 wheels / 2 max half of time needed for wheel
            p = nRF2401.receiveData(NRF_PACKET_SIZE)
            nRF2401.stopListening()

            # drive_mode = p[0]
            # drive_speed = p[1]
            # wheel_speed = p[2]
            wheel_pos = p[3] + 256 * p[4]
            # wheel_pos_deg = int(wheel_pos * 360 / 4096)
            # wheel_r_pos = p[5] + 256 * p[6]
            # pid_p = p[7]
            # pid_i = p[8]
            # pid_d = p[9]
            # i2c_status = p[10]
            # pwm_reg = p[11]

            # now = time.time()
            # drive_logger.log(now, bytes(wheelName, 'ASCII'), wheel_pos, 0, (now - started_time), speed)
            # return wheel_pos, status
        else:
            # now = time.time()
            # drive_logger.log(now, bytes(wheelName, 'ASCII'), 0, STATUS_ERROR_RX_FAILED, (now - started_time), speed)
            # return 0, STATUS_ERROR_RX_FAILED
            status = status + STATUS_ERROR_RX_FAILED

        now = time.time()
        drive_logger.log(now, bytes(wheel_name, 'ASCII'), wheel_pos, 0, (now - started_time), speed)
        return wheel_pos, status


def drive_wheels():
    if not shutdown:
        odo_fl, status_speed_fl = prepare_and_drive_wheel("fl")
        odo_fr, status_speed_fr = prepare_and_drive_wheel("fr")
        odo_bl, status_speed_bl = prepare_and_drive_wheel("bl")
        odo_br, status_speed_br = prepare_and_drive_wheel("br")

        message = ",".join([str(f) for f in [time.time(), odo_fl, status_speed_fl, odo_fr, status_speed_fr, odo_bl, status_speed_bl, odo_br, status_speed_br]])
        pyroslib.publish("wheel/speed/status", message)


def steer_wheels():
    global last_status_broadcast

    if not shutdown:
        check_pids_changed()

        angle_fl, status_steer_fl = prepare_and_steer_wheel("fl")
        angle_fr, status_steer_fr = prepare_and_steer_wheel("fr")
        angle_bl, status_steer_bl = prepare_and_steer_wheel("bl")
        angle_br, status_steer_br = prepare_and_steer_wheel("br")

        message = ",".join([str(f) for f in [time.time(), angle_fl, status_steer_fl, angle_fr, status_steer_fr, angle_bl, status_steer_bl, angle_br, status_steer_br]])
        pyroslib.publish("wheel/deg/status", message)

        now = time.time()
        if last_status_broadcast + status_broadcast_time < now:
            broadcast_wheels_status()
            last_status_broadcast = now


def drive_thread_main():
    while not shutdown:
        try:
            starting = time.time()
            drive_wheels()
            now = time.time()
            if now - starting < 0.02:
                time.sleep(now - starting)
            else:
                time.sleep(0.01)
        except BaseException as exc:
            print("ERROR: drive.thread: " + str(exc) + "\n" + ''.join(traceback.format_tb(exc.__traceback__)))

    print("drive.thread: Shutdown detected.")


# noinspection PyUnusedLocal
def wheel_deg_topic(topic, payload, groups):
    wheel_name = groups[0]
    if wheel_name in wheelMap:
        wheel = wheelMap[wheel_name]
        if DEBUG_TURN:
            print("  Turning wheel: " + wheel_name + " to " + str(payload) + " degrees")
        handle_degrees(wheel, float(payload))
    else:
        print("ERROR: no wheel with name " + wheel_name + " found.")


# noinspection PyUnusedLocal
def wheel_speed_topic(topic, payload, groups):
    wheel_name = groups[0]
    if wheel_name in wheelMap:
        wheel = wheelMap[wheel_name]
        if DEBUG_SPEED:
            print("  Setting wheel: " + wheel_name + " speed to " + str(payload))
        handle_speed(wheel, payload)
    else:
        print("ERROR: no wheel with name " + wheel_name + " fonund.")


# noinspection PyUnusedLocal
def wheels_all_stop(topic, payload, groups):
    global all_stop
    if payload == 'stop':
        all_stop = True
    elif payload == 'run':
        all_stop = False
    elif payload == 'toggle':
        all_stop = not all_stop
    elif payload == 'status':
        pass

    broadcast_wheels_status()


def broadcast_wheels_status():
    steer_milli_ah = 0
    drive_milli_ah = 0
    for wheel_name in WHEEL_NAMES:
        wheel = wheelMap[wheel_name]
        steer_milli_ah += wheel['smAh']
        drive_milli_ah += wheel['dmAh']

    total_idle = (time.time() - service_started_time) * WHEEL_IDLE_CURRENT / 3600

    status = ("s:stopped" if all_stop else "s:running")
    status += " dmAh:" + str(int(drive_milli_ah)) + " smAh:" + str(int(steer_milli_ah)) + " wtmAh:" + str(int(drive_milli_ah + steer_milli_ah + total_idle))
    pyroslib.publish('wheel/feedback/status', status)


# noinspection PyUnusedLocal
def wheels_combined(topic, payload, groups):
    if DEBUG_SPEED:
        print(str(int(time.time() * 1000) % 10000000) + ": wheels " + payload)

    wheel_commands = payload.split(" ")
    for wheel_command in wheel_commands:
        kv = wheel_command.split(":")
        if len(kv) > 1:
            wheel_name = kv[0][:2]
            command = kv[0][2]
            value = kv[1]

            if wheel_name in wheelMap:
                wheel = wheelMap[wheel_name]
                if command == "s":
                    handle_speed(wheel, value)
                elif command == "d":
                    handle_degrees(wheel, float(value))


# noinspection PyUnusedLocal
def handle_shutdown_announced(topic, payload, groups):
    global shutdown
    shutdown = True
    stop_all_wheels()


def stop_callback():
    print("Asked to stop!")
    stop_all_wheels()


def uptime_thread_method():
    last_time = time.time()
    while True:
        try:
            now = time.time()
            if now - last_time > 2:
                _update_service_started_time()
                last_time = time.time()
            else:
                last_time = now
            time.sleep(1)
        except Exception:
            time.sleep(1)


if __name__ == "__main__":
    try:
        print("#4# Starting wheels service...")
        _update_service_started_time()

        print("    initialising wheels...")
        init_wheels()

        print("    setting GPIOs...")
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        print("    subscribing to topics...")
        pyroslib.subscribe("wheel/stop", wheels_all_stop)
        pyroslib.subscribe("wheel/all", wheels_combined)
        pyroslib.subscribe("wheel/+/deg", wheel_deg_topic)
        pyroslib.subscribe("wheel/+/speed", wheel_speed_topic)
        pyroslib.subscribe("shutdown/announce", handle_shutdown_announced)
        pyroslib.init("wheels-service", onStop=stop_callback)

        print("  Loading storage details...")
        load_storage()
        init_all_wheels_pid()

        print("  Initialising radio...")
        nRF2401.initNRF(0, 0, NRF_PACKET_SIZE, NRF_DEFAULT_ADDRESS, NRF_CHANNEL)

        clusterId = pyroslib.getClusterId()
        if clusterId is not "master":
            telemetryTopic = clusterId + ":telemetry"
        else:
            telemetryTopic = "telemetry"
        print("Running telemetry at topic " + telemetryTopic)

        steer_logger = telemetry.MQTTLocalPipeTelemetryLogger('wheel-steer', topic=telemetryTopic)
        steer_logger.addFixedString('wheel', 2)
        steer_logger.addFixedString('action', 2)
        steer_logger.addDouble('current')
        steer_logger.addByte('status')
        steer_logger.addDouble('speed')
        steer_logger.addDouble('pid_last_output')
        steer_logger.addDouble('pid_last_delta')
        steer_logger.addDouble('pid_set_point')
        steer_logger.addDouble('pid_i')
        steer_logger.addDouble('pid_d')
        steer_logger.addDouble('pid_last_error')

        drive_logger = telemetry.MQTTLocalPipeTelemetryLogger('wheel-drive', topic=telemetryTopic)
        drive_logger.addFixedString('wheel', 2)
        drive_logger.addDouble('pos')
        drive_logger.addByte('status')
        drive_logger.addTimestamp('time')
        drive_logger.addWord('speed', signed=True)

        print("  Initialising telemetry logging...")
        steer_logger.init()
        drive_logger.init()
        print("  Telemetry logging initialised.")

        print("Started wheels service.")

        driveThread = threading.Thread(target=drive_thread_main, daemon=True)
        driveThread.start()

        uptime_thread = threading.Thread(target=uptime_thread_method, daemon=True)
        uptime_thread.start()

        pyroslib.forever(0.02, steer_wheels)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
