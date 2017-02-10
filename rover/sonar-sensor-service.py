#!/usr/bin/python3

import time
import traceback
import pyroslib
import RPi.GPIO as GPIO


TRIG = 11  # Originally was 23
ECHO = 8   # Originally was 24

SERVO_NUMBER = 8
SERVO_SPEED = 0.14 * 2  # 0.14 seconds per 60º (expecting servo to be twice as slow as per specs

lastServoAngle = 0


def moveServo(angle):
    global lastServoAngle
    # angle is between -90 and 90
    angle += 150
    angle = int(angle)

    f = open("/dev/servoblaster", 'w')
    f.write(str(SERVO_NUMBER) + "=" + str(angle) + "\n")
    f.close()

    angleDistance = abs(lastServoAngle - angle)

    # wait for servo to reach the destination
    time.sleep(SERVO_SPEED * angleDistance / 60.0)

    lastServoAngle = angle


def readDistance():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    start = time.time()
    while GPIO.input(ECHO) == 0 and time.time() - start < 0.1:
        pass

    pulse_start = time.time()

    while GPIO.input(ECHO) == 1 and time.time() - start < 0.3:
        pass

    pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start

    distance = pulse_duration * 171500

    distance = round(distance, 2)

    return distance


def handleScan(topic, payload, groups):
    moveServo(float(payload))
    distance = readDistance()
    # print ("   distance =" + str(distance))
    pyroslib.publish("sensor/distance", str(distance))


if __name__ == "__main__":
    try:
        print("Starting sonar sensor service...")
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(TRIG, GPIO.OUT)
        GPIO.setup(ECHO, GPIO.IN)

        GPIO.output(TRIG, False)

        print("  Waiting for sensor to settle")

        moveServo(lastServoAngle)

        time.sleep(1)

        pyroslib.subscribe("sensor/distance/scan", handleScan)
        pyroslib.init("sonar-sensor-service")

        print("Started sonar sensor service.")

        pyroslib.forever(0.02)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))

    finally:
        GPIO.cleanup()
