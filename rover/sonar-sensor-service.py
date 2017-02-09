#!/usr/bin/python3

import time
import traceback
import sys
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt


TRIG = 11  # Originally was 23
ECHO = 8   # Originally was 24

SERVO_NUMBER = 8
SERVO_SPEED = 0.14 * 2  # 0.14 seconds per 60º (expecting servo to be twice as slow as per specs

connected = False
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


def onConnect(mqttClient, data, rc):
    global connected

    if rc == 0:
        connected = True
        client.subscribe("sensor/distance/scan")

    else:
        print("ERROR: Connection returned error result: " + str(rc))
        sys.exit(rc)


def onMessage(mqttClient, data, msg):

    payload = str(msg.payload, 'utf-8')
    topic = msg.topic

    if topic == "sensor/distance/scan":
        moveServo(float(payload))
        distance = readDistance()
        # print ("   distance =" + str(distance))
        client.publish("sensor/distance", str(distance))


if __name__ == "__main__":
    try:
        print("Starting sonar sensor service...")
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(TRIG, GPIO.OUT)
        GPIO.setup(ECHO, GPIO.IN)

        GPIO.output(TRIG, False)

        print("Waiting for sensor to settle")

        moveServo(lastServoAngle)

        client = mqtt.Client("sonar-sensor-service")

        time.sleep(1)

        client.on_connect = onConnect
        client.on_message = onMessage

        client.connect("localhost", 1883, 60)

        print("  Waiting to connect before proceeding...")
        while not connected:
            client.loop()

        print("Started sonar sensor service.")
        while True:
            try:
                for it in range(0, 10):
                    time.sleep(0.0015)
                    client.loop(0.0005)
            except Exception as ex:
                print("ERROR: Got exception in main loop; " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))

    finally:
        GPIO.cleanup()
