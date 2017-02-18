
import sys
import pygame
import pyros
import pyros.gcc
import pyros.agent as agent
import pyros.pygamehelper


SCALE = 10

pygame.init()
bigFont = pygame.font.SysFont("arial", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((640, 480))

feedback = ""

angle = 15
distance = 10
speed = 10


def connected():
    pyros.agent.init(pyros.client, "fine-drive-agent.py")


def feedbackMessage(topic, message, groups):
    global feedback

    feedback = message


def onKeyDown(key):
    global angle, distance, speed, feedback

    if key == pygame.K_ESCAPE:
        pyros.publish("finemove/stop", "stop")
        pyros.loop(0.7)
        sys.exit(0)
    elif key == pygame.K_SPACE:
        pyros.publish("finemove/stop", "stop")
        print("** STOP!!!")
    elif key == pygame.K_UP:
        feedback = "** FORWARD"
        pyros.publish("finemove/forward", distance)
        print("** FORWARD")
    elif key == pygame.K_DOWN:
        feedback = "** BACK"
        pyros.publish("finemove/back", distance)
        print("** BACK")
    elif key == pygame.K_LEFT:
        feedback = "** ROTATE LEFT"
        pyros.publish("finemove/rotate", str(-angle))
        print("** ROTATE LEFT")
    elif key == pygame.K_RIGHT:
        feedback = "** ROTATE RIGHT"
        pyros.publish("finemove/rotate", str(angle))
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
        pyros.publish("finemove/forwardcont", str(speed))
        print("** FORWARD CONT")
    elif key == pygame.K_s:
        feedback = "** BACK"
        pyros.publish("finemove/backcont", str(speed))
        print("** BACK")
    else:
        pyros.gcc.handleConnectKeys(key)


def onKeyUp(key):
    global feedback

    if key == pygame.K_w:
        feedback = "** STOP"
        pyros.publish("finemove/stop", "stop")
        print("** STOP")
    elif key == pygame.K_s:
        feedback = "** STOP"
        pyros.publish("finemove/stop", "stop")
        print("** STOP")
    return


pyros.subscribe("finemove/feedback", feedbackMessage)
pyros.init("drive-controller-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)

while True:
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

    text = bigFont.render("Angle: " + str(angle), 1, (255, 255, 255))
    screen.blit(text, (0, 60))

    text = bigFont.render("Distance: " + str(distance), 1, (255, 255, 255))
    screen.blit(text, (300, 60))

    text = bigFont.render("Speed: " + str(speed), 1, (255, 255, 255))
    screen.blit(text, (300, 120))

    text = bigFont.render(feedback, 1, (255, 255, 255))
    screen.blit(text, (0, 180))

    pygame.display.flip()
    frameclock.tick(30)
