
import sys
import paho.mqtt.client as mqtt
import subprocess
import time

#
# shutdown service
#
# This service is responsible shutting down Linux.
#

storageMap = {}
wheelMap = {}
wheelCalibrationMap = {}

lightsState = False


DEBUG = False

client = mqtt.Client("shutdown-service")


def setLights(state):
    global lightsState

    # lightsState = state
    # GPIO.output(CAMERA_LIGHT_GPIO, state)
    pass


def prepareToShutdown():
    previousLightsState = lightsState
    seconds = 0.0
    interval = 0.3
    state = True
    while seconds <= 6.0:
    # while seconds <= 6.0 and GPIO.input(SWITCH_GPIO) == 0:
        time.sleep(interval)
        seconds = seconds + interval
        setLights(state)
        state = not state

    # if GPIO.input(SWITCH_GPIO) == 0:
    #     doShutdown()
    # else:
    #     setLights(previousLightsState)
    doShutdown()


def doShutdown():
    print("Shutting down now!")
    subprocess.call(["/usr/bin/sudo", "/sbin/shutdown", "-h", "now"])


def handleSystemMessages(topic, payload):
    print("Got system message on " + topic + ": " + payload)
    if topic == "shutdown" and payload == "secret_message":
        doShutdown()


def onConnect(client, data, rc):
    try:
        if rc == 0:
            client.subscribe("servo/+", 0)
            client.subscribe("wheel/+/deg", 0)
            client.subscribe("wheel/+/speed", 0)
            client.subscribe("storage/write/#", 0)
            client.subscribe("storage/read", 0)
        else:
            print("ERROR: Connection returned error result: " + str(rc))
            sys.exit(rc)
    except Exception as e:
        print("ERROR: Got exception on connect; " + str(e))


def onMessage(client, data, msg):
    global dist

    try:
        payload = str(msg.payload, 'utf-8')
        topic = msg.topic

        if topic.startswith("system/"):
            handleSystemMessages(topic[7:], payload)

    except Exception as e:
        print("ERROR: Got exception on message; " + str(e))


#
# Initialisation
#

print("Starting shutdown-service...")

client.on_connect = onConnect
client.on_message = onMessage

client.connect("localhost", 1883, 60)

print("Started shutdown-service.")

while True:
    try:
        client.loop(0.5)
    except Exception as e:
        print("ERROR: Got exception in main loop; " + str(e))
