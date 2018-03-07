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
ARDUINO = False
# the arduino version requires the code uploading to the arduino and this connecting
# to the i2c pins of the RPi.

TRIG = 11  # Originally was 23
ECHO = 8   # Originally was 24

SERVO_NUMBER = 8
SERVO_SPEED = 0.14 * 3  # 0.14 seconds per 60º (expecting servo to be twice as slow as per specs

i2c_bus = smbus.SMBus(1)
i2c_address = 0x04

lastServoAngle = 0

semaphore = threading.Semaphore()
pulse_start = 0
pulse_end = 0
edge = False


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
    global lastServoAngle
    # angle is between -90 and 90
    angle += 150
    angle = int(angle)

    try:
        # send as a list containing 1 item
        i2c_bus.write_i2c_block_data(i2c_address, 0, [angle])

        angleDistance = abs(lastServoAngle - angle)
        sleepAmount = SERVO_SPEED * angleDistance / 60.0

        if DEBUG:
            print("Moved servo to angle " + str(angle) + " for distance " + str(angleDistance) + " so sleepoing for " + str(sleepAmount))

        # wait for servo to reach the destination
        time.sleep(sleepAmount)

        lastServoAngle = angle

    except IOError as e:
        print("Failed to move servo on arduino")


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
        return readDistancesArduino()[0]
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

    # read from device 'address', offset 1 byte, 4 bytes
    try:
        values = i2c_bus.read_i2c_block_data(i2c_address, 1, 4)
    except IOError as e:
        print(e)

    # unpack the two bytes into a short
    distances = (values[0]+values[1]*0x100, values[2]+values[3]*0x100)

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
        pyroslib.init("sonar-sensor-service")

        print("Started sonar sensor service.")

        pyroslib.forever(0.02)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))

    finally:
        GPIO.cleanup()
