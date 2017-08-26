#!/usr/bin/python3

import traceback
import re
import copy
import pyroslib
import storagelib
import RPi.GPIO as GPIO


#
# wheels service
#
#
# This service is responsible for moving wheels on the rover.
# Current implementation also handles:
#     - servos
#     - storage map
#

DEBUG = False
GPIO.setmode(GPIO.BCM)
GPIO.setmode(GPIO.BOARD)

GPIO.setup(11, GPIO.OUT)
GPIO.setup(9, GPIO.OUT)
GPIO.setup(10, GPIO.OUT)

motorSpeed = None


def moveServo(servoid, angle):
    # TODO move this out to separate service
    f = open("/dev/servoblaster", 'w')
    f.write(str(servoid) + "=" + str(angle) + "\n")
    f.close()


def servoTopic(topic, payload, groups):
    moveServo(0, payload)


def setMotorSpeed():

    if motorSpeed < 0:
        GPIO.output(11, GPIO.HIGH)
        GPIO.output(9, GPIO.LOW)
    elif motorSpeed > 0:
        GPIO.output(9, GPIO.HIGH)
        GPIO.output(11, GPIO.LOW)
    else:
        GPIO.output(9, GPIO.LOW)
        GPIO.output(11, GPIO.LOW)

def driveMotors():
    setMotorSpeed()


def servoTopic(topic, payload, groups):
    servo = int(groups[0])
    moveServo(servo, payload)


def motorTopic(topic, payload, groups):
   motorSpeed = payload


if __name__ == "__main__":
    try:
        print("Starting wheels service...")

        pyroslib.subscribe("servo/+", servoTopic)
        pyroslib.subscribe("motor/+/speed", motorTopic)
        pyroslib.init("wheels-service")

        print("  Loading storage details")

        print("Started wheels service.")

        pyroslib.forever(0.02, driveMotors)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
