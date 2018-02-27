#
# Copyright 2016-2018 Games Creators Club
#
# MIT License
#

import pygame
import os
import inspect

BLACK = (0, 0, 0)
DARK_GREY = (80, 80, 80)
GREY = (160, 160, 160)
WHITE = (255, 255, 255)
LIGHT_BLUE = (160, 255, 255)
GREEN = (128, 255, 128)
RED = (255, 128, 128)
YELLOW = (255, 255, 128)
BLUE = (128, 128, 255)

smallFont = None
font = None
bigFont = None

frameclock = pygame.time.Clock()
screen = None
backgroundImage = None
scaledBackground = None

SCREEN_RECT = None


def _thisPath(filename):
    return os.path.join(os.path.dirname(__file__), filename)


def initAll(screenSize, loadBackground = False):
    global screen, backgroundImage, scaledBackground
    global smallFont, font, bigFont
    global SCREEN_RECT

    pygame.init()

    fontFile = _thisPath("garuda.ttf")
    bigFont = pygame.font.Font(fontFile, 20)
    font = pygame.font.Font(fontFile, 16)
    smallFont = pygame.font.Font(fontFile, 12)

    screen = pygame.display.set_mode(screenSize)
    SCREEN_RECT = pygame.Rect(0, 0, screen.get_width(), screen.get_height())

    if loadBackground:
        backgroundImage = pygame.image.load(_thisPath("blue-background.png"))
        scaledBackground = pygame.transform.scale(backgroundImage, screen.get_size())


def screenResized(size):
    global scaledBackground

    scaledBackground = pygame.transform.scale(backgroundImage, size)


def background(topFrame = False):
    if scaledBackground is not None:
        screen.blit(scaledBackground, (0, 0))
    else:
        screen.fill((0, 0, 0))

    if topFrame:
        drawTopFrame()


def frameEnd():
    pygame.display.flip()
    frameclock.tick(30)


def drawKeyValue(key, value, x, y, colour = WHITE):
    screen.blit(font.render(key + ":", 1, colour), (x, y))
    screen.blit(font.render(value, 1, colour), (x + 100, y))
    return y + 20  # font.get_height()


def drawBigText(text, pos, colour = WHITE):
    screen.blit(bigFont.render(text, 1, colour), pos)


def drawText(text, pos, colour = WHITE):
    screen.blit(font.render(text, 1, colour), pos)


def drawSmallText(text, pos, colour = WHITE):
    screen.blit(smallFont.render(text, 1, colour), pos)


def drawRect(pos, size, colour = LIGHT_BLUE, stick = 0, outside = 1):

    pygame.draw.line(screen, colour, (pos[0] - stick, pos[1] - outside), (pos[0] + size[0] + stick, pos[1] - outside))
    pygame.draw.line(screen, colour, (pos[0] - stick, pos[1] + size[1] + outside), (pos[0] + size[0] + stick, pos[1] + size[1] + outside))

    pygame.draw.line(screen, colour, (pos[0] - outside, pos[1] - stick), (pos[0] - outside, pos[1] + size[1] + stick))
    pygame.draw.line(screen, colour, (pos[0] + size[0] + outside, pos[1] - stick), (pos[0] + size[0] + outside, pos[1] + size[1] + stick))


def drawFrame(rect, colour = LIGHT_BLUE, backgroundColour = BLACK):
    if backgroundColour is not None:
        pygame.draw.rect(screen, backgroundColour, rect, 0)
    pygame.draw.rect(screen, colour, (rect[0] + 4, rect[1] + 4, rect[2] - 8, rect[3] - 8), 1)
    for i in range(6, 12):
        pygame.draw.line(screen, colour, (rect[0] + rect[2] - i, rect[1] + rect[3] - 6), (rect[0] + rect[2] - 6, rect[1] + rect[3] - i), 1)


