
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import sys
import pygame
import pyros
import pyros.gcc
import pyros.gccui
import pyros.pygamehelper


wheelsMap = {"fl": {"deg": 0, "speed": 0},
             "fr": {"deg": 0, "speed": 0},
             "bl": {"deg": 0, "speed": 0},
             "br": {"deg": 0, "speed": 0}}

screen = None
font10 = None
font20 = None
font30 = None
font40 = None
font50 = None
boxes = None
client = None
gotoAng = None
gotoRPM = None
last_keys = None
wheelfr = None
wheelfl = None
wheelbr = None
wheelbl = None
frameclock = None
selected = None
address = None
emStop = None
mousePos = None


def handleWheelPosition(topic, message, groups):
    global wheelsMap

    topicsplit = topic.split("/")
    wheelName = topicsplit[1]

    wheelName = groups[0]

    wheelsMap[wheelName]["deg"] = message
    # print("Got deg for wheel", wheelName)


def handleWheelSpeed(topic, message, groups):
    global wheelsMap

    wheelName = groups[0]
    wheelsMap[wheelName]["speed"] = message
    # print("Got speed for wheel", wheelName)


def processLine(wheelName, line):
    global wheelsMap

    splitline = line.split(",")
    if not len(splitline) == 3:
        print("Received an invalid value for " + wheelName)
    else:
        wheelsMap[wheelName][splitline[0]][splitline[1]] = splitline[2]


def sendMessage(topic, value):
    pyros.publish(topic, value)


def rotate(image, angle):
    """Rotate an image while keeping its center and size.
    Stolen from http://www.pygame.org/wiki/RotateCenter"""
    loc = image.get_rect().center  # rot_image is not defined
    rot_sprite = pygame.transform.rotate(image, angle)
    rot_sprite.get_rect().center = loc
    return rot_sprite


def init():
    global screen, font10, font20, font30, font40, font50
    global boxes, client, gotoAng, gotoRPM
    global wheelfr, wheelfl, wheelbr, wheelbl
    global frameclock, selected, address

    screen = pyros.gccui.initAll((1024, 768), True)
    font = pyros.gccui.font
    bigFont = pyros.gccui.bigFont

    pygame.display.set_caption("GCC Robot Controller")

    pyros.subscribe("wheel/+/deg", handleWheelPosition)
    pyros.subscribe("wheel/+/speed", handleWheelSpeed)
    pyros.init("instrument-display-#", unique=True, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)

    # last_keys = pygame.key.get_pressed()

    pygame.display.set_caption("Robot Gui")
    
    font10 = pygame.font.SysFont("Arial", 10)
    font20 = pygame.font.SysFont("Arial", 20)
    font30 = pygame.font.SysFont("Arial", 30)
    font40 = pygame.font.SysFont("Arial", 40)
    font50 = pygame.font.SysFont("Arial", 50)

    wheelfr = pygame.image.load("Wheel.png")
    wheelfl = pygame.image.load("Wheel.png")
    wheelbr = pygame.image.load("Wheel.png")
    wheelbl = pygame.image.load("Wheel.png")


def Text(text, size, position, colour):
    text = str(text)
    if size == 10:
        font = font10
    elif size == 20:
        font = font20
    elif size == 30:
        font = font30
    elif size == 40:
        font = font40
    elif size == 50:
        font = font50
    else:
        font = 10

    font_colour = pygame.Color(colour)
    rendered_text = font.render(text, 1, font_colour).convert_alpha()
    
    screen.blit(rendered_text, position)


def drawScreen():
    global emStop
    
    # Box top left
    pygame.draw.rect(screen, (150, 150, 150), (0, 0, 1024 / 2, 768 / 2))
    
    # Box bottom right
    pygame.draw.rect(screen, (150, 150, 150), (1024 / 2, 768 / 2, 1024 / 2, 768 / 2))

    # Robot Middle
    pygame.draw.rect(screen, (150, 150, 255), (1024 * 0.75 - 42, 768 * 0.75 - 60, 100, 150))

    # =======###Les wheels###====== #
    pos1 = (1024 * 0.75 - 50, 768 * 0.75 - 75)
    pos2 = (1024 * 0.75 + 50, 768 * 0.75 - 75)
    pos3 = (1024 * 0.75 - 50, 768 * 0.75 + 75)
    pos4 = (1024 * 0.75 + 50, 768 * 0.75 + 75)
    # fr
    wheel1 = rotate(wheelfr, 90 + float(wheelsMap["fr"]["deg"]))
    screen.blit(wheel1, pos1)
    
    # fl
    wheel2 = rotate(wheelfl, 90 + float(wheelsMap["fl"]["deg"]))
    screen.blit(wheel2, pos2)
    
    # br
    wheel3 = rotate(wheelfr, 90 + float(wheelsMap["br"]["deg"]))
    screen.blit(wheel3, pos3)
    
    # bl
    wheel4 = rotate(wheelfl, 90 + float(wheelsMap["bl"]["deg"]))
    screen.blit(wheel4, pos4)
    
    Text("Radar", 30, (0, 30), "#ffffff")
    Text("Radar", 30, (1024 / 2, 0), "#ffffff")

    degColour = "#58ccde"
    Text("Deg", 30, (512, 768 / 2), degColour)
    Text("FL:" + str(wheelsMap["fl"]["deg"]), 20, (512, 768 / 2 + 30), degColour)
    Text("FR:" + str(wheelsMap["fr"]["deg"]), 20, (512 + 80, 768 / 2 + 30), degColour)
    
    Text("BL:" + str(wheelsMap["bl"]["deg"]), 20, (512, 768 / 2 + 50), degColour)
    Text("BR:" + str(wheelsMap["br"]["deg"]), 20, (512 + 80, 768 / 2 + 50), degColour)

    speed1 = round(float(wheelsMap["fl"]["speed"]), 1)
    speed2 = round(float(wheelsMap["fr"]["speed"]), 1)
    speed3 = round(float(wheelsMap["bl"]["speed"]), 1)
    speed4 = round(float(wheelsMap["br"]["speed"]), 1)

    speedColour = "#7ff188"
    Text("Speed", 30, (512, 768 / 2 + 100), speedColour)
    Text("FL:" + str(speed1), 20, (512, 768 / 2 + 130), speedColour)
    Text("FR:" + str(speed2), 20, (512 + 80, 768 / 2 + 130), speedColour)
    
    Text("BL:" + str(speed3), 20, (512, 768 / 2 + 150), speedColour)
    Text("BR:" + str(speed4), 20, (512 + 80, 768 / 2 + 150), speedColour)

    pygame.display.flip()


def onKeyDown(key):
    if pyros.gcc.handleConnectKeyDown(key):
        pass


def onKeyUp(key):
    if pyros.gcc.handleConnectKeyUp(key):
        pass


init()

while True:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)
    pyros.gccui.background(True)

    mousePos = pygame.mouse.get_pos()

    drawScreen()

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()
