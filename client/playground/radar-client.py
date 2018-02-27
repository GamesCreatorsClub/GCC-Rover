
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import pygame, sys, threading, random
import paho.mqtt.client as mqtt
import pyros
import pyros.gcc
import pyros.gccui
import pyros.agent as agent
import time

screen = pyros.gccui.initAll((600, 600), True)
font = pyros.gccui.font
bigFont = pyros.gccui.bigFont

client = mqtt.Client("radar-client-#" + str(random.randint(1000, 9999)))

roverAddress = ["172.24.1.184", "172.24.1.185", "172.24.1.186", "gcc-wifi-ap", "gcc-wifi-ap", "gcc-wifi-ap"]
roverPort = [1883, 1883, 1883, 1884, 1885, 1886]
selectedRover = 3

connected = False
stopped = False
distance = ""
received = True

RADAR_AGENT = "radar-agent"


def onConnect(c, data, flags, rc):
    global connected
    if rc == 0:
        agent.init(c, RADAR_AGENT + ".py")
        connected = True
        c.subscribe("scan/data")
    else:
        print("DriveController: Connection returned error result: " + str(rc))
        sys.exit(rc)


def onMessage(client, data, msg):
    global exit, distance, received

    if agent.process(client, msg):
        if agent.returncode(RADAR_AGENT) != None:
            exit = True
    else:
        payload = str(msg.payload, 'utf-8')
        topic = msg.topic
        if topic == "scan/data":
            print("** distance = " + payload)
            distance = payload
            received = True


def _reconnect():
    client.reconnect()


def connect():
    global connected
    connected = False
    client.disconnect()
    print("DriveController: Connecting to rover " + str(selectedRover + 2) + " @ " + roverAddress[selectedRover] + "...")

    client.connect_async(roverAddress[selectedRover], roverPort[selectedRover], 60)
    thread = threading.Thread(target=_reconnect)
    thread.daemon = True
    thread.start()


def onDisconnect(client, data, rc):
    connect()


client.on_disconnect = onDisconnect
client.on_connect = onConnect
client.on_message = onMessage

connect()
angle = 0


def onKeyDown(key):
    global angle, stopped, received

    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif keys[pygame.K_ESCAPE]:
        client.publish("drive", "stop")
        agent.stopAgent(client, RADAR_AGENT)
        client.loop(0.7)
    elif keys[pygame.K_SPACE]:
        if not stopped:
            client.publish("drive", "stop")
            agent.stopAgent(client, RADAR_AGENT)
            stopped = True
    elif keys[pygame.K_s]:
        if received:
            received = False
            client.publish("scan/start", str(angle))
            print("** asked for distance")
    elif keys[pygame.K_o]:
        angle -= 1
        if angle < -90:
            angle = -90
    elif keys[pygame.K_p]:
        angle += 1
        if angle > 90:
            angle = 90


def onKeyUp(key):
    if pyros.gcc.handleConnectKeyUp(key):
        pass


while True:
    for it in range(0, 10):
        time.sleep(0.0015)
        client.loop(0.0005)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    keys = pygame.key.get_pressed()

    pyros.loop(0.03)
    pyros.gccui.background(True)

    text = bigFont.render("Stopped: " + str(stopped), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(10, 80, 0, 0))

    text = bigFont.render("Angle: " + str(angle), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(10, 140, 0, 0))

    text = bigFont.render("Distance: " + str(distance), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(10, 180, 0, 0))

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()