def drawTopFrame(colour = LIGHT_BLUE):
    rect = SCREEN_RECT

    pygame.draw.line(screen, colour, (rect[0] + 4, rect[1] + 4), (rect[0] + 330, rect[1] + 4))
    pygame.draw.line(screen, colour, (rect[0] + 4, rect[1] + 4), (rect[0] + 4, rect[1] + 30))
    pygame.draw.line(screen, colour, (rect[0] + 4, rect[1] + 30), (rect[0] + 300, rect[1] + 30))
    pygame.draw.line(screen, colour, (rect[0] + 300, rect[1] + 30), (rect[0] + 330, rect[1] + 4))
    pygame.draw.line(screen, colour, (rect[0] + 330, rect[1] + 4), (rect[0] + rect[2] - 4, rect[1] + 4))
    pygame.draw.line(screen, colour, (rect[0] + rect[2] - 4, rect[1] + 4), (rect[0] + rect[2] - 4, rect[1] + rect[3] - 4))
    pygame.draw.line(screen, colour, (rect[0] + 4, rect[1] + rect[3] - 4), (rect[0] + rect[2] - 4, rect[1] + rect[3] - 4))
    pygame.draw.line(screen, colour, (rect[0] + 4, rect[1] + rect[3] - 4), (rect[0] + 4, rect[1] + 30))


def drawFilledRect(pos, size, colour = LIGHT_BLUE):
    pygame.draw.rect(screen, colour, pygame.Rect(pos, size))


def drawImage(image, pos, stick = 6):
    screen.blit(image, pos)

    drawRect(pos, image.get_size(), stick = stick, outside = 1)


def drawUpArrow(x1, y1, x2, y2, colour):
    pygame.draw.line(screen, colour, (x1, y2), (x1 + (x2 - x1) / 2, y1))
    pygame.draw.line(screen, colour, (x1 + (x2 - x1) / 2, y1), (x2, y2))
    pygame.draw.line(screen, colour, (x1, y2), (x2, y2))


def drawDownArrow(x1, y1, x2, y2, colour):
    pygame.draw.line(screen, colour, (x1, y1), (x1 + (x2 - x1) / 2, y2))
    pygame.draw.line(screen, colour, (x1 + (x2 - x1) / 2, y2), (x2, y1))
    pygame.draw.line(screen, colour, (x1, y1), (x2, y1))


def drawGraph(pos, size, data, minData, maxData, maxPoints, axisColour = LIGHT_BLUE, dataColour = GREEN, stick = 0):

    def calcPoint(d, mn, mx, x, y, h):
        r = mx - mn - 1
        if r < 5:
            r = 5

        d = d - mn
        if d > mx:
            d = mx
        if d < 0:
            d = 0
        d = r - d

        return x, y + int(d / r * h)

    outside = 0

    # pygame.draw.line(screen, axisColour, (pos[0] - stick, pos[1] - outside), (pos[0] + size[0] + stick, pos[1] - outside))
    pygame.draw.line(screen, axisColour, (pos[0] - stick, pos[1] + size[1] + outside), (pos[0] + size[0] + stick, pos[1] + size[1] + outside))

    pygame.draw.line(screen, axisColour, (pos[0] - outside, pos[1] - stick), (pos[0] - outside, pos[1] + size[1] + stick))
    # pygame.draw.line(screen, axisColour, (pos[0] + size[0] + outside, pos[1] - stick), (pos[0] + size[0] + outside, pos[1] + size[1] + stick))

    if len(data) > 1:
        to = len(data) - maxPoints
        if to < 0:
            to = 0

        stretch = size[0] / min([maxPoints, len(data) - 1])

        x = pos[0] + size[0] - 1

        ld = data[len(data) - 1]
        lp = calcPoint(ld, minData, maxData, x, pos[1], size[1])

        for i in range(len(data) - 2, to - 1, -1):
            x = x - int(stretch)
            d = data[i]
            p = calcPoint(d, minData, maxData, x, pos[1], size[1])

            pygame.draw.line(screen, dataColour, lp, p)
            ld = d
            lp = p
