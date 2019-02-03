#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import RPi.GPIO as GPIO

import copy
import nRF2401
import pyroslib
import re
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

i2cBus = smbus.SMBus(I2C_BUS)

shutdown = False

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


STOP_OVERHEAT = bytes('SO', 'ASCII')
STOP_NO_DATA = bytes('SN', 'ASCII')
STOP_REACHED_POSITION = bytes('SK', 'ASCII')
FORWARD = bytes('FO', 'ASCII')
BACK = bytes('BA', 'ASCII')


def normaiseAngle(a):
    if a < 0:
        a += 360
    if a >= 360:
        a -= 360
    return a


def angleDiference(a1, a2):
    diff = a1 - a2
    if diff > 180:
        return diff - 360
    elif diff < -180:
        return diff + 360
    else:
        return diff


def addAngles(a1, a2):
    return normaiseAngle(a1 + a2)


def subAngles(a1, a2):
    return normaiseAngle(a1 - a2)


def oppositeAngle(a, mod):
    if mod >= 0:
        return a
    return normaiseAngle(a + 180)


def smallestAngleChange(old_angle, mod, new_angle):
    real_old_angle = oppositeAngle(old_angle, mod)
    angle_diff = angleDiference(real_old_angle, new_angle)
    if angle_diff > 90:
        new_diff = angle_diff - 180
        return normaiseAngle(old_angle + new_diff), -mod
    elif angle_diff < -90:
        new_diff = 180 - angle_diff
        return normaiseAngle(old_angle + new_diff), -mod
    elif mod < 0:
        return normaiseAngle(old_angle + angle_diff), mod
    else:
        return new_angle, mod


class PID:
    def __init__(self, kp, ki, kd, gain, dead_band):
        self.set_point = 0.0
        self.p = 0.0
        self.i = 0.0
        self.d = 0.0
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.kg = gain
        self.dead_band = dead_band
        self.last_error = 0.0
        self.last_time = 0.0
        self.last_output = 0.0
        self.last_delta = 0.0
        self.first = True

    def process(self, set_point, current):
        now = time.time()

        error = angleDiference(set_point, current)
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


def initWheel(wheelName):
    wheelMap[wheelName] = {
        'deg': 0,
        'deg_stop': False,
        'speed': 0,
        's_mod': 1,
        'gen': None,
        'name': wheelName,
        'pid': PID(0.7, 0.29, 0.01, 1.0, 1)
    }


def initWheelPid(wheelName):
    global kp, ki, kd, kg, deadband
    kp = float(wheelCalibrationMap['pid']['p'])
    ki = float(wheelCalibrationMap['pid']['i'])
    kd = float(wheelCalibrationMap['pid']['d'])
    kg = float(wheelCalibrationMap['pid']['g'])
    deadband = int(float(wheelCalibrationMap['pid']['deadband']))

    pid = wheelMap[wheelName]['pid']
    pid.kp = kp
    pid.ki = ki
    pid.kd = kd
    pid.kg = kg
    pid.dead_band = deadband


def initWheels():
    global wheelCalibrationMap

    if "wheels" not in storagelib.storageMap:
        storagelib.storageMap["wheels"] = {}

    if "cal" not in storagelib.storageMap["wheels"]:
        storagelib.storageMap["wheels"]["cal"] = {}

    wheelCalibrationMap = storagelib.storageMap["wheels"]["cal"]

    initWheel("fr")
    initWheel("fl")
    initWheel("br")
    initWheel("bl")


def updateWheelsPid():
    initWheelPid('fr')
    initWheelPid('fl')
    initWheelPid('br')
    initWheelPid('bl')


def checkPidsChanged():
    if kp != wheelCalibrationMap['pid']['p'] or ki != wheelCalibrationMap['pid']['i'] or \
        kd != wheelCalibrationMap['pid']['d'] or kg != wheelCalibrationMap['pid']['g'] or \
        deadband != wheelCalibrationMap['pid']['deadband']:

        updateWheelsPid()


