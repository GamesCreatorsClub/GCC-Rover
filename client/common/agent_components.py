
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

        self.arrow_image = pygame.image.load("../common/arrow.png")
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
    def __init__(self, rect, label_text, format, colour=None, font=None, h_alignment=gccui.ALIGNMENT.LEFT, v_alignment=gccui.ALIGNMENT.TOP):
        super(ValueWithLabel, self).__init__(rect, label_text, colour, font, h_alignment=h_alignment, v_alignment=v_alignment)
        self.label_text = label_text
        self.format = format

    def setText(self, text):
        super(ValueWithLabel, self).setText(self.label_text + self.format.format(text))


class ReflectonValueWithLabel(ValueWithLabel):
    def __init__(self, rect, label_text, format, root, path, colour=None, font=None, h_alignment=gccui.ALIGNMENT.LEFT, v_alignment=gccui.ALIGNMENT.TOP):
        super(ReflectonValueWithLabel, self).__init__(rect, label_text, format, colour=colour, font=font, h_alignment=h_alignment, v_alignment=v_alignment)
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
    def __init__(self, rect, label_text, format, root, path, colour=None, font=None, h_alignment=gccui.ALIGNMENT.LEFT, v_alignment=gccui.ALIGNMENT.TOP):
        super(ReflectonAngleWithLabel, self).__init__(rect, label_text, format, root, path, colour=colour, font=font, h_alignment=h_alignment, v_alignment=v_alignment)

    def fetchValue(self):
        o = super(ReflectonAngleWithLabel, self).fetchValue()
        return int(o * 180 / math.pi)


class ReflectonLookupWithLabel(ReflectonValueWithLabel):
    def __init__(self, rect, label_text, format, root, path, lookup, colour=None, font=None, h_alignment=gccui.ALIGNMENT.LEFT, v_alignment=gccui.ALIGNMENT.TOP):
        super(ReflectonLookupWithLabel, self).__init__(rect, label_text, format, root, path, colour=colour, font=font, h_alignment=h_alignment, v_alignment=v_alignment)
        self.lookup = lookup

    def fetchValue(self):
        o = super(ReflectonLookupWithLabel, self).fetchValue()
        return self.lookup[o]


class WheelsStatus(gccui.Collection):
    def __init__(self, rect, uiFactory, wheel_odo_and_status_method, wheel_angle_and_status_method):
        super(WheelsStatus, self).__init__(rect)
        self.uiFactory = uiFactory

        wheelImage = pygame.image.load("../common/wheel.png")
        wheelOdoImage = pygame.image.load("../common/wheel-odo.png")

        self.addComponent(WheelStatusComponent(Rect(rect.x, rect.y, 150, 32), uiFactory, wheelOdoImage, partial(wheel_odo_and_status_method, 'fl')))
        self.addComponent(WheelStatusComponent(Rect(rect.x + 155, rect.y, 150, 32), uiFactory, wheelOdoImage, partial(wheel_odo_and_status_method, 'fr')))
        self.addComponent(WheelStatusComponent(Rect(rect.x, rect.y + 37, 150, 32), uiFactory, wheelOdoImage, partial(wheel_odo_and_status_method, 'bl')))
        self.addComponent(WheelStatusComponent(Rect(rect.x + 155, rect.y + 37, 150, 32), uiFactory, wheelOdoImage, partial(wheel_odo_and_status_method, 'br')))

        self.addComponent(WheelComponent(Rect(rect.x, rect.y + 74, 150, 150), uiFactory, wheelImage, partial(wheel_angle_and_status_method, 'fl'), True))
        self.addComponent(WheelComponent(Rect(rect.x + 155, rect.y + 74, 150, 150), uiFactory, wheelImage, partial(wheel_angle_and_status_method, 'fr'), True))
        self.addComponent(WheelComponent(Rect(rect.x, rect.y + 230, 150, 150), uiFactory, wheelImage, partial(wheel_angle_and_status_method, 'bl'), True))
        self.addComponent(WheelComponent(Rect(rect.x + 155, rect.y + 230, 150, 150), uiFactory, wheelImage, partial(wheel_angle_and_status_method, 'br'), True))


class Border(gccui.Component):
    def __init__(self, rect, colour=pygame.color.THECOLORS['cornflowerblue'], stick=6, outside=1):
        super(Border, self).__init__(rect)
        self.colour = colour
        self.stick = stick
        self.outside = outside

    def draw(self, surface):
        pygame.draw.line(surface, self.colour, (self.rect.left - self.stick, self.rect.top - self.outside), (self.rect.right + self.stick, self.rect.top - self.outside))
        pygame.draw.line(surface, self.colour, (self.rect.left - self.stick, self.rect.bottom + self.outside), (self.rect.right + self.stick, self.rect.bottom + self.outside))

        pygame.draw.line(surface, self.colour, (self.rect.left - self.outside, self.rect.top - self.stick), (self.rect.left - self.outside, self.rect.bottom + self.stick))
        pygame.draw.line(surface, self.colour, (self.rect.right + self.outside, self.rect.top - self.stick), (self.rect.right + self.outside, self.rect.bottom + self.stick))


class BorderImage(gccui.Image):
    def __init__(self, rect, surface, h_alignment=gccui.ALIGNMENT.LEFT, v_alignment=gccui.ALIGNMENT.TOP):
        super(BorderImage, self).__init__(rect, surface, h_alignment=h_alignment, v_alignment=v_alignment)
        self.border = Border(rect)

    def redefineRect(self, rect):
        super(BorderImage, self).redefineRect(rect)
        self.border.redefineRect(rect)

    def draw(self, surface):
        super(BorderImage, self).draw(surface)
        self.border.draw(surface)

