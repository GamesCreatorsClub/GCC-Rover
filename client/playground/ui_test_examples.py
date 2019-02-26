
#
# Copyright 2019 Games Creators Club
#
# MIT License
#

import pygame, time, sys
from gccui import *

# All methods defined here are only for 'testing' and won't be seen if this file is imported as 'library'
selected_component = None
known_components = []
mousePos = (0, 0)
mouseDown = False


def main():
    global current_keys, running, mouseDown, mousePos, selected_component

    current_keys = pygame.key.get_pressed()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        uiAdapter.processEvent(event)

    running = True

    uiAdapter.draw(screen)


def button1Pressed(button, pos):
    print("Button1 pressed")


def button2Pressed(button, pos):
    print("Button2 pressed")


def someButtonPressed(button, pos):
    print("Button3 or button 4 is pressed")


pygame.init()

screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Pi Wars")

font = pygame.font.SysFont('Arial', 30)

# uiFactory = FlatTheme.FlatThemeFactory(font)
uiAdapter = UIAdapter(screen)
uiFactory = BoxBlueSFTheme.BoxBlueSFThemeFactory(uiAdapter, font)

running = True

wheelCal_label = uiFactory.label(None, 'Wheel Calibration')
pidCal_label = uiFactory.label(None, 'PID Calibration')
speedCal_label = uiFactory.label(None, 'Speed Calibration')
monitor_label = uiFactory.label(None, 'Shutdown Monitor', colour=(255, 0, 0))

myObject = uiFactory.button(pygame.Rect(320, 280, 150, 50), label=wheelCal_label)
myObject1 = uiFactory.button(pygame.Rect(myObject.rect.x + 300, myObject.rect.y, 150, 50), button1Pressed, label=pidCal_label, hint=UI_HINT.WARNING)  # making each button relative to the middle one.
myObject2 = uiFactory.button(pygame.Rect(myObject.rect.x, myObject.rect.y + 200, 150, 50), button2Pressed, label=speedCal_label, hint=UI_HINT.ERROR)  # This doesnt really work, Ill remove it later
myObject3 = uiFactory.button(pygame.Rect(myObject.rect.x, myObject.rect.y - 200, 150, 50), someButtonPressed, label=monitor_label)
myObject4 = uiFactory.button(pygame.Rect(myObject.rect.x - 300, myObject.rect.y, 150, 50), someButtonPressed)

screenComponent = Collection(screen.get_rect())
uiAdapter.setTopComponent(screenComponent)

screenComponent.addComponent(myObject)
screenComponent.addComponent(myObject1)
screenComponent.addComponent(myObject2)
screenComponent.addComponent(myObject3)
screenComponent.addComponent(myObject4)

clock = pygame.time.Clock()
while True:
    main()

    pygame.display.flip()
    clock.tick(60)



