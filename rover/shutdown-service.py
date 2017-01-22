
import sys
import paho.mqtt.client as mqtt
import subprocess
import time
import RPi.GPIO as GPIO

#
# shutdown service
#
# This service is responsible shutting down Linux.
#

lightsState = False

DEBUG = False

SWITCH_GPIO = 20

client = mqtt.Client("shutdown-service")

GPIO.setmode(GPIO.BCM)
GPIO.setup(SWITCH_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def setLights(state):
    global lightsState

    if state:
        client.publish("lights/camera", "on")
        print("Switched lights on")
    else:
        client.publish("lights/camera", "off")
        print("Switched lights off")
    client.loop(0.005)


def prepareToShutdown():
    print("Preparing to shut down...")
    previousLightsState = lightsState
    seconds = 0.0
    interval = 0.3
    state = True
    lastSeconds = int(seconds)

    currentSwtich = GPIO.input(SWITCH_GPIO)
    previousSwitch = currentSwtich

    while seconds <= 6.0 and not (previousSwitch == 0 and currentSwtich == 1):
        time.sleep(interval)
        seconds = seconds + interval
        setLights(state)
        state = not state
        if lastSeconds != int(seconds):
            lastSeconds = int(seconds)
            print("Preparing to shut down... " + str(lastSeconds))

        previousSwitch = currentSwtich
        currentSwtich = GPIO.input(SWITCH_GPIO)

    if not (previousSwitch == 0 and currentSwtich == 1):
        doShutdown()
    else:
        setLights(previousLightsState)


def doShutdown():
    print("Shutting down now!")
    try:
        # subprocess.call(["/usr/bin/sudo", "/sbin/shutdown", "-h", "now"])
        pass
    except Exception as e:
        print("ERROR: Failed to shutdown; " + str(e))

def onConnect(client, data, rc):
    try:
        if rc == 0:
            client.subscribe("system/shutdown", 0)
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

        if payload == "secret_message":
            prepareToShutdown()

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
        for i in range(0, 10):
            time.sleep(0.045)
            client.loop(0.005)
        if GPIO.input(SWITCH_GPIO) == 0:
            prepareToShutdown()
    except Exception as e:
        print("ERROR: Got exception in main loop; " + str(e))
