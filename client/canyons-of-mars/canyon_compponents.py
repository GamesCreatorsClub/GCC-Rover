
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


class RunButtons(gccui.components.CardsCollection):
    def __init__(self, rect, uiFactory, run_log, off_callback, runners):
        super(RunButtons, self).__init__(rect)
        self.playback = False
        self.run_log = run_log
        self.runners_count = len(runners)
        self.off_callback = off_callback

        self.label = uiFactory.label(rect, "Connecting...")
        self.addComponent(self.label)

        self.count_label = uiFactory.label(self.rect, "Log # -")
        self.addComponent(self.count_label)

        self.onComponent = gccui.Collection(rect)
        self.onComponent.addComponent(uiFactory.text_button(rect, "Stop", self.off_button_clicked, hint=gccui.UI_HINT.WARNING))

        self.offComponent = gccui.Collection(rect)

        self.runners = gccui.Collection(rect)

        self.offComponent.addComponent(uiFactory.text_button(rect, "Stop", self.off_button_clicked, hint=gccui.UI_HINT.ERROR))

        for runner in runners:
            self.runners.addComponent(uiFactory.text_button(rect, runner[0], partial(self.runners_button_clicked, runner[1])))

        self.runners.addComponent(uiFactory.text_button(rect, "Playback", self.playback_button_clicked))

        self.offComponent.addComponent(self.runners)

        self.ctrl = gccui.Collection(rect)
        self.ctrl.addComponent(uiFactory.text_button(rect, "Leave Playback", onClick=self.leave_playback_clicked))
        self.ctrl.addComponent(uiFactory.text_button(rect, "<<", onClick=partial(self.prev_clicked, 10)))
        self.ctrl.addComponent(uiFactory.text_button(rect, "<", onClick=partial(self.prev_clicked, 1)))
        self.ctrl.addComponent(uiFactory.text_button(rect, ">", onClick=partial(self.next_clicked, 1)))
        self.ctrl.addComponent(uiFactory.text_button(rect, ">>", onClick=partial(self.next_clicked, 10)))
        self.ctrl.addComponent(uiFactory.text_button(rect, "Load", onClick=self.load_clicked))
        self.ctrl.addComponent(uiFactory.text_button(rect, "Save", onClick=self.save_clicked))
        self.ctrl.setVisible(False)
        self.offComponent.addComponent(self.ctrl)

        self.addCard("on", self.onComponent)
        self.addCard("off", self.offComponent)

        self.selectCard("off")

        self.redefineRect(rect)

    def redefineRect(self, rect):
        margin = 5
        label_height = 20
        button_height = 30
        self.label.redefineRect(Rect(rect.x, rect.y, rect.width, label_height))
        self.count_label.redefineRect(Rect(rect.x, self.label.rect.bottom + margin, rect.width, label_height))

        self.onComponent.rect = Rect(rect.x, self.count_label.rect.bottom + margin, rect.width, rect.height - label_height * 2 - margin * 2)
        self.offComponent.rect = self.onComponent.rect

        self.ctrl.rect = Rect(rect.x, self.count_label.rect.bottom + margin, rect.width, rect.height - label_height * 2 - margin * 2 - button_height - margin)
        self.runners.rect = self.ctrl.rect

        self.onComponent.components[0].redefineRect(Rect(rect.x, rect.bottom - button_height, rect.width, button_height))

        self.offComponent.components[0].redefineRect(Rect(rect.x, rect.bottom - button_height, rect.width, button_height))

        for i in range(0, self.runners_count):
            self.runners.components[i].redefineRect(Rect(rect.x, self.count_label.rect.bottom + margin + i * (button_height + margin), rect.width, button_height))

        self.runners.components[self.runners_count].redefineRect(Rect(rect.x, self.runners.rect.bottom - button_height, rect.width, button_height))

        self.ctrl.components[0].redefineRect(Rect(self.ctrl.rect.x, self.ctrl.rect.bottom - button_height - margin, self.ctrl.rect.width, button_height))
        self.ctrl.components[1].redefineRect(Rect(self.ctrl.rect.x, self.ctrl.rect.y + label_height + margin, int(self.ctrl.rect.width * 0.23), button_height))
        self.ctrl.components[2].redefineRect(Rect(self.ctrl.rect.x + self.ctrl.rect.width // 4, self.ctrl.rect.y + label_height + margin, int(self.ctrl.rect.width * 0.23), button_height))
        self.ctrl.components[3].redefineRect(Rect(self.ctrl.rect.x + self.ctrl.rect.width * 2 // 4, self.ctrl.rect.y + label_height + margin, int(self.ctrl.rect.width * 0.23), button_height))
        self.ctrl.components[4].redefineRect(Rect(self.ctrl.rect.x + self.ctrl.rect.width * 3 // 4, self.ctrl.rect.y + label_height + margin, int(self.ctrl.rect.width * 0.23), button_height))
        self.ctrl.components[5].redefineRect(Rect(self.ctrl.rect.x, self.ctrl.components[2].rect.bottom + margin, int(self.ctrl.rect.width * 0.45), button_height))
        self.ctrl.components[6].redefineRect(Rect(self.ctrl.rect.x + self.ctrl.rect.width // 2, self.ctrl.components[2].rect.bottom + margin, int(self.ctrl.rect.width * 0.45), button_height))

    def draw(self, surface):
        self.count_label.setText("# {:> 3d}/{:> 3d} {:>7.2f}s".format(self.run_log.ptr, self.run_log.size(), self.run_log.currentRecordTimeOffset()))
        super(RunButtons, self).draw(surface)

    def prevClicked(self, button, pos):
        self.run_log.previousRecord()

    def nextClicked(self, button, pos):
        self.run_log.nextRecord()

    def on(self):
        self.selectCard("on")

    def off(self):
        self.selectCard("off")

    def runners_button_clicked(self, callback, button, pos):
        self.selectCard('on')
        callback()

    def off_button_clicked(self, button, pos):
        self.selectCard('off')
        self.off_callback()

    def playback_button_clicked(self, button, pos):
        self.ctrl.setVisible(True)
        self.runners.setVisible(False)
        self.run_log.setup()
        self.playback = True

    def leave_playback_clicked(self, button, pos):
        self.ctrl.setVisible(False)
        self.runners.setVisible(True)
        self.playback = False

    def prev_clicked(self, step, button, pos):
        self.run_log.previousRecord(step)

    def next_clicked(self, step, button, pos):
        self.run_log.nextRecord(step)

    def load_clicked(self, button, pos):
        self.run_log.load()

    def save_clicked(self, button, pos):
        self.run_log.save()


class HeadingComponent(gccui.components.CardsCollection):
    def __init__(self, rect, uiFactory, read_heading_method, on_callback, off_callback):
        super(HeadingComponent, self).__init__(rect)

        self.read_heading_method = read_heading_method
        self.current_heading = 0

        self.arrow_image = pygame.image.load("arrow.png")
        self.arrow_image = pygame.transform.scale(self.arrow_image, (24, 24))

        self.on_callback = on_callback
        self.off_callback = off_callback

        self.onComponent = gccui.Collection(rect)
        self.onComponent.addComponent(uiFactory.text_button(Rect(0, 0, 0, 30), "Sensors Off", self.off_button_clicked, hint=gccui.UI_HINT.WARNING))

        self.offComponent = gccui.Collection(rect)
        self.offComponent.addComponent(uiFactory.text_button(Rect(0, 0, 0, 30), "Sensors On", self.on_button_clicked))

        self.addCard("on", self.onComponent)
        self.addCard("off", self.offComponent)

        self.selectCard("off")

        self.heading_label = uiFactory.label(Rect(370, 0, 70, 20), "", h_alignment=gccui.ALIGNMENT.RIGHT)
        self.addComponent(self.heading_label)

        self.image = uiFactory.image(Rect(0, 0, self.arrow_image.get_width(), self.arrow_image.get_height()), self.arrow_image, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.addComponent(self.image)

        self.redefineRect(rect)

    def redefineRect(self, rect):
        self.rect = rect
        self.heading_label.redefineRect(Rect(rect.x, rect.y, rect.width, self.heading_label.rect.height))

        self.onComponent.redefineRect(Rect(rect.x, self.rect.bottom - 30, rect.width, 30))
        self.offComponent.redefineRect(Rect(rect.x, self.rect.bottom - 30, rect.width, 30))
        # self.onComponent.components[0].redefineRect(Rect(rect.x, self.rect.bottom - 30 - margin, rect.width, 30))
        # self.offComponent.components[0].redefineRect(Rect(rect.x, self.hearect.bottom - 30 - margin, rect.width, 30))

        self.image.redefineRect(Rect(rect.x, rect.y, rect.width, rect.height - self.heading_label.rect.height - 10))

    def draw(self, surface):
        self.setHeading(self.read_heading_method())
        super(HeadingComponent, self).draw(surface)

    def on(self):
        self.selectCard("on")

    def off(self):
        self.selectCard("off")

    def on_button_clicked(self, button, pos):
        self.selectCard('on')
        self.on_callback()

    def off_button_clicked(self, button, pos):
        self.selectCard('off')
        self.off_callback()

    def setHeading(self, heading):
        if self.current_heading != heading:
            self.heading_label.setText("{:7.2f}".format(heading))

            rotatedImage = pygame.transform.rotate(self.arrow_image, heading)
            rotatedImage.get_rect(center=self.rect.center)
            self.image._surface = rotatedImage
            self.current_heading = heading


class ValueWithLabel(gccui.Label):
    def __init__(self, rect, label_text, format, colour=None, font=None):
        super(ValueWithLabel, self).__init__(rect, label_text, colour, font)
        self.label_text = label_text
        self.format = format

    def setText(self, text):
        super(ValueWithLabel, self).setText(self.label_text + self.format.format(text))


class ReflectonValueWithLabel(ValueWithLabel):
    def __init__(self, rect, label_text, format, root, path, colour=None, font=None):
        super(ReflectonValueWithLabel, self).__init__(rect, label_text, format, colour=colour, font=font)
        self.label_text = label_text
        self.format = format
        self.root = root
        self.path = path.split(".")

    def fetchValue(self):
        o = self.root
        for p in self.path:
            o = getattr(o, p)

        return o

    def draw(self, surface):
        self.setText(self.fetchValue())

        super(ReflectonValueWithLabel, self).draw(surface)


class ReflectonAngleWithLabel(ReflectonValueWithLabel):
    def __init__(self, rect, label_text, format, root, path, colour=None, font=None):
        super(ReflectonAngleWithLabel, self).__init__(rect, label_text, format, root, path, colour=colour, font=font)

    def fetchValue(self):
        o = super(ReflectonAngleWithLabel, self).fetchValue()
        return int(o * 180 / math.pi)


class ReflectonLookupWithLabel(ReflectonValueWithLabel):
    def __init__(self, rect, label_text, format, root, path, lookup, colour=None, font=None):
        super(ReflectonLookupWithLabel, self).__init__(rect, label_text, format, root, path, colour=colour, font=font)
        self.lookup = lookup

    def fetchValue(self):
        o = super(ReflectonLookupWithLabel, self).fetchValue()
        return self.lookup[o]


class WheelsStatus(gccui.Collection):
    def __init__(self, rect, uiFactory, wheel_odo_and_status_method, wheel_angle_and_status_method):
        super(WheelsStatus, self).__init__(rect)
        self.uiFactory = uiFactory

        wheelImage = pygame.image.load("wheel.png")
        wheelOdoImage = pygame.image.load("wheel-odo.png")

        self.addComponent(WheelStatusComponent(Rect(rect.x, rect.y, 150, 32), uiFactory, wheelOdoImage, partial(wheel_odo_and_status_method, 'fl')))
        self.addComponent(WheelStatusComponent(Rect(rect.x + 155, rect.y, 150, 32), uiFactory, wheelOdoImage, partial(wheel_odo_and_status_method, 'fr')))
        self.addComponent(WheelStatusComponent(Rect(rect.x, rect.y + 37, 150, 32), uiFactory, wheelOdoImage, partial(wheel_odo_and_status_method, 'bl')))
        self.addComponent(WheelStatusComponent(Rect(rect.x + 155, rect.y + 37, 150, 32), uiFactory, wheelOdoImage, partial(wheel_odo_and_status_method, 'br')))

        self.addComponent(WheelComponent(Rect(rect.x, rect.y + 74, 150, 150), uiFactory, wheelImage, partial(wheel_angle_and_status_method, 'fl'), True))
        self.addComponent(WheelComponent(Rect(rect.x + 155, rect.y + 74, 150, 150), uiFactory, wheelImage, partial(wheel_angle_and_status_method, 'fr'), True))
        self.addComponent(WheelComponent(Rect(rect.x, rect.y + 230, 150, 150), uiFactory, wheelImage, partial(wheel_angle_and_status_method, 'bl'), True))
        self.addComponent(WheelComponent(Rect(rect.x + 155, rect.y + 230, 150, 150), uiFactory, wheelImage, partial(wheel_angle_and_status_method, 'br'), True))
