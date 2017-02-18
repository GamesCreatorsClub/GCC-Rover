
import sys
import pygame

lastkeys = []
keys = []


def processKeys(onKeyDown, onKeyUp):
    global lastkeys, keys

    lastkeys = keys
    keys = pygame.key.get_pressed()
    if not len(keys) == 0 and not len(lastkeys) == 0:

        for i in range(0, len(keys) - 1):

            if keys[i] and not lastkeys[i]:
                onKeyDown(i)
            if not keys[i] and lastkeys[i]:
                onKeyUp(i)
