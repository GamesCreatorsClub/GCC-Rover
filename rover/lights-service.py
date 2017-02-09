#!/usr/bin/python3

import sys
import traceback
import time
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt

#
# lights service
#
# This service is responsible switching LEDs on and off.
#

DEBUG = False
CAMERA_LIGHT_GPIO = 16

lightsState = False


def setLights(state):
    global lightsState

    lightsState = state
    GPIO.output(CAMERA_LIGHT_GPIO, state)


def onConnect(mqttClient, data, rc):
    if rc == 0:
        mqttClient.subscribe("lights/camera", 0)
    else:
        print("ERROR: Connection returned error result: " + str(rc))
        sys.exit(rc)


def onMessage(mqttClient, data, msg):
    payload = str(msg.payload, 'utf-8')
    topic = msg.topic

    if topic.startswith("lights/"):
        topicsplit = topic.split("/")
        if topicsplit[1] == "camera":
            if "on" == payload or "ON" == payload or "1" == payload:
                setLights(True)
            else:
                setLights(False)


#
# Initialisation
#

if __name__ == "__main__":
    try:
        print("Starting lights service...")

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(CAMERA_LIGHT_GPIO, GPIO.OUT)

        client = mqtt.Client("lights-service")
        client.on_connect = onConnect
        client.on_message = onMessage

        client.connect("localhost", 1883, 60)

        print("Started lights service.")

        while True:
            try:
                for i in range(0, 10):
                    time.sleep(0.045)
                    client.loop(0.005)
            except Exception as ex:
                print("ERROR: Got exception in main loop; " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
