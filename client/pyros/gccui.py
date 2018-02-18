#
# Copyright 2016-2018 Games Creators Club
#
# MIT License
#

import pygame
import os
import inspect

GREY = (160, 160, 160)
WHITE = (255, 255, 255)
LIGHT_BLUE = (160, 255, 255)
GREEN = (128, 255, 128)
RED = (255, 128, 128)

smallFont = None
font = None
bigFont = None

frameclock = pygame.time.Clock()
screen = None
backgroundImage = None
scaledBackground = None


def _thisPath(filename):
    return os.path.join(os.path.dirname(__file__), filename)


def initAll(screenSize, loadBackground = False):
    global screen, backgroundImage, scaledBackground
    global smallFont, font, bigFont

    pygame.init()

    fontFile = _thisPath("garuda.ttf")
    bigFont = pygame.font.Font(fontFile, 20)
    font = pygame.font.Font(fontFile, 16)
    smallFont = pygame.font.Font(fontFile, 12)

    screen = pygame.display.set_mode(screenSize)

    if loadBackground:
        backgroundImage = pygame.image.load(_thisPath("blue-background.png"))
        scaledBackground = pygame.transform.scale(backgroundImage, screen.get_size())


def screenResized(size):
    global scaledBackground

    scaledBackground = pygame.transform.scale(backgroundImage, size)


def background():
    if scaledBackground is not None:
        screen.blit(scaledBackground, (0, 0))
    else:
        screen.fill((0, 0, 0))


def frameEnd():
    pygame.display.flip()
    frameclock.tick(30)


def drawKeyValue(key, value, x, y, colour = WHITE):
    screen.blit(font.render(key + ":", 1, colour), (x, y))
    screen.blit(font.render(value, 1, colour), (x + 100, y))
    return y + 20  # font.get_height()


def drawSmall(text, pos, colour = WHITE):
    screen.blit(smallFont.render(text, 1, colour), pos)


def drawRect(pos, size, colour = LIGHT_BLUE, stick = 0, outside = 1):

    pygame.draw.line(screen, colour, (pos[0] - stick, pos[1] - outside), (pos[0] + size[0] + stick, pos[1] - outside))
    pygame.draw.line(screen, colour, (pos[0] - stick, pos[1] + size[1] + outside), (pos[0] + size[0] + stick, pos[1] + size[1] + outside))

    pygame.draw.line(screen, colour, (pos[0] - outside, pos[1] - stick), (pos[0] - outside, pos[1] + size[1] + stick))
    pygame.draw.line(screen, colour, (pos[0] + size[0] + outside, pos[1] - stick), (pos[0] + size[0] + outside, pos[1] + size[1] + stick))


def drawFilledRect(pos, size, colour = LIGHT_BLUE):
    pygame.draw.rect(screen, colour, pygame.Rect(pos, size))


def drawImage(image, pos, stick = 6):
    screen.blit(image, pos)

    drawRect(pos, image.get_size(), stick = stick, outside = 1)