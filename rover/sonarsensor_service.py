#!/usr/bin/python3

import time
import traceback
import threading
import pyroslib
import RPi.GPIO as GPIO

DEBUG = False

TRIG = 11  # Originally was 23
ECHO = 8   # Originally was 24

SERVO_NUMBER = 8
SERVO_SPEED = 0.14 * 3  # 0.14 seconds per 60º (expecting servo to be twice as slow as per specs

lastServoAngle = 0

semaphore = threading.Semaphore()
pulse_start = 0
pulse_end = 0
edge = False


def moveServo(angle):
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


def readDistance():
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
