
import sys
import pygame
import pyros
import pyros.gcc
import pyros.agent as agent
import pyros.pygamehelper
import math


pygame.init()
bigFont = pygame.font.SysFont("arial", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600, 600))

speeds = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 20, 30, 35, 40, 42, 43, 44, 45, 50, 75, 100, 125, 150, 175, 200, 250, 300]
selectedSpeed = 4


def connected():
    pyros.agent.init(pyros.client, "drive-agent.py")


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
currentSpeed = 50


def onKeyDown(key):
    global currentSpeed, selectedSpeed, stopped

    if key == pygame.K_ESCAPE:
        sys.exit()
    elif key == pygame.K_w:
        pyros.publish("move/drive", "0 " + str(currentSpeed))
        pygame.draw.rect(screen, (255, 255, 255), rects["UP"])
        stopped = False
    elif key == pygame.K_s:
        pyros.publish("move/drive", "180 " + str(currentSpeed))
        pygame.draw.rect(screen, (255, 255, 255), rects["DOWN"])
        stopped = False
    elif key == pygame.K_a:
        pyros.publish("move/drive", "-90 " + str(currentSpeed))
        pygame.draw.rect(screen, (255, 255, 255), rects["LEFT"])
        stopped = False
    elif key == pygame.K_d:
        pyros.publish("move/drive", "90 " + str(currentSpeed))
        pygame.draw.rect(screen, (255, 255, 255), rects["RIGHT"])
        stopped = False
    elif key == pygame.K_q:
        pyros.publish("move/rotate", str(-currentSpeed))
        pygame.draw.rect(screen, (255, 255, 255), rects["LEFT"])
        stopped = False
    elif key == pygame.K_e:
        pyros.publish("move/rotate", str(currentSpeed))
        pygame.draw.rect(screen, (255, 255, 255), rects["RIGHT"])
        stopped = False
    elif key == pygame.K_x:
        pyros.publish("drive", "align")
        pygame.draw.rect(screen, (255, 255, 255), rects["UP"])
        pygame.draw.rect(screen, (255, 255, 255), rects["DOWN"])
    elif key == pygame.K_c:
        pyros.publish("drive", "align")
        pygame.draw.rect(screen, (255, 255, 255), rects["UP"])
        pygame.draw.rect(screen, (255, 255, 255), rects["DOWN"])
    elif key == pygame.K_v:
        pyros.publish("drive", "slant")
        pygame.draw.rect(screen, (255, 255, 255), rects["LEFT"])
        pygame.draw.rect(screen, (255, 255, 255), rects["RIGHT"])
    elif key == pygame.K_SPACE:
        pyros.publish("move", "stop")
    elif key == pygame.K_UP:
        pyros.publish("drive", "motors>" + str(currentSpeed))
        stopped = False
    elif key == pygame.K_DOWN:
        pyros.publish("drive", "motors>" + str(-currentSpeed))
        stopped = False
    elif key == pygame.K_LEFTBRACKET:
        if selectedSpeed > 0:
            selectedSpeed -= 1
        currentSpeed = speeds[selectedSpeed]
    elif key == pygame.K_RIGHTBRACKET:
        if selectedSpeed < len(speeds) - 1:
            selectedSpeed += 1
        currentSpeed = speeds[selectedSpeed]
    else:
        pyros.gcc.handleConnectKeys(key)


def onKeyUp(key):
    global stopped
    if not stopped:
        pyros.publish("move/drive", str(round(angleFromCentre, 1) + " 0"))
        print("stop")
        stopped = True


pyros.init("drive-controller-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)

mousePos = [0, 0]
mouseDown = False

angleFromCentre = 0
distanceFromCentre = 0

centre = [300, 300]

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.MOUSEMOTION:
            mousePos = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouseDown = True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            mouseDown = False

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)

    screen.fill((0, 0, 0))

    if mouseDown:
        stopped = False
        angleFromCentre = math.atan2((mousePos[0] - centre[0]), -(mousePos[1] - centre[1])) * 180 / math.pi
        distanceFromCentre = math.sqrt((mousePos[0] - centre[0]) * (mousePos[0] - centre[0]) + (mousePos[1] - centre[1]) * (mousePos[1] - centre[1])) / 10

        print("angle: " + str(angleFromCentre) + "   distance: " + str(distanceFromCentre))

        pyros.publish("move/drive", str(round(angleFromCentre, 1)) + " " + str(int(distanceFromCentre)))
    else:
        stopped = True
        pyros.publish("move/drive", str(round(angleFromCentre, 1)) + " 0")

    value = currentSpeed + 155
    if value > 255:
        value = 255
    elif value < 1:
        value = 0

    pygame.draw.rect(screen, (value, value, value), rects["SPEED"])

    if pyros.isConnected():
        text = bigFont.render("Connected to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (128, 255, 128))
    else:
        text = bigFont.render("Connecting to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (255, 128, 128))
    screen.blit(text, (0, 0))

    text = bigFont.render("Speed: " + str(currentSpeed), 1, (255, 255, 255))
    screen.blit(text, (0, 40))

    text = bigFont.render("Stopped: " + str(stopped), 1, (255, 255, 255))
    screen.blit(text, (0, 80))

    pygame.display.flip()
    frameclock.tick(30)
