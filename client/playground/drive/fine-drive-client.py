
import pygame
import sys
import threading
import random
import paho.mqtt.client as mqtt
import time
import pyros.agent as agent

SCALE = 10

pygame.init()
bigFont = pygame.font.SysFont("arial", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((640, 480))

client = mqtt.Client("sonar-client-#" + str(random.randint(1000, 9999)))

roverAddress = ["172.24.1.184", "172.24.1.185", "172.24.1.186", "gcc-wifi-ap", "gcc-wifi-ap", "gcc-wifi-ap"]
roverPort = [1883, 1883, 1883, 1884, 1885, 1886]
selectedRover = 0

connected = False

selectedRoverTxt = ""
feedback = ""

def onConnect(clnt, data, rc):
    global connected
    if rc == 0:
        print("DriveController: Connected to rover " + selectedRoverTxt + " @ " + roverAddress[selectedRover] + ".")
        connected = True
        agent.init(clnt, "fine-drive-agent.py")
        client.subscribe("finemove/feedback")
    else:
        print("DriveController: Connection returned error result: " + str(rc))
        sys.exit(rc)


def onMessage(c, data, msg):
    global feedback

    payload = str(msg.payload, 'utf-8')
    topic = msg.topic
    if agent.process(client, msg):
        if agent.returncode("fine-drive-agent") != None:
            exit = True
    elif topic == "finemove/feedback":
        feedback = payload

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


def onDisconnect(c, data, rc):
    connect()


client.on_disconnect = onDisconnect
client.on_connect = onConnect
client.on_message = onMessage

connect()
angle = 15
distance = 10
speed = 10

def onKeyDown(key):
    global selectedRover, angle, distance, speed, feedback

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
        client.publish("finemove/stop", "stop")
        client.loop(0.7)
        sys.exit(0)
    elif key == pygame.K_SPACE:
        client.publish("finemove/stop", "stop")
        print("** STOP!!!")
    elif key == pygame.K_UP:
        feedback = "** FORWARD"
        client.publish("finemove/forward", distance)
        print("** FORWARD")
    elif key == pygame.K_DOWN:
        feedback = "** BACK"
        client.publish("finemove/back", distance)
        print("** BACK")
    elif key == pygame.K_LEFT:
        feedback = "** ROTATE LEFT"
        client.publish("finemove/rotate", str(-angle))
        print("** ROTATE LEFT")
    elif key == pygame.K_RIGHT:
        feedback = "** ROTATE RIGHT"
        client.publish("finemove/rotate", str(angle))
        print("** ROTATE RIGHT")
    elif key == pygame.K_LEFTBRACKET:
        angle -= 15
    elif key == pygame.K_RIGHTBRACKET:
        angle += 15
    elif key == pygame.K_o:
        distance -= 5
    elif key == pygame.K_p:
        distance += 5
    elif key == pygame.K_k:
        speed -= 1
    elif key == pygame.K_l:
        speed += 1
    elif key == pygame.K_w:
        feedback = "** FORWARD CONT"
        client.publish("finemove/forwardcont", str(speed))
        print("** FORWARD CONT")
    elif key == pygame.K_s:
        feedback = "** BACK"
        client.publish("finemove/backcont", str(speed))
        print("** BACK")

    return


def onKeyUp(key):
    if key == pygame.K_w:
        feedback = "** STOP"
        client.publish("finemove/stop", "stop")
        print("** STOP")
    elif key == pygame.K_s:
        feedback = "** STOP"
        client.publish("finemove/stop", "stop")
        print("** STOP")
    return


lastkeys = []
keys = []


while True:
    for it in range(0, 10):
        time.sleep(0.0015)
        client.loop(0.0005)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
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

    client.loop(1/40)
    screen.fill((0, 0, 0))

    selectedRoverTxt = str(selectedRover + 2)
    if selectedRover > 2:
        selectedRoverTxt = str(selectedRover - 1) + "-proxy"

    if connected:
        text = bigFont.render("Connected to rover: " + selectedRoverTxt + " @ " + roverAddress[selectedRover], 1, (128, 255, 128))
    else:
        text = bigFont.render("Connecting to rover: " + selectedRoverTxt + " @ " + roverAddress[selectedRover], 1, (255, 128, 128))
    screen.blit(text, pygame.Rect(0, 0, 0, 0))

    text = bigFont.render("Angle: " + str(angle), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 60, 0, 0))

    text = bigFont.render("Distance: " + str(distance), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(300, 60, 0, 0))

    text = bigFont.render("Speed: " + str(speed), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(300, 120, 0, 0))

    text = bigFont.render(feedback, 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 180, 0, 0))

    pygame.display.flip()
    frameclock.tick(30)
