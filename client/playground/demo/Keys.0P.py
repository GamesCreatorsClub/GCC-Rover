
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import pygame

pygame.init()
screen = pygame.display.set_mode((300, 200))

while True:
    pygame.time.Clock().tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
    current_keys = pygame.key.get_pressed()
    last_keys = current_keys
    if current_keys[pygame.K_DOWN]:
        print("Hello")
    if current_keys[pygame.K_UP]:
        print("Hellow2")
    pygame.display.flip()
