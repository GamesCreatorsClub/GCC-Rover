
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import paho.mqtt.client as mqtt
import pygame, sys, threading, os, random
import pyros.agent as agent

pygame.init()
bigFont = pygame.font.SysFont("arial", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600,600))

client = mqtt.Client("test-maze-#" + str(random.randint(1000, 9999)))

roverAddress = ["172.24.1.184", "172.24.1.185", "172.24.1.186", "gcc-wifi-ap", "gcc-wifi-ap", "gcc-wifi-ap"]
roverPort = [1883, 1883, 1883, 1884, 1885, 1886]
selectedRover = 0

connected = False

stopped = False

MAZE_AGENT = "test-maze-agent"
DRIVE_AGENT = "auto-drive-agent"


def onConnect(client, data, rc):
    global connected
    if rc == 0:
        print("DriveController: Connected to rover " + selectedRoverTxt + " @ " + roverAddress[selectedRover] + ".");
        agent.init(client, MAZE_AGENT + ".py")
        agent.init(client, DRIVE_AGENT + ".py")
        connected = True
    else:
        print("DriveController: Connection returned error result: " + str(rc))
        os._exit(rc)

def onMessage(client, data, msg):
    global exit

    if agent.process(client, msg):
        if agent.returncode(MAZE_AGENT) != None:
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


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    keys = pygame.key.get_pressed()

    client.loop(1/40)
    screen.fill((0, 0, 0))

    if keys[pygame.K_2]:
        selectedRover = 0
        connect()
    elif keys[pygame.K_3]:
        selectedRover = 1
        connect()
    elif keys[pygame.K_4]:
        selectedRover = 2
        connect()
    elif keys[pygame.K_5]:
        selectedRover = 3
        connect()
    elif keys[pygame.K_6]:
        selectedRover = 4
        connect()
    elif keys[pygame.K_7]:
        selectedRover = 5
        connect()
    elif keys[pygame.K_ESCAPE]:
        client.publish("drive", "stop")
        agent.stopAgent(client, MAZE_AGENT)
        client.loop(0.7)
        sys.exit(0)
    elif keys[pygame.K_SPACE]:
        if not stopped:
            client.publish("drive", "stop")
            agent.stopAgent(client, MAZE_AGENT)
            stopped = True

    selectedRoverTxt = str(selectedRover + 2)
    if selectedRover > 2:
        selectedRoverTxt = str(selectedRover - 1) + "-proxy"

    if connected:
        text = bigFont.render("Connected to rover: " + selectedRoverTxt + " @ " + roverAddress[selectedRover], 1, (128, 255, 128))
    else:
        text = bigFont.render("Connecting to rover: " + selectedRoverTxt + " @ " + roverAddress[selectedRover], 1, (255, 128, 128))
    screen.blit(text, pygame.Rect(0, 0, 0, 0))

    text = bigFont.render("Stopped: " + str(stopped), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 80, 0, 0))

    pygame.display.flip()
    frameclock.tick(30)