def subscribeWheels():
    storagelib.subscribeWithPrototype("wheels/cal/fl", PROTOTYPE_WHEEL_CALIBRATION)
    storagelib.subscribeWithPrototype("wheels/cal/fr", PROTOTYPE_WHEEL_CALIBRATION)
    storagelib.subscribeWithPrototype("wheels/cal/bl", PROTOTYPE_WHEEL_CALIBRATION)
    storagelib.subscribeWithPrototype("wheels/cal/br", PROTOTYPE_WHEEL_CALIBRATION)
    storagelib.subscribeWithPrototype("wheels/cal/pid", PROTOTYPE_PID_CALIBRATION)


def ensureWheelData(name, motorEnablePin, motorPWMPin, i2cAddress, nrfAddress):
    calMap = copy.deepcopy(PROTOTYPE_WHEEL_CALIBRATION)
    calMap['steer']['en_pin'] = str(motorEnablePin)
    calMap['steer']['pwm_pin'] = str(motorPWMPin)
    calMap['speed']['addr'] = str(nrfAddress)
    calMap['deg']['i2c'] = str(i2cAddress)
    storagelib.bulkPopulateIfEmpty("wheels/cal/" + name, calMap)


def ensurePIDData():
    calMap = copy.deepcopy(PROTOTYPE_PID_CALIBRATION)
    calMap['p'] = str(PROTOTYPE_PID_CALIBRATION['p'])
    calMap['i'] = str(PROTOTYPE_PID_CALIBRATION['i'])
    calMap['d'] = str(PROTOTYPE_PID_CALIBRATION['d'])
    calMap['g'] = str(PROTOTYPE_PID_CALIBRATION['g'])
    calMap['deadband'] = str(PROTOTYPE_PID_CALIBRATION['deadband'])
    storagelib.bulkPopulateIfEmpty("wheels/cal/pid", calMap)


def printWheelCal(wheelName):
    print("    " + wheelName + ".deg.i2c: " + str(wheelCalibrationMap[wheelName]['deg']['i2c']))
    print("    " + wheelName + ".deg.0: " + str(wheelCalibrationMap[wheelName]['deg']['0']))
    print("    " + wheelName + ".speed.addr: " + str(wheelCalibrationMap[wheelName]['speed']['addr']))
    print("    " + wheelName + ".steer.en_pin: " + str(wheelCalibrationMap[wheelName]['steer']['en_pin']))
    print("    " + wheelName + ".steer.pwm_pin: " + str(wheelCalibrationMap[wheelName]['steer']['pwm_pin']))


def printPidCal():
    print("    pid.p: " + str(wheelCalibrationMap['pid']['p']))
    print("    pid.i: " + str(wheelCalibrationMap['pid']['i']))
    print("    pid.d: " + str(wheelCalibrationMap['pid']['d']))
    print("    pid.g: " + str(wheelCalibrationMap['pid']['g']))
    print("    pid.deadband: " + str(wheelCalibrationMap['pid']['deadband']))


def setupWheelWithCal(wheelName):
    wheel = wheelMap[wheelName]
    wheelCalMap = wheelCalibrationMap[wheelName]

    enPin = int(wheelCalMap['steer']['en_pin'])
    GPIO.setup(enPin, GPIO.OUT)

    pwm_pin = int(wheelCalMap['steer']['pwm_pin'])
    GPIO.setup(pwm_pin, GPIO.OUT)
    motor_pwm = GPIO.PWM(pwm_pin, 1000)
    motor_pwm.start(0)
    wheelCalMap['steer']['pwm'] = motor_pwm

    address = wheelCalMap['speed']['addr']
    wheelCalMap['speed']['nrf'] = [ord(address[0]), ord(address[1]), ord(address[2]), ord(address[3]), ord(address[4])]


