
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import RPi.GPIO as GPIO
import time
import traceback
import random
import sys
import paho.mqtt.client as mqtt

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

TRIG = 11  # 23
ECHO = 8   # 24

SERVO_NUMBER = 8

GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

GPIO.output(TRIG, False)

print("Waiting for sensor to settle")

time.sleep(1)

connected = False

client = mqtt.Client("radar-agent-#" + str(random.randint(1000, 9999)))

def moveServo(angle):
    # angle is between -90 and 90
    angle += 150
    angle = int(angle)

    f = open("/dev/servoblaster", 'w')
    f.write(str(SERVO_NUMBER) + "=" + str(angle) + "\n")
    f.close()


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


def onConnect(mqttClient, data, flags, rc):
    global connected
    try:
        if rc == 0:
            connected = True

            #
            # Subscribe to the topic goes here
            #
            client.subscribe("scan/start")

        else:
            print("ERROR: Connection returned error result: " + str(rc))
            sys.exit(rc)

    except Exception as ex:
        print("ERROR: Got exception on connect; " + str(ex))


def onMessage(mqttClient, data, msg):
    global wheelsStopped

    try:
        payload = str(msg.payload, 'utf-8')
        topic = msg.topic

        #
        # Reading distance and sending data back (publish) goes here
        #
        if topic == "scan/start":
            moveServo(float(payload))
            time.sleep(1)
            distance = readDistance()
            print ("   distance =" + str(distance))
            client.publish("scan/data" , str(distance))

    except Exception as ex:
        print("ERROR: Got exception on message; " + str(ex))


try:
    print("Connecting to the broker.")

    client.on_connect = onConnect
    client.on_message = onMessage

    client.connect("localhost", 1883, 60)

    while not connected:
        client.loop()

    print("Connected to the broker.")

    while True:
        for it in range(0, 10):
            time.sleep(0.0015)
            client.loop(0.0005)

except Exception as ex:
    print("ERROR: " + str(ex))
    print("ERROR: " + traceback.format_exception(ex))
finally:
    GPIO.cleanup()
