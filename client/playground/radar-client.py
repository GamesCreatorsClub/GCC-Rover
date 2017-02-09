import pygame, sys, threading, random
import paho.mqtt.client as mqtt
import pyros.agent as agent
import time

pygame.init()
bigFont = pygame.font.SysFont("arial", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600,600))

client = mqtt.Client("radar-client-#" + str(random.randint(1000, 9999)))

roverAddress = ["172.24.1.184", "172.24.1.185", "172.24.1.186", "gcc-wifi-ap", "gcc-wifi-ap", "gcc-wifi-ap"]
roverPort = [1883, 1883, 1883, 1884, 1885, 1886]
selectedRover = 3

connected = False
stopped = False
distance = ""
received = True

RADAR_AGENT = "radar-agent"


def onConnect(client, data, rc):
    global connected
    if rc == 0:
        print("DriveController: Connected to rover " + selectedRoverTxt + " @ " + roverAddress[selectedRover] + ".");
        agent.init(client, RADAR_AGENT + ".py")
        connected = True
        client.subscribe ("scan/data")
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
    print("DriveController: Connecting to rover " + str(selectedRover + 2) + " @ " + roverAddress[selectedRover] + "...");

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

while True:
    for it in range(0, 10):
        time.sleep(0.0015)
        client.loop(0.0005)

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
        agent.stopAgent(client, RADAR_AGENT)
        client.loop(0.7)
        sys.exit(0)
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

    text = bigFont.render("Angle: " + str(angle), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 140, 0, 0))

    text = bigFont.render("Distance: " + str(distance), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 180, 0, 0))

    pygame.display.flip()
    frameclock.tick(30)
