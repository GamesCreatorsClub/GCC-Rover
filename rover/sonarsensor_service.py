#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import time
import traceback
import threading
import pyroslib
import RPi.GPIO as GPIO
import smbus # for i2c comms

DEBUG = False
ARDUINO = True
# the arduino version requires the code uploading to the arduino and this connecting
# to the i2c pins of the RPi.

TRIG = 11  # Originally was 23
ECHO = 8   # Originally was 24

CONTINUOUS_MODE_TIMEOUT = 3  # 5 seconds before giving up on sending accel data out
MAX_TIMEOUT = 0.05  # 0.02 is 50 times a second so this is 20 times a second

SERVO_NUMBER = 8
SERVO_SPEED = 0.14 * 3  # 0.14 seconds per 60º (expecting servo to be twice as slow as per specs

DEBUG_LEVEL_OFF = 0
DEBUG_LEVEL_INFO = 1
DEBUG_LEVEL_ALL = 2
DEBUG_LEVEL = DEBUG_LEVEL_INFO

i2c_bus = smbus.SMBus(1)
i2c_address = 0x04

timing = 100

lastServoAngle = 0
newServoAngle = 0

stopVariable = 0

doReadSensor = False
continuousMode = False
lastTimeRead = 0
lastTimeReceivedRequestForContMode = 0
started = time.time()

tof = None
lastRead = time.time()

twoSensorsMode = True
initialised = False

semaphore = threading.Semaphore()
pulse_start = 0
pulse_end = 0
edge = False


def log(level, where, what):
    if level <= DEBUG_LEVEL:
        t = round(time.time() - started, 4)
        print("{0:>18} {1}: {2}".format(t, where, what))


def moveServo(angle):
    if ARDUINO:
        moveServoArduino(angle)
    else:
        moveServoRpi(angle)


def moveServoRpi(angle):
    global lastServoAngle
    # angle is between -90 and 90
    angle += 150
    angle = int(angle)

    f = open("/dev/servoblaster", 'w')
    f.write(str(SERVO_NUMBER) + "=" + str(angle) + "\n")
    f.close()

    angleDistance = abs(lastServoAngle - angle)
    sleepAmount = SERVO_SPEED * angleDistance / 60.0

    if DEBUG:
        print("Moved servo to angle " + str(angle) + " for distance " + str(angleDistance) + " so sleepoing for " + str(sleepAmount))

    # wait for servo to reach the destination
    time.sleep(sleepAmount)

    lastServoAngle = angle


def moveServoArduino(angle):
    pass
    #
    # global lastServoAngle
    # # angle is between -90 and 90
    # angle += 150
    # angle = int(angle)
    #
    # try:
    #     # send as a list containing 1 item
    #     i2c_bus.write_i2c_block_data(i2c_address, 0, [angle])
    #
    #     angleDistance = abs(lastServoAngle - angle)
    #     sleepAmount = SERVO_SPEED * angleDistance / 60.0
    #
    #     if DEBUG:
    #         print("Moved servo to angle " + str(angle) + " for distance " + str(angleDistance) + " so sleepoing for " + str(sleepAmount))
    #
    #     # wait for servo to reach the destination
    #     time.sleep(sleepAmount)
    #
    #     lastServoAngle = angle
    #
    # except IOError as e:
    #     print("Failed to move servo on arduino")


def edgeDetect(pin):
    global pulse_start, pulse_end, edge

    t = time.time()

    if edge:
        pulse_end = t
        if semaphore is not None:
            semaphore.release()
        # print("  < edge down received")
    else:
        pulse_start = t
        edge = True
        # print("  > edge up received")


# replacing the old function
def readDistance():
    if ARDUINO:
        return readDistancesArduino()
    else:
        return readDistanceRpi()


def readDistanceRpi():
    global semaphore, edge, pulse_start

    edge = False

    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    pulse_start = time.time()

    semaphore = threading.Semaphore(0)
    semaphore.acquire(blocking=True, timeout=1)

    pulse_duration = pulse_end - pulse_start

    distance = pulse_duration * 171500

    distance = round(distance, 2)

    return distance


