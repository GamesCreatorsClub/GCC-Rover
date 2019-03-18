
#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import gccui
import math
import pygame

from functools import partial
from pygame import Rect
from roverscreencomponents import WheelComponent, WheelStatusComponent


class MazeCorridorComponent(gccui.components.CardsCollection):
    def __init__(self, rect, uiFactory, rover):
        super(MazeCorridorComponent, self).__init__(rect)
        self.rover = rover

        self.rover_image = pygame.image.load("rover-top-no-cover-48.png")
        self.rover_image = pygame.transform.scale(self.rover_image, (32, 32))

        # self.front_distance = 4000
        # self.back_distance = 4000
        # self.left_angle = 0
        # self.right_angle = 0
        # self.left_front_distance = 0
        # self.right_front_distance = 0

        self.scale = self.rect.width / 2

        self.rover_image_component = uiFactory.image(self.rect.copy(), self.rover_image)
        self.rover_image_component.rect.width = self.rover_image.get_width()
        self.rover_image_component.rect.height = self.rover_image.get_height()
        self.rover_image_component.rect.center = self.rect.center
        self.addComponent(self.rover_image_component)

    def draw(self, surface):
        def drawRadar(state, deg):
            d = state.radar.radar[deg]

            if deg == 90 or deg == 180 or deg == 270 or deg == 0:
                if d > 1200:
                    d = 1200
            else:
                if d > 1700:
                    d = 1700

            d = int(d * self.scale / 1200)
            deg = deg * math.pi / 180 - math.pi / 2
            x = int(math.cos(deg) * d + self.rect.center[0])
            y = int(math.sin(deg) * d + self.rect.center[1])
            pygame.draw.line(surface, pygame.color.THECOLORS['gray48'], self.rect.center, (x, y))
            pygame.draw.circle(surface, pygame.color.THECOLORS['gray48'], (x, y), 3)

        def drawWall(side_distance, front_distance, angle, mod, corner):
            angle = angle / 2
            side_distance = int(side_distance * self.scale / 1200)
            front_distance = int(front_distance * self.scale / 1200)

            x0 = int(mod * side_distance)
            y0 = 0

            x2 = int(mod * math.sin(angle * math.pi / 180) * self.scale + x0)
            y2 = self.scale

            if corner:
                x1 = mod * side_distance
                y1 = 0
                if (x2 - x1) != 0.0:
                    k = (y2 - y1) / (x2 - x1)
                else:
                    k = 1000000000.0
                y = (y1 - k * x1) / (1 + mod * k)
                x = y
                x1 = int(- mod * x)
                y1 = int(y)
                x1 = x1 + self.rect.center[0]
                y1 = y1 + self.rect.center[1]

                x31 = mod * self.scale
                y31 = -mod * x2

                x31 = x31 + self.rect.center[0]
                y31 = y31 + self.rect.center[1]

                pygame.draw.line(surface, pygame.color.THECOLORS['green2'], (x1, y1), (x31, y31))

            else:
                x1 = int(-mod * math.sin(angle * math.pi / 180) * self.scale + x0)
                y1 = -self.scale

                x1 = x1 + self.rect.center[0]
                y1 = y1 + self.rect.center[1]
            x2 = x2 + self.rect.center[0]
            y2 = y2 + self.rect.center[1]

            pygame.draw.line(surface, pygame.color.THECOLORS['green2'], (x1, y1), (x2, y2))

        def drawFrontWall(front_distance, angle, left_corner, right_corner):
            if front_distance < 1200:
                front_distance = int(front_distance * self.scale / 1200)

                angle = - angle + math.pi / 2

                x0 = 0
                y0 = -front_distance

                x1 = -self.scale
                y1 = int(-math.sin(angle * math.pi / 180) * self.scale + y0)

                x2 = self.scale
                y2 = int(math.sin(angle * math.pi / 180) * self.scale + y0)

                x1 = x1 + self.rect.center[0]
                y1 = y1 + self.rect.center[1]
                x2 = x2 + self.rect.center[0]
                y2 = y2 + self.rect.center[1]

                pygame.draw.line(surface, pygame.color.THECOLORS['green2'], (x1, y1), (x2, y2))

        pygame.draw.rect(surface, pygame.color.THECOLORS['green'], self.rect, 1)

        state = self.rover.getRoverState()

        for d in [0, 45, 90, 135, 180, 225, 270, 315]:
            drawRadar(state, d)

        left_angle = int(state.left_wall_angle * 180 / math.pi)
        right_angle = int(state.right_wall_angle * 180 / math.pi)

        left_front_distance = state.left_front_distance_of_wall
        right_front_distance = state.right_front_distance_of_wall

        drawWall(state.radar.radar[90], state.radar.radar[45], right_angle, 1, right_front_distance > 50)
        drawWall(state.radar.radar[270], state.radar.radar[315], left_angle, -1, left_front_distance > 50)
        drawFrontWall(state.radar.radar[0], right_angle, left_front_distance > 0, right_front_distance > 0)

        rotated_rover_image = pygame.transform.rotate(self.rover_image, -state.heading.heading)
        rotated_rover_image.get_rect(center=self.rect.center)
        self.rover_image_component._surface = rotated_rover_image

        super(MazeCorridorComponent, self).draw(surface)


