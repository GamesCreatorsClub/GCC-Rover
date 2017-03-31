
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import pygame, sys, time, random
import paho.mqtt.client as mqtt
import math
pygame.init()

screen = pygame.display.set_mode((600,600))

frameclock = pygame.time.Clock()

afont = pygame.font.SysFont("apple casual", 48)

distance = 150.0


def generateRandomName(name):

    return name + "#" + time.strftime("%M%S")

client = mqtt.Client(generateRandomName("Demo"))


def onConnect(client, data, rc):
    if rc == 0:
        print("CONNECTED")
    else:
        print("COULD NOT CONNECT. error code: " + str(rc))


def onMessage(client, data, msg):
    topic = msg.topic
    playload = str(msg.payload, 'utf-8')


def angle1(distance):
    x= math.atan2(36.5,(distance-69))
    math.degrees(x)

    return math.degrees(x) - 90.0
def angle2(distance):
    x= math.atan2(36.5, (distance+69))
    math.degrees(x)

    return math.degrees(x) - 90.0

def sendwheels():
    client.publish("wheel/fl/deg", str(angle1(distance)))
    client.publish("wheel/fr/deg", str(-angle1(distance)))
    client.publish("wheel/bl/deg", str(angle2(distance)))
    client.publish("wheel/br/deg", str(-angle2(distance)))

    client.publish("wheel/br/speed", "0") 
   

def onKeyDown(key):
    global distance
    if key == pygame.K_o:
        distance = distance - 10
        sendwheels()
    elif key == pygame.K_p:
        distance = distance + 10
        sendwheels()
    return


def onKeyPressed(key):

    return

def onKeyUp(key):

    return

def drawText(surface, text, position, font):
    surface.blit(font.render(text, 1, (255,200,255)), position)


client.on_connect = onConnect
client.on_message = onMessage
adress = "gcc-wifi-ap"
client.disconnect()
client.connect(adress, 1886, 60)


keys = []
lastkeys = []
while True:
    for event in pygame.event.get():
       if event.type == pygame.QUIT:
           pygame.quit()
           sys.exit()
    lastkeys = keys
    keys = pygame.key.get_pressed()

    for i in range(0, len(lastkeys)):
        if keys[i]:
            onKeyPressed(i)
        if keys[i] and not lastkeys[i]:
            onKeyDown(i)
        if not keys[i] and lastkeys[i]:
            onKeyUp(i)

    screen.fill((0, 0, 0))
    drawText(screen, "Distance is " + str(distance), (16,16), afont)

    drawText(screen, "Angle1 is " + str(angle1(distance)), (16,50), afont)
    drawText(screen, "Angle2 is " + str(angle2(distance)), (16,80), afont)


    pygame.display.flip()
    frameclock.tick(30)







