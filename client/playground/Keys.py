
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import paho.mqtt.client as mqtt
import pygame, sys, threading, os, random
import time

last_keys = []
current_keys = []
mode = 2
mode2started = False


pygame.init()
screen = pygame.display.set_mode((300, 200))
client = mqtt.Client("DriveController#" + str(random.randint(1000, 9999)))

roverAddress = ["10.170.1.59", "172.24.1.184", "172.24.1.185", "172.24.1.186"]
selectedRover = 2

def onConnect(client, data, flags, rc):
    global connected
    if rc == 0:
        print("DriveController: Connected to rover " + str(selectedRover + 2) + " @ " + roverAddress[selectedRover] + ".");
        agent.init(client, "DriveAgent.py")
        connected = True
    else:
        print("DriveController: Connection returned error result: " + str(rc))
        os._exit(rc)

def onMessage(client, data, msg):
    global exit

    if agent.process(msg):
        if agent.returncode("DriveAgent") != None:
            exit = True
    else:
        print("DriveController: Wrong topic '" + msg.topic + "'")

def _reconnect():
    client.reconnect()

def connect():
    global connected
    connected = False
    client.disconnect()
    print("DriveController: Connecting to rover " + str(selectedRover + 2) + " @ " + roverAddress[selectedRover] + "...");

    # client.connect(roverAddress[selectedRover], 1883, 60)
    client.connect_async(roverAddress[selectedRover], 1883, 60)
    thread = threading.Thread(target=_reconnect)
    thread.daemon = True
    thread.start()

def onDisconnect(client, data, rc):
    connect()

def wheelsTurn(deg):
    client.publish("wheel/fl/deg", deg)
    client.publish("wheel/fr/deg", deg)
    client.publish("wheel/br/deg", "0")
    client.publish("wheel/bl/deg", "0")

client.on_disconnect = onDisconnect
client.on_connect = onConnect
client.on_message = onMessage

connect()
timer = 0

global current_speed, wheelPosIndex
current_speed = 100

wheelPos = ["-60", "-45", "-30", "-15", "0", "15", "30", "45", "60"]
wheelPosIndex = 1

def Left():
    global current_speed, wheelPosIndex
    wheelPosIndex -= 1
    if wheelPosIndex < 0:
        wheelPosIndex = 0
    wheelsTurn(wheelPos[wheelPosIndex])
def Right():
    global current_speed, wheelPosIndex
    wheelPosIndex += 1
    if wheelPosIndex > len(wheelPos) - 1:
        wheelPosIndex = len(wheelPos) - 1
    print(wheelPos[wheelPosIndex])
    wheelsTurn(wheelPos[wheelPosIndex])

def UP1():
    global current_speed, wheelPosIndex
    speed = speed + 50
    if speed > 200:
        speed = 200
    client.publish("wheel/fl/speed", str(speed))
    client.publish("wheel/fr/speed", str(speed))
    client.publish("wheel/bl/speed", str(speed))
    client.publish("wheel/br/speed", str(speed))
def BACK():
    global current_speed, wheelPosIndex
    speed = speed - 50
    if speed < -200:
        speed = -200
    client.publish("wheel/fl/speed", "-100")
    client.publish("wheel/fr/speed", "-100")
    client.publish("wheel/bl/speed", "-100")
    client.publish("wheel/br/speed", "-100")
def STOP():
    global current_speed, wheelPosIndex
    client.publish("wheel/fl/speed", str(0))
    client.publish("wheel/fr/speed", str(0))
    client.publish("wheel/bl/speed", str(0))
    client.publish("wheel/br/speed", str(0))

while True:
    pygame.time.Clock().tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
    last_keys = current_keys
    current_keys = pygame.key.get_pressed()
    #mode = input("What mode do you want")
    if mode == 1:
        mode = 1

    if mode == 2:
        if mode2started:
            timer = timer + 1
            if timer < 3:
                UP1()
            elif timer > 3 and timer < 6:
                STOP()
            elif timer > 6:
                timer = 0


    if current_keys != last_keys:
        if current_keys[pygame.K_LEFT]:
            Left()
        elif current_keys[pygame.K_RIGHT]:
            Right()
            wheelsTurn(wheelPos[wheelPosIndex])
        elif current_keys[pygame.K_UP]:
            print("mode=" + str(mode) + ", timer=" + str(timer))
            if mode == 1:
                UP1()
            if mode == 2:
                mode2started = True


        elif current_keys[pygame.K_DOWN]:
            BACK()
        else:
            mode2started = False
            STOP()

        if current_keys[pygame.K_o]:
            current_speed = current_speed - 50
            print("Speed " + str(current_speed))
        if current_keys[pygame.K_p]:
            current_speed = current_speed + 50
            print("Speed " + str(current_speed))


    pygame.display.flip()
