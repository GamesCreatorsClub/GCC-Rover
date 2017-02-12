import paho.mqtt.client as mqtt
import pygame, sys, threading, os, random
import pyros.agent as agent

client = mqtt.Client("St8")


pygame.init()
bigFont = pygame.font.SysFont("apple casual", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600,600))


def onConnect(client, data, rc):
    print("Received connect callback. rc=" + str(rc))
    if rc == 0:
        agent.init(client, "straightLine-agent.py")
        pass

def onMessage(client, data, msg):
    global exit

    if agent.process(client, msg):
        if agent.returncode("straightLine-agent") != None:
            exit = True
    else:
        print("DriveController: Wrong topic '" + msg.topic + "'")

client.on_connect = onConnect
client.on_message = onMessage
client.connect("gcc-rover-2", 1883, 60)

def onKeyDown(key):

    if key == pygame.K_UP:
        client.publish("straight", "forward")
        print("fwd")
    if key == pygame.K_DOWN:
        client.publish("straight", "stop")
        print("stppd")
    if key == pygame.K_r:
        client.publish("straight", "calibrate")
        print("calibrating")
    return

def onKeyUp(key):
    return

lastkeys = []
keys = []
t = 0

client.publish("straight", "calibrate")

while True:
    client.loop(1.0/60)
    t += 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            client.publish("straight", "stop")
            pygame.quit()
            sys.exit()
    lastkeys = keys
    keys = pygame.key.get_pressed()
    if not len(keys) == 0 and not len(lastkeys) == 0:

        for i in range(0, len(keys) - 1):

            if keys[i] and not lastkeys[i]:
                onKeyDown(i)
            if not keys[i] and lastkeys[i]:
                onKeyUp(i)

    # if t % 5 == 0:
    #     client.publish("wheel/fl/angle", str(0))
    #     client.publish("wheel/bl/angle", skeystr(0))
    #     client.publish("wheel/fr/angle", str(0))
    #     client.publish("wheel/br/angle", str(0))

    screen.fill((0, 0, 0))
    pygame.display.flip()
    frameclock.tick(30)