def loadStorage():
    ensureWheelData("fr", 12, 16, 1, 'WHL01')
    ensureWheelData("fl", 20, 21, 2, 'WHL02')
    ensureWheelData("br", 6, 13, 4, 'WHL03')
    ensureWheelData("bl", 19, 26, 8, 'WHL04')
    subscribeWheels()
    storagelib.waitForData()
    printWheelCal("fl")
    printWheelCal("fr")
    printWheelCal("bl")
    printWheelCal("br")
    printPidCal()

    setupWheelWithCal("fl")
    setupWheelWithCal("fr")
    setupWheelWithCal("bl")
    setupWheelWithCal("br")
    print("  Storage details loaded.")


def stopWheel(wheelName):
    wheel = wheelMap[wheelName]
    enPin = int(wheelCalibrationMap[wheelName]['steer']['en_pin'])
    steerDir = int(wheelCalibrationMap[wheelName]['steer']['dir'])

    if "pwm" in wheelCalibrationMap[wheelName]["steer"]:
        motor_pwm = wheelCalibrationMap[wheelName]['steer']['pwm']

        GPIO.output(enPin, GPIO.LOW)
        motor_pwm.ChangeDutyCycle(0)
        print("*** Stopped wheel " + str(wheelName))


def stopAllWheels():
    stopWheel('fr')
    stopWheel('fl')
    stopWheel('br')
    stopWheel('bl')


def handleDeg(wheel, wheelCal, new_angle):

    try:
        new_angle = float(new_angle)

        old_angle = wheel['deg']
        old_mod = wheel['s_mod']

        new_angle, mod = smallestAngleChange(old_angle, wheel['s_mod'], new_angle)

        wheel['old'] = old_angle
        wheel['deg'] = new_angle
        wheel['s_mod'] = mod

        wheel['deg_stop'] = False
    except:
        wheel['deg_stop'] = True


def handleSpeed(wheel, wheelCal, speedStr):
    wheelNumber = wheel['name']

    if speedStr == "0":
        if DEBUG_SPEED_VERBOSE:
            print("    got speed 0 @ for " + str(wheelNumber))
        speed = 0
    else:
        if speedStr == "-0" or speedStr == "+0":
            if DEBUG_SPEED_VERBOSE:
                print("    got speed +0 @ for " + str(wheelNumber))
            speed = 0
        else:
            speed = float(speedStr)

        if DEBUG_SPEED_VERBOSE:
            print("    got speed " + speedStr + " @ for " + str(wheelNumber))

    wheel['speed'] = speedStr


def interpolate(value, zerostr, maxstr):
    zero = float(zerostr)
    maxValue = float(maxstr)
    return (maxValue - zero) * value + zero


