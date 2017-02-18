
import sys
import pygame
import pyros
import pyros.gcc
import pyros.agent as agent
import pyros.pygamehelper


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
        pyros.publish("drive", "forward>" + str(currentSpeed))
        pygame.draw.rect(screen, (255, 255, 255), rects["UP"])
        stopped = False
    elif key == pygame.K_s:
        pyros.publish("drive", "back>" + str(currentSpeed))
        pygame.draw.rect(screen, (255, 255, 255), rects["DOWN"])
        stopped = False
    elif key == pygame.K_a:
        pyros.publish("drive", "crabLeft>" + str(currentSpeed))
        pygame.draw.rect(screen, (255, 255, 255), rects["LEFT"])
        stopped = False
    elif key == pygame.K_d:
        pyros.publish("drive", "crabRight>" + str(currentSpeed))
        pygame.draw.rect(screen, (255, 255, 255), rects["RIGHT"])
        stopped = False
    elif key == pygame.K_q:
        pyros.publish("drive", "pivotLeft>" + str(currentSpeed))
        pygame.draw.rect(screen, (255, 255, 255), rects["LEFT"])
        stopped = False
    elif key == pygame.K_e:
        pyros.publish("drive", "pivotRight>" + str(currentSpeed))
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
        if danceTimer >= 10:
            pyros.publish("drive", "slant")
            pygame.draw.rect(screen, (255, 255, 255), rects["UP"])
            pygame.draw.rect(screen, (255, 255, 255), rects["DOWN"])
            pygame.draw.rect(screen, (255, 255, 255), rects["LEFT"])
            pygame.draw.rect(screen, (255, 255, 255), rects["RIGHT"])
        elif danceTimer <= 10:
            pyros.publish("drive", "align")
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
    if key == pygame.K_w or key == pygame.K_s or key == pygame.K_a or key == pygame.K_d \
            or key == pygame.K_q or key == pygame.K_e or key == pygame.K_x or key == pygame.K_c \
            or key == pygame.K_v or key == pygame.K_SPACE or key == pygame.K_UP or key == pygame.K_DOWN:

        if not stopped:
            pyros.publish("drive", "stop")
            stopped = True


pyros.init("drive-controller-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort())


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)

    screen.fill((0, 0, 0))

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
