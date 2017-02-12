import sys
import threading
import time
import random
import pygame
import paho.mqtt.client as mqtt
from PIL import Image


pygame.init()
bigFont = pygame.font.SysFont("arial", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((1024, 600))

client = mqtt.Client("gyro-display-#" + str(random.randint(1000, 9999)))

roverAddress = ["172.24.1.184", "172.24.1.185", "172.24.1.186", "gcc-wifi-ap", "gcc-wifi-ap", "gcc-wifi-ap"]
roverPort = [1883, 1883, 1883, 1884, 1885, 1886]
selectedRover = 0

rawImage = pygame.Surface((80, 64), 24)
processedImage = pygame.Surface((80, 64), 24)
whiteBalanceImage = pygame.Surface((80, 64), 24)

rawImageBig = pygame.Surface((320, 256), 24)
processedImageBig = pygame.Surface((320, 256), 24)
whiteBalanceImageBig = pygame.Surface((320, 256), 24)

gyroAngle = 0.0

selectedRoverTxt = ""
connected = False

whiteBalanceImageBig = pygame.image.load("arrow.png")


continuousMode = False

def toPyImage(imageBytes):
    pilImage = Image.frombytes("L", (80, 64), imageBytes)
    pilRGBImage = Image.new("RGB", pilImage.size)
    pilRGBImage.paste(pilImage)
    pyImageSmall = pygame.image.fromstring(pilRGBImage.tobytes("raw"), (80, 64), 'RGB')
    pyImageBig = pygame.transform.scale(pyImageSmall, (320, 256))
    return (pyImageSmall, pyImageBig)


def onConnect(client, data, rc):
    global connected
    if rc == 0:
        print("DriveController: Connected to rover " + selectedRoverTxt + " @ " + roverAddress[selectedRover] + ".");

        client.subscribe("camera/raw")
        client.subscribe("camera/processed")
        client.subscribe("camera/whitebalance")

        connected = True
    else:
        print("DriveController: Connection returned error result: " + str(rc))
        sys.exit(rc)


def onMessage(client, data, msg):
    global gyroAngle, whiteBalanceImage, whiteBalanceImageBig, rawImage, rawImageBig, processedImage, processedImageBig

    topic = msg.topic

    print("Got message on " + topic)
    if topic == "camera/whitebalance":

        images = toPyImage(msg.payload)
        whiteBalanceImage = images[0]
        whiteBalanceImageBig = images[1]
        print("  Converted images for white balance.")

    elif topic == "camera/raw":

        images = toPyImage(msg.payload)
        rawImage = images[0]
        rawImageBig = images[1]
        print("  Converted images for raw.")

    elif topic == "camera/processed":

        images = toPyImage(msg.payload)
        processedImage = images[0]
        processedImageBig = images[1]
        print("  Converted images for processed.")

        if continuousMode:
            client.publish("camera/processed/fetch")

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
    elif keys[pygame.K_w]:
        print("  fetching white balance picture...")
        client.publish("camera/whitebalance/fetch")
    elif keys[pygame.K_r]:
        print("  fetching white balance picture...")
        client.publish("camera/raw/fetch")
    elif keys[pygame.K_p]:
        print("  fetching white balance picture...")
        client.publish("camera/processed/fetch")
    elif keys[pygame.K_s]:
        print("  storing whitebalance image...")
        client.publish("camera/whitebalance/store")
        client.publish("camera/whitebalance/fetch")
    elif keys[pygame.K_c]:
        continuousMode = not continuousMode

    selectedRoverTxt = str(selectedRover + 2)
    if selectedRover > 2:
        selectedRoverTxt = str(selectedRover - 1) + "-proxy"

    if connected:
        text = bigFont.render("Connected to rover: " + selectedRoverTxt + " @ " + roverAddress[selectedRover], 1, (128, 255, 128))
    else:
        text = bigFont.render("Connecting to rover: " + selectedRoverTxt + " @ " + roverAddress[selectedRover], 1, (255, 128, 128))

    screen.blit(text, (0, 0))

    text = bigFont.render("Continuous mode: " + str(continuousMode), 1, (255, 128, 128))
    screen.blit(text, (300, 50))

    screen.blit(rawImage, (10, 50))
    screen.blit(whiteBalanceImage, (110, 50))
    screen.blit(processedImage, (210, 50))

    screen.blit(rawImageBig, (10, 150))
    screen.blit(whiteBalanceImageBig, (362, 150))
    screen.blit(processedImageBig, (724, 150))

    pygame.display.flip()
    frameclock.tick(30)