def steerWheel(wheelName, curDeg, status):

    def stopAll():
        GPIO.output(enPin, GPIO.LOW)
        motor_pwm.ChangeDutyCycle(0)

    wheel = wheelMap[wheelName]
    enPin = int(wheelCalibrationMap[wheelName]['steer']['en_pin'])
    steerDir = int(wheelCalibrationMap[wheelName]['steer']['dir'])
    if "pwm" not in wheelCalibrationMap[wheelName]['steer']:
        pwm_pin = int(wheelCalibrationMap[wheelName]['steer']['pwm_pin'])
        GPIO.setup(pwm_pin, GPIO.OUT)
        motor_pwm = GPIO.PWM(pwm_pin, 1000)
        motor_pwm.start(0)
    else:
        motor_pwm = wheelCalibrationMap[wheelName]['steer']['pwm']

    if motor_pwm is not None:

        deg = int(wheel['deg'])

        if 'overheat' in wheel:
            overheat = wheel['overheat']
            now = time.time()
            if now - overheat > OVERHEAT_COOLDOWN:
                del wheel['overheat']
            else:
                stopAll()
                steer_logger.log(time.time(), bytes(wheelName, 'ascii'), STOP_OVERHEAT, curDeg, status | STATUS_ERROR_MOTOR_OVERHEAT, 0, 0, 0, 0, 0, 0, 0)
                return

        deg_stop = wheel['deg_stop']

        if deg_stop or curDeg is None or deg is None:
            stopAll()
            steer_logger.log(time.time(), bytes(wheelName, 'ascii'), STOP_NO_DATA, curDeg, status, 0, 0, 0, 0, 0, 0, 0)
        else:

            pid = wheel['pid']
            speed = pid.process(deg, curDeg)

            forward = True
            speed = speed * steerDir
            origSpeed = speed
            if speed < 0:
                forward = False
                speed = -speed

            if speed > 100.0:
                speed = 100.0
            elif speed < 1:
                speed = 0.0
                stopAll()
                steer_logger.log(time.time(), bytes(wheelName, 'ascii'), STOP_REACHED_POSITION, curDeg, status, speed, pid.last_output, pid.last_delta, pid.set_point, pid.i, pid.d, pid.last_error)
                return

            if speed > 50:
                now = time.time()
                if 'termal' in wheel:
                    termal = wheel['termal']
                    if now - termal > OVERHEAT_PROTECTION:
                        del wheel['termal']
                        wheel['overheat'] = now
                        stopAll()
                        steer_logger.log(time.time(), bytes(wheelName, 'ascii'), STOP_OVERHEAT, curDeg, status | STATUS_ERROR_MOTOR_OVERHEAT, speed, pid.last_output, pid.last_delta, pid.set_point, pid.i, pid.d, pid.last_error)
                        return
                else:
                    wheel['termal'] = now
            elif 'termal' in wheel:
                del wheel['termal']

            if forward:
                GPIO.output(enPin, GPIO.LOW)
                motor_pwm.ChangeDutyCycle(speed)
                steer_logger.log(time.time(), bytes(wheelName, 'ascii'), BACK, curDeg, status, speed, pid.last_output, pid.last_delta, pid.set_point, pid.i, pid.d, pid.last_error)
                if DEBUG_TURN:
                    print(wheelName.upper() + ": going back; " + str(deg) + "<-->" + str(curDeg) + ", s=" + str(speed) + " os=" + str(origSpeed) + ", " + pid.to_string())
            else:
                GPIO.output(enPin, GPIO.HIGH)
                motor_pwm.ChangeDutyCycle(100.0 - speed)
                steer_logger.log(time.time(), bytes(wheelName, 'ascii'), FORWARD, curDeg, status, speed, pid.last_output, pid.last_delta, pid.set_point, pid.i, pid.d, pid.last_error)
                if DEBUG_TURN:
                    print(wheelName.upper() + ": going forward; " + str(deg) + "<-->" + str(curDeg) + ", s=" + str(speed) + " os=" + str(origSpeed) + ", " + pid.to_string())


def readPosition(wheelName):
    wheel = wheelMap[wheelName]
    i2cAddress = int(wheelCalibrationMap[wheelName]['deg']["i2c"])
    try:
        i2cBus.write_byte(I2C_MULTIPLEXER_ADDRESS, i2cAddress)
        try:
            pos = i2cBus.read_i2c_block_data(I2C_AS5600_ADDRESS, 0x0B, 5)
            angle = (pos[3] * 256 + pos[4]) * 360 // 4096
            status = pos[0] & 0b00111000 | STATUS_ERROR_MAGNET_NOT_DETECTED

            if DEBUG_READ:
                print("Read wheel " + wheelName + " @ address " + str(i2cAddress) + " pos " + str(angle) + " " + ("MH" if status & 8 else "  ") + " " + ("ML" if status & 16 else "  ") + " " + ("MD" if status & 32 else "  "))

            return angle, status
        except:
            if DEBUG_READ:
                print("Failed to read " + wheelName + " @ address " + str(i2cAddress))

        return 0, STATUS_ERROR_I2C_READ

    except:
        if DEBUG_READ:
            print("Failed to select " + wheelName + " @ address " + str(i2cAddress))

        return 0, STATUS_ERROR_I2C_WRITE


