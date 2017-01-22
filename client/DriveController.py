import paho.mqtt.client as mqtt
import pygame, sys, threading, os, random
import agent

pygame.init()
bigFont = pygame.font.SysFont("apple casual", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600,600))

client = mqtt.Client("DriveController#" + str(random.randint(1000, 9999)))

roverAddress = ["172.24.1.184", "172.24.1.185", "172.24.1.186", "gcc-wifi-ap", "gcc-wifi-ap", "gcc-wifi-ap"]
roverPort = [1883, 1883, 1883, 1884, 1885, 1886]
selectedRover = 1

speeds = [50, 75, 100, 150, 200, 250, 300]
selectedSpeed = 1
connected = False

def onConnect(client, data, rc):
    global connected
    if rc == 0:
        print("DriveController: Connected to rover " + selectedRoverTxt + " @ " + roverAddress[selectedRover] + ".");
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

rects = {
    "UP": pygame.Rect(200, 0, 200, 200),
    "DOWN": pygame.Rect(200, 400, 200, 200),
    "LEFT": pygame.Rect(0, 200, 200, 200),
    "RIGHT": pygame.Rect(400, 200, 200, 200),
    "SPEED": pygame.Rect(200, 200, 200, 200),
}



straight = True
stopped = True

danceTimer = 0
speed = 50

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
            print("Set speed to: " + str(speed))

    keys = pygame.key.get_pressed()

    client.loop(1/40)
    screen.fill((0, 0, 0))

    if keys[pygame.K_w]:
        client.publish("drive", "forward>" + str(speed))
        pygame.draw.rect(screen, (255, 255, 255), rects["UP"])
        stopped = False
    elif keys[pygame.K_s]:
        client.publish("drive", "back>" + str(speed))
        pygame.draw.rect(screen, (255, 255, 255), rects["DOWN"])
        stopped = False
    elif keys[pygame.K_a]:
        client.publish("drive", "crabLeft>" + str(speed))
        pygame.draw.rect(screen, (255, 255, 255), rects["LEFT"])
        stopped = False
    elif keys[pygame.K_d]:
        client.publish("drive", "crabRight>" + str(speed))
        pygame.draw.rect(screen, (255, 255, 255), rects["RIGHT"])
        stopped = False
    elif keys[pygame.K_q]:
        client.publish("drive", "pivotLeft>" + str(speed))
        pygame.draw.rect(screen, (255, 255, 255), rects["LEFT"])
        stopped = False
    elif keys[pygame.K_e]:
        client.publish("drive", "pivotRight>" + str(speed))
        pygame.draw.rect(screen, (255, 255, 255), rects["RIGHT"])
        stopped = False
    elif keys[pygame.K_x]:
        client.publish("drive", "align")
        pygame.draw.rect(screen, (255, 255, 255), rects["UP"])
        pygame.draw.rect(screen, (255, 255, 255), rects["DOWN"])
    elif keys[pygame.K_c]:
        client.publish("drive", "align")
        pygame.draw.rect(screen, (255, 255, 255), rects["UP"])
        pygame.draw.rect(screen, (255, 255, 255), rects["DOWN"])
    elif keys[pygame.K_v]:
        client.publish("drive", "slant")
        pygame.draw.rect(screen, (255, 255, 255), rects["LEFT"])
        pygame.draw.rect(screen, (255, 255, 255), rects["RIGHT"])
    elif keys[pygame.K_SPACE]:
        if danceTimer >= 10:
            client.publish("drive", "slant")
            pygame.draw.rect(screen, (255, 255, 255), rects["UP"])
            pygame.draw.rect(screen, (255, 255, 255), rects["DOWN"])
            pygame.draw.rect(screen, (255, 255, 255), rects["LEFT"])
            pygame.draw.rect(screen, (255, 255, 255), rects["RIGHT"])
        elif danceTimer <= 10:
            client.publish("drive", "align")
    elif keys[pygame.K_UP]:
        client.publish("drive", "motors>" + str(speed))
        stopped = False
    elif keys[pygame.K_DOWN]:
        client.publish("drive", "motors>" + str(-speed))
        stopped = False
    elif keys[pygame.K_LEFTBRACKET]:
        if selectedSpeed > 0:
            selectedSpeed = selectedSpeed - 1
        speed = speeds[selectedSpeed]
    elif keys[pygame.K_RIGHTBRACKET]:
        if selectedSpeed < len(speeds) - 1:
            selectedSpeed = selectedSpeed + 1
        speed = speeds[selectedSpeed]
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
    else:
        if not stopped:
            client.publish("drive", "stop")
            stopped = True

    value = speed + 155
    if (value > 255):
        value = 255
    elif value < 1:
        value = 0

    pygame.draw.rect(screen, (value, value, value), rects["SPEED"])

    selectedRoverTxt = str(selectedRover + 2)
    if selectedRover > 2:
        selectedRoverTxt = str(selectedRover - 1) + "-proxy"

    if connected:
        text = bigFont.render("Connected to rover: " + selectedRoverTxt + " @ " + roverAddress[selectedRover], 1, (128, 255, 128))
    else:
        text = bigFont.render("Connecting to rover: " + selectedRoverTxt + " @ " + roverAddress[selectedRover], 1, (255, 128, 128))
    screen.blit(text, pygame.Rect(0, 0, 0, 0))

    text = bigFont.render("Speed: " + str(speed), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 40, 0, 0))

    text = bigFont.render("Stopped: " + str(stopped), 1, (255, 255, 255))
    screen.blit(text, pygame.Rect(0, 80, 0, 0))

    pygame.display.flip()
    frameclock.tick(30)