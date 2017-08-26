#!/usr/bin/python3

print("At the beginning")

import traceback
import pyroslib
import RPi.GPIO as GPIO


print("After imports")

#
# wheels service
#
#
# This service is responsible for moving wheels on the rover.
# Current implementation also handles:
#     - servos
#     - storage map
#


DEBUG = True
motorSpeed = 0

def moveServo(servoid, angle):
    # TODO move this out to separate service
    f = open("/dev/servoblaster", 'w')
    f.write(str(servoid) + "=" + str(angle) + "\n")
    f.close()


def setMotorSpeed():
    print(str(motorSpeed))
    if motorSpeed < 0:
        print("23-1, 21-0")
        # GPIO.output(23, 1)
        # GPIO.output(21, 0)
        forwardPWM.ChangeDutyCycle(0)
        backPWM.ChangeDutyCycle(-motorSpeed / 3)
    elif motorSpeed > 0:
        print("21-1, 23-0")
        # GPIO.output(21, 1)
        # GPIO.output(23, 0)
        forwardPWM.ChangeDutyCycle(motorSpeed / 3)
        backPWM.ChangeDutyCycle(0)
    else:
        print("23-0, 21-0")
        # GPIO.output(21, 0)
        # GPIO.output(23, 0)
        forwardPWM.ChangeDutyCycle(0)
        backPWM.ChangeDutyCycle(0)


def servoTopic(topic, payload, groups):
    servo = int(groups[0])
    moveServo(servo, payload)


def steeringTopic(topic, payload, groups):
    moveServo(0, payload)


def motorTopic(topic, payload, groups):
    global motorSpeed
    motorSpeed = int(payload)
    setMotorSpeed()


if __name__ == "__main__":
    try:
        print("Starting wheels service...")

        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)

        GPIO.setup(23, GPIO.OUT)
        GPIO.setup(21, GPIO.OUT)

        forwardPWM = GPIO.PWM(21, 50)
        backPWM = GPIO.PWM(23, 50)

        forwardPWM.start(0)
        backPWM.start(0)

        print("Set GPIO")

        pyroslib.subscribe("steering", steeringTopic)
        pyroslib.subscribe("servo/+", servoTopic)
        pyroslib.subscribe("motor", motorTopic)
        pyroslib.init("wheels-service")
        print("  Loading storage details")

        print("Started wheels service.")

        pyroslib.forever(0.5)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