def prepareAndSteerWheel(wheelName):
    angle, status = readPosition(wheelName)
    if DBEUG_ERRORS and status & 24 != 0:
        print(wheelName + ": position (raw) " + str(angle) + " " + ("MH" if status & 8 else "  ") + " " + ("ML" if status & 16 else "  ") + " " + ("MD" if status & 32 else "  "))

    wheel = wheelMap[wheelName]
    posDir = int(wheelCalibrationMap[wheelName]['deg']['dir'])
    if posDir < 0:
        angle = 360 - angle

    if status == 1:
        return 0, status

    caloffset = int(wheelCalibrationMap[wheelName]['deg']['0'])
    angle -= caloffset
    if angle < 0:
        angle += 360

    steerWheel(wheelName, angle, status)

    if 'overheat' in wheel:
        status |= STATUS_ERROR_MOTOR_OVERHEAT

    return angle, status


def prepareAndDriveWheel(wheelName):
    wheel = wheelMap[wheelName]
    wheelSpeedCalMap = wheelCalibrationMap[wheelName]['speed']

    address = wheelSpeedCalMap['nrf']

    started_time = time.time()
    nRF2401.setReadPipeAddress(0, address)
    nRF2401.setWritePipeAddress(address)

    speedStr = wheel['speed']
    speedModStr = wheel['s_mod']

    try:
        speed = int(float(speedStr)) * int(speedModStr)
    except:
        speed = None

    if speed is not None:
        send_speed = int(127 - (speed * 127 / 300))

        data = nRF2401.padToSize([MSG_TYPE_SET_RAW_BR, send_speed, send_speed], NRF_PACKET_SIZE)
        nRF2401.swithToTX()
        done = nRF2401.sendData(data, 0.015)
        if done:
            nRF2401.swithToRX()
            nRF2401.startListening()
            if nRF2401.poolData(0.0025):  # 1 sec / 50 times a second / 4 wheels / 2 max half of time needed for wheel
                p = nRF2401.receiveData(NRF_PACKET_SIZE)
                nRF2401.stopListening()

                drive_mode = p[0]
                drive_speed = p[1]
                wheel_speed = p[2]
                wheel_pos = p[3] + 256 * p[4]
                wheel_pos_deg = int(wheel_pos * 360 / 4096)
                wheel_r_pos = p[5] + 256 * p[6]
                pid_p = p[7]
                pid_i = p[8]
                pid_d = p[9]
                i2c_status = p[10]
                pwm_reg = p[11]

                now = time.time()
                drive_logger.log(now, bytes(wheelName, 'ASCII'), wheel_pos_deg, 0, (now- started_time), speed)
                return wheel_pos_deg, 0
            else:
                now = time.time()
                drive_logger.log(now, bytes(wheelName, 'ASCII'), 0, STATUS_ERROR_RX_FAILED, (now - started_time), speed)
                return 0, STATUS_ERROR_RX_FAILED
        else:
            now = time.time()
            drive_logger.log(now, bytes(wheelName, 'ASCII'), 0, STATUS_ERROR_TX_FAILED, (now - started_time), speed)
            return 0, STATUS_ERROR_TX_FAILED


def driveAllWheels():
    if not shutdown:
        checkPidsChanged()

        angleFl, statusSteerFl = prepareAndSteerWheel("fl")
        angleFr, statusSteerFr = prepareAndSteerWheel("fr")
        angleBl, statusSteerBl = prepareAndSteerWheel("bl")
        angleBr, statusSteerBr = prepareAndSteerWheel("br")

        odoFl, statusSpeedFl = prepareAndDriveWheel("fl")
        odoFr, statusSpeedFr = prepareAndDriveWheel("fr")
        odoBl, statusSpeedBl = prepareAndDriveWheel("bl")
        odoBr, statusSpeedBr = prepareAndDriveWheel("br")

        statusFl = statusSteerFl | statusSpeedFl
        statusFr = statusSteerFr | statusSpeedFr
        statusBl = statusSteerBl | statusSpeedBl
        statusBr = statusSteerBr | statusSpeedBr

        message = ",".join([str(f) for f in [angleFl, odoFl, statusFl, angleFr, odoFr, statusFr, angleBl, odoBl, statusBl, angleBr, odoBr, statusBr]])
        pyroslib.publish("wheel/status", message)