# returns 2 distances in a tuple
def readDistancesArduino():

    # # read from device 'address', offset 1 byte, 4 bytes
    # try:
    #     values = i2c_bus.read_i2c_block_data(i2c_address, 0, 4)
    # except IOError as e:
    #     print(e)
    #
    # # unpack the two bytes into a short
    # distances = ((values[0] * 0x100 + values[1]) / 5.8 - 56, (values[2] * 0x100 + values[3]) / 5.8 - 56)
    # log(DEBUG_LEVEL_INFO, "read", hex(values[0]) + " " + hex(values[1]) + " " + hex(values[2]) + " " + hex(values[3]) + " -> " + str(distances[0]) + " " + str(distances[1]))

    # read from device 'address', offset 1 byte, 4 bytes
    try:
        values1 = i2c_bus.read_i2c_block_data(i2c_address, 0, 2)
    except IOError as e:
        print(e)
    try:
        values2 = i2c_bus.read_i2c_block_data(i2c_address, 2, 2)
    except IOError as e:
        print(e)

    # unpack the two bytes into a short
    distances = ((values1[0] * 0x100 + values1[1]) / 5.8 - 56, (values2[0] * 0x100 + values2[1]) / 5.8 - 56)
    # log(DEBUG_LEVEL_INFO, "read", hex(values1[0]) + " " + hex(values1[1]) + " " + hex(values2[0]) + " " + hex(values2[1]) + " -> " + str(distances[0]) + " " + str(distances[1]))

    return distances


def handleRead(topic, payload, groups):
    angle = float(payload)
    if DEBUG:
        print("Got read - moving to angle " + str(angle))

    moveServo(angle)
    distance = readDistance()
    # print ("   distance =" + str(distance))
    pyroslib.publish("sensor/distance", str(angle) + ":" + str(distance))


def handleScan(topic, payload, groups):
    startScan = True

    if DEBUG:
        print("Got scan...")

    distances = {}
    angle = -90
    while angle <= 90:
        moveServo(float(angle))
        distance = readDistance()
        distances[angle] = distance
        angle += 22.5

    angle = 90
    while angle >= -90:
        moveServo(float(angle))
        distance = readDistance()

        if distance < distances[angle]:
            distances[angle] = distance
        angle -= 22.5

    angles = list(distances.keys())
    angles.sort()

    distancesList = []
    for angle in angles:
        distancesList.append(str(angle) + ":" + str(distances[angle]))

    # print ("   distance =" + str(distance))
    pyroslib.publish("sensor/distance", str(",".join(distancesList)))


def handleContinuousMode(topic, message, groups):
    global doReadSensor, continuousMode, lastTimeReceivedRequestForContMode

    if message.startswith("stop"):
        continuousMode = False
        doReadSensor = False

    else:
        if not continuousMode:
            continuousMode = True
            doReadSensor = True
            log(DEBUG_LEVEL_INFO, "Message", "  Started continuous mode...")

        lastTimeReceivedRequestForContMode = time.time()


def loop():
    global doReadSensor, lastTimeRead, continuousMode, newServoAngle

    if doReadSensor:
        if lastServoAngle != newServoAngle:
            moveServo(newServoAngle)
            log(DEBUG_LEVEL_INFO, "Loop", "  Moved to the new angle " + str(newServoAngle))

        distance = readDistance()
        if twoSensorsMode:
            distance1 = distance[0]
            distance2 = distance[1]
            if distance1 > 0 or distance2 > 0:
                message = ""
                if distance1 > 0:
                    message = message + str(round(lastServoAngle, 1)) + ":" + str(int(distance1))

                if distance2 > 0:
                    if distance1 > 0:
                        message = message + ","
                    message = message + str(round(lastServoAngle - 90.0, 1)) + ":" + str(int(distance2))

                message = message + ",timestamp:" + str(time.time())

                pyroslib.publish("sensor/distance", message)
        else:
            if distance > 0:
                pyroslib.publish("sensor/distance", str(lastServoAngle) + ":" + str(distance))

        if continuousMode:
            if time.time() - lastTimeReceivedRequestForContMode > CONTINUOUS_MODE_TIMEOUT:
                continuousMode = False
                log(DEBUG_LEVEL_INFO, "Message", "  Stopped continuous mode.")
        else:
            doReadSensor = False


if __name__ == "__main__":
    try:
        print("Starting sonar sensor service...")
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(TRIG, GPIO.OUT)
        GPIO.setup(ECHO, GPIO.IN)
        GPIO.add_event_detect(ECHO, GPIO.BOTH, callback=edgeDetect)

        GPIO.output(TRIG, False)

        print("  Waiting for sensor to settle")

        moveServo(lastServoAngle)

        time.sleep(1)

        pyroslib.subscribe("sensor/distance/read", handleRead)
        pyroslib.subscribe("sensor/distance/scan", handleScan)
        pyroslib.subscribe("sensor/distance/continuous", handleContinuousMode)
        pyroslib.init("sonar-sensor-service")

        print("Started sonar sensor service.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))

    finally:
        GPIO.cleanup()
