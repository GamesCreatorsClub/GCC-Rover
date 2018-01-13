#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import paho.mqtt.client as mqtt
import time

client = mqtt.Client("servoagent")


def onConnect(client, data, flags, rc):
    client.subscribe("s")
    print("Servo Agent: Connected to rover")



def moveServo():
    return

def onMessage(client, data, msg):
    payload = str(msg.payload, 'utf-8')

    if msg.topic == "moveservo":
        moveServo()



client.on_connect = onConnect
client.on_message = onMessage

print("DriverAgent: Starting...")

client.connect("localhost", 1883, 60)

while True:
    for it in range(0, 10):
        time.sleep(0.0015)
        client.loop(0.0005)