def driveWheels():
    if not shutdown:

        odoFl, statusSpeedFl = prepareAndDriveWheel("fl")
        odoFr, statusSpeedFr = prepareAndDriveWheel("fr")
        odoBl, statusSpeedBl = prepareAndDriveWheel("bl")
        odoBr, statusSpeedBr = prepareAndDriveWheel("br")

        message = ",".join([str(f) for f in [time.time(), odoFl, statusSpeedFl, odoFr, statusSpeedFr, odoBl, statusSpeedBl, odoBr, statusSpeedBr]])
        pyroslib.publish("wheel/speed/status", message)


def steerWheels():
    if not shutdown:
        checkPidsChanged()

        angleFl, statusSteerFl = prepareAndSteerWheel("fl")
        angleFr, statusSteerFr = prepareAndSteerWheel("fr")
        angleBl, statusSteerBl = prepareAndSteerWheel("bl")
        angleBr, statusSteerBr = prepareAndSteerWheel("br")

        message = ",".join([str(f) for f in [time.time(), angleFl, statusSteerFl, angleFr, statusSteerFr, angleBl, statusSteerBl, angleBr, statusSteerBr]])
        pyroslib.publish("wheel/deg/status", message)


def driveThreadMain():
    while not shutdown:
        try:
            starting = time.time()
            driveWheels()
            now = time.time()
            if now - starting < 0.02:
                time.sleep(now - starting)
            else:
                time.sleep(0.01)
        except BaseException as e:
            print("ERROR: drive.thread: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))

    print("drive.thread: Shutdown detected.")


def wheelDegTopic(topic, payload, groups):
    wheelName = groups[0]

    if wheelName in wheelMap:
        wheel = wheelMap[wheelName]
        wheelCal = wheelCalibrationMap[wheelName]

        if DEBUG_TURN:
            print("  Turning wheel: " + wheelName + " to " + str(payload) + " degs")

        handleDeg(wheel, wheelCal['deg'], payload)

    else:
        print("ERROR: no wheel with name " + wheelName + " fonund.")


def wheelSpeedTopic(topic, payload, groups):
    wheelName = groups[0]

    if wheelName in wheelMap:
        wheel = wheelMap[wheelName]
        wheelCal = wheelCalibrationMap[wheelName]

        if DEBUG_SPEED:
            print("  Setting wheel: " + wheelName + " speed to " + str(payload))
        handleSpeed(wheel, wheelCal['speed'], payload)
    else:
        print("ERROR: no wheel with name " + wheelName + " fonund.")


def wheelsCombined(topic, payload, groups):
    if DEBUG_SPEED:
        print(str(int(time.time() * 1000) % 10000000) + ": wheels " + payload)

    wheelCmds = payload.split(" ")
    for wheelCmd in wheelCmds:
        kv = wheelCmd.split(":")
        if len(kv) > 1:
            wheelName = kv[0][:2]
            command = kv[0][2]
            value = kv[1]

            if wheelName in wheelMap:
                wheel = wheelMap[wheelName]
                wheelCal = wheelCalibrationMap[wheelName]
                if command == "s":
                    handleSpeed(wheel, wheelCal['speed'], value)
                elif command == "d":
                    handleDeg(wheel, wheelCal['deg'], float(value))


def handleShutdownAnnounced(topic, payload, groups):
    global shutdown
    shutdown = True
    stopAllWheels()


if __name__ == "__main__":
    try:
        print("Starting wheels service...")
        print("    initialising wheels...")
        initWheels()

        print("    setting GPIOs...")
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        print("    sbscribing to topics...")
        pyroslib.subscribe("wheel/all", wheelsCombined)
        pyroslib.subscribe("wheel/+/deg", wheelDegTopic)
        pyroslib.subscribe("wheel/+/speed", wheelSpeedTopic)
        pyroslib.subscribe("shutdown/announce", handleShutdownAnnounced)
        pyroslib.init("wheels-service")

        print("  Loading storage details...")
        loadStorage()
        updateWheelsPid()

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

        driveThread = threading.Thread(target=driveThreadMain, daemon=True)
        driveThread.start()

        pyroslib.forever(0.02, steerWheels)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
