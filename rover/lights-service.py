
import sys
import paho.mqtt.client as mqtt
import time
import RPi.GPIO as GPIO

#
# lights service
#
# This service is responsible switching LEDs on and off.
#

CAMERA_LIGHT_GPIO = 16

lightsState = False


DEBUG = False

client = mqtt.Client("lights-service")

GPIO.setmode(GPIO.BCM)
GPIO.setup(CAMERA_LIGHT_GPIO, GPIO.OUT)


def setLights(state):
    global lightsState

    lightsState = state
    GPIO.output(CAMERA_LIGHT_GPIO, state)


def onConnect(mqttClient, data, rc):
    try:
        if rc == 0:
            mqttClient.subscribe("lights/camera", 0)
        else:
            print("ERROR: Connection returned error result: " + str(rc))
            sys.exit(rc)
    except Exception as ex:
        print("ERROR: Got exception on connect; " + str(ex))


def onMessage(mqttClient, data, msg):
    try:
        payload = str(msg.payload, 'utf-8')
        topic = msg.topic

        # print("Got " + payload + " on " +topic)

        if topic.startswith("lights/"):
            topicsplit = topic.split("/")
            if topicsplit[1] == "camera":
                if "on" == payload or "ON" == payload or "1" == payload:
                    setLights(True)
                else:
                    setLights(False)

    except Exception as ex:
        print("ERROR: Got exception on message; " + str(ex))


#
# Initialisation
#

print("Starting lights service...")

client.on_connect = onConnect
client.on_message = onMessage

client.connect("localhost", 1883, 60)

print("Started lights service.")

while True:
    try:
        for i in range(0, 10):
            time.sleep(0.045)
            client.loop(0.005)
    except Exception as e:
        print("ERROR: Got exception in main loop; " + str(e))
