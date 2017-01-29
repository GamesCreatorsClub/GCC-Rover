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


client.on_connect =  onConnect
client.connect("gcc-rover-4", 1883, 60)

def onKeyDown(key):

    if key == pygame.K_UP:
        client.publish("straight", "forward")
        print("fwd")
    if key == pygame.K_DOWN:
        client.publish("straight", "stop")
        print("stppd")
    return

def onKeyUp(key):
    return

lastkeys = []
keys = []
while True:
    client.loop(1.0/60)
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



    screen.fill((0, 0, 0))
    pygame.display.flip()
    frameclock.tick(30)