import sys
import threading
import time
import random
import pygame
import paho.mqtt.client as mqtt


pygame.init()
bigFont = pygame.font.SysFont("arial", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600,600))
arrow_image = pygame.image.load("arrow.png")

client = mqtt.Client("gyro-display-#" + str(random.randint(1000, 9999)))

roverAddress = ["172.24.1.184", "172.24.1.185", "172.24.1.186", "gcc-wifi-ap", "gcc-wifi-ap", "gcc-wifi-ap"]
roverPort = [1883, 1883, 1883, 1884, 1885, 1886]
selectedRover = 3

gyroAngle = 0.0

connected = False


def onConnect(client, data, rc):
    global connected
    if rc == 0:
        print("DriveController: Connected to rover " + selectedRoverTxt + " @ " + roverAddress[selectedRover] + ".");

        client.subscribe("sensor/gyro")
        client.publish("sensor/gyro/continuous", "")

        connected = True
    else:
        print("DriveController: Connection returned error result: " + str(rc))
        sys.exit(rc)


def onMessage(client, data, msg):
    global gyroAngle

    payload = str(msg.payload, 'utf-8')
    topic = msg.topic

    if topic == "sensor/gyro":
        gyroAngle += float(payload)
        # print("Got gyro " + payload)


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

resubscribe = time.time()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    keys = pygame.key.get_pressed()

    for it in range(0, 30):
        time.sleep(0.0005)
        client.loop(0.0005)
    screen.fill((0, 0, 0))

    if keys[pygame.K_ESCAPE]:
        sys.exit()
    elif keys[pygame.K_2]:
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

    selectedRoverTxt = str(selectedRover + 2)
    if selectedRover > 2:
        selectedRoverTxt = str(selectedRover - 1) + "-proxy"

    if connected:
        text = bigFont.render("Connected to rover: " + selectedRoverTxt + " @ " + roverAddress[selectedRover], 1, (128, 255, 128))
    else:
        text = bigFont.render("Connecting to rover: " + selectedRoverTxt + " @ " + roverAddress[selectedRover], 1, (255, 128, 128))

    screen.blit(text, (0, 0))

    loc = arrow_image.get_rect().center
    rot_arrow_image = pygame.transform.rotate(arrow_image, -gyroAngle)
    rot_arrow_image.get_rect().center = loc

    screen.blit(rot_arrow_image, (150, 150))


    pygame.display.flip()
    frameclock.tick(30)

    if time.time() - resubscribe > 2:
        resubscribe = time.time()
        if connected:
            client.publish("sensor/gyro/continuous", "")
            print("Re-subscribed")