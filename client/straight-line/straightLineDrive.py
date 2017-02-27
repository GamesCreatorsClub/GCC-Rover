
import sys
import pygame
import pyros
import pyros.gcc
import pyros.agent
import pyros.pygamehelper


pygame.init()
bigFont = pygame.font.SysFont("apple casual", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600, 600))


def connected():
    pyros.agent.init(pyros.client, "straightLine-agent.py")
    print("Sent agent")


def onKeyDown(key):

    if key == pygame.K_ESCAPE:
        pyros.publish("straight", "stop")
        pyros.loop(0.7)
        sys.exit(0)
    elif key == pygame.K_UP:
        pyros.publish("straight", "forward")
        print("fwd")
    elif key == pygame.K_RETURN:
        pyros.publish("straight", "calibrate-and-go")
        print("fwd")
    elif key == pygame.K_DOWN or key == pygame.K_SPACE:
        pyros.publish("straight", "stop")
        print("stppd")
    elif key == pygame.K_r:
        pyros.publish("straight", "calibrate")
        print("calibrating")
    else:
        pyros.gcc.handleConnectKeys(key)
    return


def onKeyUp(key):
    return


t = 0

pyros.publish("straight", "calibrate")
pyros.init("straight-line-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)


while True:
    t += 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pyros.publish("straight", "stop")
            pyros.loop(0.7)
            pygame.quit()
            sys.exit()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)

    screen.fill((0, 0, 0))

    if pyros.isConnected():
        text = bigFont.render("Connected to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (128, 255, 128))
    else:
        text = bigFont.render("Connecting to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (255, 128, 128))

    screen.blit(text, (0, 0))

    pygame.display.flip()
    frameclock.tick(30)
