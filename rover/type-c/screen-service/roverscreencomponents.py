#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import gccui
import math
import os
import pygame
import pyroslib
import subprocess
import time
from functools import partial
from pygame import Rect


OFF = 10
XOFF = 0
YOFF = 15

STATUS_ERROR_I2C_WRITE = 1
STATUS_ERROR_I2C_READ = 2
STATUS_ERROR_MOTOR_OVERHEAT = 4
STATUS_ERROR_MAGNET_HIGH = 8
STATUS_ERROR_MAGNET_LOW = 16
STATUS_ERROR_MAGNET_NOT_DETECTED = 32
STATUS_ERROR_RX_FAILED = 64
STATUS_ERROR_TX_FAILED = 128

_uiFactory = None
_uiAdapter = None
_font = None
_smallFont = None

_wheelsMap = None
_wheelImage = None
_wheelOdoImage = None
_wheelRects = {'fl': None, 'fr': None, 'bl': None, 'br': None}
_radar = None


def init(uiFactory, uiAdapter, font, smallFont, screen_rect, wheelsMap, wheelRects, radar):
    global _uiFactory, _uiAdapter, _wheelImage, _wheelOdoImage, _wheelsMap, _radar

    _uiFactory = uiFactory
    _uiAdapter = uiAdapter
    _font = font
    _smallFont = smallFont
    _wheelsMap = wheelsMap
    _wheelRects = wheelRects
    _radar = radar

    _wheelImage = pygame.image.load("graphics/wheel.png")
    _wheelOdoImage = pygame.image.load("graphics/wheel-odo.png")

    imageWidth = _wheelImage.get_width() // 2
    imageHeight = _wheelImage.get_height() // 2

    _wheelRects['fl'] = _wheelImage.get_rect(center=screen_rect.center).move(-imageWidth - OFF + XOFF, -imageHeight - OFF + YOFF)
    _wheelRects['fr'] = _wheelImage.get_rect(center=screen_rect.center).move(imageWidth + OFF + XOFF, -imageHeight - OFF + YOFF)
    _wheelRects['bl'] = _wheelImage.get_rect(center=screen_rect.center).move(-imageWidth - OFF + XOFF, imageHeight + OFF + YOFF)
    _wheelRects['br'] = _wheelImage.get_rect(center=screen_rect.center).move(imageWidth + OFF + XOFF, imageHeight + OFF + YOFF)
    _wheelRects['middle'] = _wheelImage.get_rect(center=screen_rect.center).move(XOFF, -YOFF)


class WheelStatus:
    NORM = 0
    WAS_WARN = 1
    WARN = 2
    WAR_ERR = 3
    ERR = 4

    def __init__(self, label=None):
        self.duration = 0
        self.old_text = ''
        self.overall_status = WheelStatus.NORM
        self.label = label
        self.colour = (255, 255, 255, 255)

    def _updateLabelColour(self):
        if self.label is not None:
            self.label.colour = self.colour
            self.label.invalidateSurface()

    def _updateLabelText(self, text):
        if self.label is not None:
            self.label.setText(text)

    def getKind(self):
        if self.overall_status == WheelStatus.NORM:
            pass

    def updateI2CStatus(self, _status):
        self._update(("2W", WheelStatus.ERR) if _status & STATUS_ERROR_I2C_WRITE else (("2R", WheelStatus.ERR) if _status & STATUS_ERROR_I2C_READ else ("", WheelStatus.NORM)))

    def updateRadioStatus(self, _status):
        self._update(("RX", WheelStatus.WARN) if _status & STATUS_ERROR_RX_FAILED else (("TX", WheelStatus.ERR) if _status & STATUS_ERROR_TX_FAILED else ("", WheelStatus.NORM)))

    def updateMagnetStatus(self, _status):
        self._update(("MH", WheelStatus.WARN) if _status & STATUS_ERROR_MAGNET_HIGH else (("ML", WheelStatus.WARN) if _status & STATUS_ERROR_MAGNET_LOW else (("ND", WheelStatus.ERR) if _status & STATUS_ERROR_MAGNET_NOT_DETECTED == 0 else ("", WheelStatus.NORM))))

    def updateControlStatus(self, _status):
        self._update(("O", WheelStatus.ERR) if _status & STATUS_ERROR_MOTOR_OVERHEAT else ("", WheelStatus.NORM))

    def _update(self, status):
        old_text = self.old_text
        text = status[0]
        kind = status[1]
        duration = self.duration
        if old_text == text:
            if kind == self.NORM:
                if duration > -1000:
                    duration -= 1
                    self.duration = duration
            else:
                duration += 1
                self.duration = duration

            if duration > 10:
                self.colour = pygame.color.THECOLORS['red']
                self._updateLabelColour()
                self.overall_status = WheelStatus.ERR
            if duration < -15:
                self._updateLabelText('')
                self.overall_status = WheelStatus.NORM
            elif duration < -12:
                self.colour = pygame.color.THECOLORS['orange4']
                self._updateLabelColour()
                self.overall_status = WheelStatus.WAS_WARN
            elif duration < -9:
                self.colour = pygame.color.THECOLORS['orange3']
                self._updateLabelColour()
                self.overall_status = WheelStatus.WAS_WARN
            elif duration < -6:
                self.colour = pygame.color.THECOLORS['orange2']
                self._updateLabelColour()
                self.overall_status = WheelStatus.WAS_WARN
            elif duration < -3:
                self.colour = pygame.color.THECOLORS['orange1']
                self._updateLabelColour()
                self.overall_status = WheelStatus.WAS_WARN
            elif duration < 0:
                self.colour = pygame.color.THECOLORS['orange']
                self._updateLabelColour()
                self.overall_status = WheelStatus.WAS_WARN

        else:
            self.old_text = text
            if kind == self.NORM:
                self.colour = pygame.color.THECOLORS['orange']
                self._updateLabelColour()
                self.overall_status = WheelStatus.NORM
            elif kind == self.WARN:
                self.colour = pygame.color.THECOLORS['orange']
                self._updateLabelColour()
                self._updateLabelText(text)
                self.overall_status = WheelStatus.WARN
            else:
                self.colour = pygame.color.THECOLORS['red']
                self._updateLabelText(text)
                self.overall_status = WheelStatus.ERR
            self.duration = 0

    def combineOverallStatus(self, overall_status):
        return max(self.overall_status, overall_status)


class WheelComponent(gccui.Collection):
    def __init__(self, rect, wheel_name, draw_angle):
        super(WheelComponent, self).__init__(rect)
        self.i2c_status = WheelStatus()
        self.radio_status = WheelStatus()
        self.magnet_status = WheelStatus()
        self.control_status = WheelStatus()
        self.wheel_name = wheel_name
        self.draw_angle = draw_angle
        self.image = _uiFactory.image(rect, None, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.addComponent(self.image)
        self.angle_text = _uiFactory.label(self.rect,
                                          "",
                                          h_alignment=gccui.ALIGNMENT.CENTER,
                                          v_alignment=gccui.ALIGNMENT.MIDDLE,
                                          colour=pygame.color.THECOLORS['black'])

        self.addComponent(self.angle_text)

        if not self.draw_angle:
            self.angle_text.setVisible(False)

        self.redefineRect(self.rect)

        self.wheelImageAlpha = _wheelImage.copy()
        self.wheelImageAlpha.fill((0, 0, 0, 255), None, pygame.BLEND_RGBA_MULT)

        def makeColourImage(colour):
            image = self.wheelImageAlpha.copy()
            image.fill(colour, None, pygame.BLEND_RGBA_ADD)
            return image

        self.wheelGreenImage = makeColourImage((0, 255, 0, 0))
        self.wheelYellowImage = makeColourImage((200, 255, 0, 0))
        self.wheelOrangeImage = makeColourImage((255, 220, 0, 0))
        self.wheelRedImage = makeColourImage((255, 0, 0, 0))

    def redefineRect(self, rect):
        self.rect = rect
        self.image.redefineRect(rect)
        self.angle_text.redefineRect(Rect(rect.x, rect.centery - self.angle_text.font.get_height() // 2, rect.width, self.angle_text.font.get_height()))

    def draw(self, surface):
        wheel = _wheelsMap[self.wheel_name]

        selectedWheelImage = _wheelImage
        status = wheel['deg_status'] | wheel['speed_status']

        self.i2c_status.updateI2CStatus(status)
        self.radio_status.updateRadioStatus(status)
        self.magnet_status.updateMagnetStatus(status)
        self.control_status.updateControlStatus(status)

        overall_status = self.i2c_status.overall_status
        overall_status = self.radio_status.combineOverallStatus(overall_status)
        overall_status = self.magnet_status.combineOverallStatus(overall_status)
        overall_status = self.control_status.combineOverallStatus(overall_status)

        if overall_status == WheelStatus.NORM:
            selectedWheelImage = self.wheelGreenImage
        elif overall_status == WheelStatus.WAS_WARN:
            selectedWheelImage = self.wheelYellowImage
        elif overall_status == WheelStatus.WARN or overall_status == WheelStatus.WAR_ERR:
            selectedWheelImage = self.wheelOrangeImage
        else:
            selectedWheelImage = self.wheelRedImage

        _angle = float(wheel['angle'])

        rotatedWheelImage = pygame.transform.rotate(selectedWheelImage, -_angle)
        rotatedWheelImage.get_rect(center=self.rect.center)
        self.image._surface = rotatedWheelImage

        if self.draw_angle:
            self.angle_text.setText(str(wheel['angle']))

        super(WheelComponent, self).draw(surface)


class WheelStatusComponent(gccui.Collection):
    def __init__(self, rect, wheel_name):
        super(WheelStatusComponent, self).__init__(rect)
        self.wheel_name = wheel_name
        self.odo_image = _uiFactory.image(rect, _wheelOdoImage, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.margin = (rect.width - _wheelOdoImage.get_rect().width) // 2

        self.odo_text = _uiFactory.label(self.rect,
                                        "",
                                        font=_smallFont,
                                        h_alignment=gccui.ALIGNMENT.RIGHT,
                                        v_alignment=gccui.ALIGNMENT.MIDDLE,
                                        colour=pygame.color.THECOLORS['white'])

        self.i2c_text = _uiFactory.label(self.rect,
                                        "",
                                        font=_smallFont,
                                        h_alignment=gccui.ALIGNMENT.LEFT,
                                        v_alignment=gccui.ALIGNMENT.MIDDLE,
                                        colour=pygame.color.THECOLORS['orange'])

        self.radio_text = _uiFactory.label(self.rect,
                                        "",
                                        font=_smallFont,
                                        h_alignment=gccui.ALIGNMENT.RIGHT,
                                        v_alignment=gccui.ALIGNMENT.MIDDLE,
                                        colour=pygame.color.THECOLORS['orange'])

        self.control_text = _uiFactory.label(self.rect,
                                        "",
                                        font=_smallFont,
                                        h_alignment=gccui.ALIGNMENT.LEFT,
                                        v_alignment=gccui.ALIGNMENT.MIDDLE,
                                        colour=pygame.color.THECOLORS['orange'])

        self.magnet_text = _uiFactory.label(self.rect,
                                        "",
                                        font=_smallFont,
                                        h_alignment=gccui.ALIGNMENT.RIGHT,
                                        v_alignment=gccui.ALIGNMENT.MIDDLE,
                                        colour=pygame.color.THECOLORS['orange'])

        self.i2c_status = WheelStatus(self.i2c_text)
        self.radio_status = WheelStatus(self.radio_text)
        self.control_status = WheelStatus(self.control_text)
        self.magnet_status = WheelStatus(self.magnet_text)

        self.addComponent(self.odo_image)
        self.addComponent(self.odo_text)

        self.addComponent(self.i2c_text)
        self.addComponent(self.magnet_text)
        self.addComponent(self.radio_text)
        self.addComponent(self.control_text)

        self.redefineRect(self.rect)

    def redefineRect(self, rect):
        self.rect = rect
        self.odo_image.redefineRect(rect)
        self.odo_text.redefineRect(rect.move(-self.margin - 5, 0))

        self.i2c_text.redefineRect(Rect(rect.x, rect.y, self.margin // 2, rect.height))
        self.radio_text.redefineRect(Rect(rect.x + self.margin // 2, rect.y, self.margin // 2, rect.height))

        self.control_text.redefineRect(Rect(rect.right - self.margin, rect.y, self.margin // 2, rect.height))
        self.magnet_text.redefineRect(Rect(rect.right - self.margin + self.margin // 2, rect.y, self.margin // 2, rect.height))

    def draw(self, surface):
        wheel = _wheelsMap[self.wheel_name]

        status = wheel['deg_status'] | wheel['speed_status']
        self.i2c_status.updateI2CStatus(status)
        self.radio_status.updateRadioStatus(status)
        self.control_status.updateControlStatus(status)
        self.magnet_status.updateMagnetStatus(status)

        self.odo_text.setText(str(wheel['odo']))

        super(WheelStatusComponent, self).draw(surface)


class Radar(gccui.Component):
    def __init__(self, rect, limit_distance):
        super(Radar, self).__init__(rect)
        self.limit_distance = limit_distance
        self.grey = pygame.color.THECOLORS['grey48']

    def draw(self, surface):
        def limit(d):
            if d < 0:
                d = 0
            if d > self.limit_distance:
                d = self.limit_distance

            size = min(self.rect.width, self.rect.height)
            return - (int(size * 0.8) - d / 20.0)

        pi8 = math.pi / 8

        WHITE = pygame.color.THECOLORS['white']

        pygame.draw.circle(surface, self.grey, self.rect.center, int(self.rect.width / 2.3), 1)
        pygame.draw.circle(surface, self.grey, self.rect.center, int(self.rect.width / 2.9), 1)
        pygame.draw.circle(surface, self.grey, self.rect.center, int(self.rect.width / 3.9), 1)
        pygame.draw.circle(surface, self.grey, self.rect.center, int(self.rect.width / 6), 1)
        pygame.draw.circle(surface, self.grey, self.rect.center, int(self.rect.width / 12), 1)
        for d in [pi8, pi8 * 3, pi8 * 5, pi8 * 7, pi8 * 9, pi8 * 11, pi8 * 13, pi8 * 15]:
            x1 = math.cos(d) * int(self.rect.width / 2.3) + self.rect.centerx
            y1 = math.sin(d) * int(self.rect.width / 2.3) + self.rect.centery
            x2 = math.cos(d) * int(self.rect.width / 12) + self.rect.centerx
            y2 = math.sin(d) * int(self.rect.width / 12) + self.rect.centery
            pygame.draw.line(surface, self.grey, (x1, y1), (x2, y2))

        pygame.draw.arc(_uiAdapter.getScreen(), (255, 0, 255), self.rect.inflate(limit(_radar[0]), limit(_radar[0])), pi8 * 3, pi8 * 5)  # 0º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(_radar[45]), limit(_radar[45])), pi8 * 1, pi8 * 3)  # 45º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(_radar[90]), limit(_radar[90])), pi8 * 15, pi8 * 1)  # 90º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(_radar[135]), limit(_radar[135])), pi8 * 13, pi8 * 15)  # 135º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(_radar[180]), limit(_radar[180])), pi8 * 11, pi8 * 13)  # 180º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(_radar[225]), limit(_radar[225])), pi8 * 9, pi8 * 11)  # 225º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(_radar[270]), limit(_radar[270])), pi8 * 7, pi8 * 9)  # 270º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(_radar[315]), limit(_radar[315])), pi8 * 5, pi8 * 7)  # 315º


class FlashingImage(gccui.Image):
    def __init__(self, rect, surface, h_alignment=gccui.ALIGNMENT.LEFT, v_alignment=gccui.ALIGNMENT.TOP):
        super(FlashingImage, self).__init__(rect, surface, h_alignment=h_alignment, v_alignment=v_alignment)
        self.last_flash = 0
        self.flash_len = 1
        self.do_show = True
        self.flashing_is_on = False

    def setFlashing(self, flashing):
        self.flashing_is_on = flashing
        if not flashing:
            self.do_show = True

    def getFlashing(self):
        return self.flashing_is_on

    def getFlashState(self):
        return self.do_show

    def draw(self, surface):
        if self.flashing_is_on:
            if self.do_show:
                super(FlashingImage, self).draw(surface)

            now = time.time()
            if self.last_flash + self.flash_len < now:
                self.last_flash = now
                self.do_show = not self.do_show

        else:
            super(FlashingImage, self).draw(surface)


class BatteryComponent(FlashingImage):
    def __init__(self, rect, grey_image, white_image, red_image):
        super(BatteryComponent, self).__init__(rect, grey_image)
        self.grey_image = grey_image
        self.white_image = white_image
        self.red_image = red_image
        self.bp = -1
        self.battery_warning = False
        self.battery_critical = False
        self.colour = pygame.color.THECOLORS['gray']

    def setBatteryPercentage(self, bp):
        if self.bp < 0 and bp >= 0:
            self.setImage(self.white_image)
            self.colour = pygame.color.THECOLORS['white']
        elif self.bp >= 0 and bp < 0:
            self.setImage(self.grey_image)
            self.colour = pygame.color.THECOLORS['gray']

        self.bp = bp

    def setBatteryStatus(self, status):
        if status == 'warning':
            if not self.battery_warning:
                self.battery_warning = True
                self.battery_critical = False
                self.colour = pygame.color.THECOLORS['orange']
                self.setImage(self.white_image)
                super(BatteryComponent, self).setFlashing(False)
        elif status == 'critical':
            if not self.battery_critical:
                self.battery_warning = False
                self.battery_critical = True
                self.colour = pygame.color.THECOLORS['red']
                super(BatteryComponent, self).setFlashing(True)
                self.setImage(self.red_image)
        else:
            if self.battery_warning or self.battery_critical:
                self.battery_warning = False
                self.battery_critical = False
                self.colour = pygame.color.THECOLORS['white']
                self.setImage(self.white_image)
                super(BatteryComponent, self).setFlashing(False)

    def draw(self, surface):
        if self.bp >= 0 and self.getFlashState():
            bp = self.bp
            rect = self.rect.inflate(-8, -8)
            rect.move_ip(4, -1)

            width = rect.width
            right = rect.right
            rect.width = int(width * bp / 100)
            rect.right = right
            pygame.draw.rect(surface, self.colour, rect)

        super(BatteryComponent, self).draw(surface)


class TemperatureStatusComponent(FlashingImage):
    def __init__(self, rect, temp_warning_image, temp_critical_image):
        super(TemperatureStatusComponent, self).__init__(rect, None)
        self.temp_warning_image = temp_warning_image
        self.temp_critical_image = temp_critical_image
        self.temperature = -1
        self.temperature_warning = False
        self.temperature_critical = False
        self.colour = pygame.color.THECOLORS['gray']

    def setTemperature(self, temperature):
        self.temperature = temperature

    def setTemperatureStatus(self, status):
        if status == 'warning':
            if not self.temperature_warning:
                self.temperature_warning = True
                self.temperature_critical = False
                self.colour = pygame.color.THECOLORS['orange']
                self.setImage(self.temp_warning_image)
        elif status == 'critical':
            if not self.temperature_critical:
                self.temperature_warning = False
                self.temperature_critical = True
                self.colour = pygame.color.THECOLORS['red']
                super(TemperatureStatusComponent, self).setFlashing(True)
                self.setImage(self.temp_critical_image)
        else:
            if self.temperature_warning or self.temperature_critical:
                self.temperature_warning = False
                self.temperature_critical = False
                self.colour = pygame.color.THECOLORS['white']
                self.setImage(None)

    def draw(self, surface):
        super(TemperatureStatusComponent, self).draw(surface)


class TemperatureComponent(gccui.Image):
    def __init__(self, rect):
        super(TemperatureComponent, self).__init__(rect, None)
        self.temp_full_critical_image = pygame.image.load("graphics/temp-full-critical.png")
        self.temp_full_warning_image = pygame.image.load("graphics/temp-full-warning.png")
        self.temp_full_nominal_image = pygame.image.load("graphics/temp-full-nominal.png")
        self.label = _uiFactory.label(rect, "", colour=pygame.color.THECOLORS['black'], font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.setImage(self.temp_full_nominal_image)
        self.temperature = -1
        self.temperature_warning = False
        self.temperature_critical = False
        self.colour_critical = pygame.color.Color(235, 78, 78)
        self.colour_warning = pygame.color.Color(255, 200, 0)
        self.colour_nominal = pygame.color.Color(235, 235, 78)
        self.colour = self.colour_nominal

    def redefineRect(self, rect):
        super(TemperatureComponent, self).redefineRect(rect)
        label_rect = rect.inflate(0, -148)
        label_rect.bottom = rect.bottom
        self.label.redefineRect(label_rect)

    def setTemperature(self, temperature):
        self.temperature = temperature
        self.label.setText(str(int(temperature)))

    def setTemperatureStatus(self, status):
        if status == 'warning':
            if not self.temperature_warning:
                self.temperature_warning = True
                self.temperature_critical = False
                self.setImage(self.temp_full_warning_image)
                self.colour = self.colour_warning
                self.label.setColour(pygame.color.THECOLORS['white'])
        elif status == 'critical':
            if not self.temperature_critical:
                self.temperature_warning = False
                self.temperature_critical = True
                self.setImage(self.temp_full_critical_image)
                self.colour = self.colour_critical
                self.label.setColour(pygame.color.THECOLORS['white'])
        else:
            if self.temperature_warning or self.temperature_critical:
                self.temperature_warning = False
                self.temperature_critical = False
                self.setImage(self.temp_full_nominal_image)
                self.colour = self.colour_nominal
                self.label.setColour(pygame.color.THECOLORS['black'])

    def draw(self, surface):
        if self.temperature >= 0:
            rect = self.rect.inflate(-40, -80)
            rect.move_ip(0, -13)

            height = rect.height
            bottom = rect.bottom
            rect.height = int(height * self.temperature / 90)
            rect.bottom = bottom
            pygame.draw.rect(surface, self.colour, rect)
        super(TemperatureComponent, self).draw(surface)
        self.label.draw(surface)


class CPUComponent(gccui.Component):
    def __init__(self, rect):
        super(CPUComponent, self).__init__(rect)
        self.percentage_label = _uiFactory.label(rect, "", colour=pygame.color.THECOLORS['black'], font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.cpu_label = _uiFactory.label(rect, "CPU", colour=pygame.color.THECOLORS['white'], font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.load = -1
        self.colour = pygame.color.THECOLORS['green']
        self.border_rect = None
        self.inner_rect = None
        self.bar_margin = 2
        self.border = _uiFactory.border(rect, _uiFactory.colour)
        self.redefineRect(rect)

    def redefineRect(self, rect):
        super(CPUComponent, self).redefineRect(rect)
        label_rect = rect.copy()
        label_rect.height = 35
        self.cpu_label.redefineRect(label_rect)

        label_rect = rect.copy()
        label_rect.width = label_rect.width - 4
        label_rect.x = label_rect.x + 4
        label_rect.height = 40
        label_rect.bottom = rect.bottom
        self.percentage_label.redefineRect(label_rect)

        self.border_rect = rect.inflate(-20, -0)
        self.border.redefineRect(self.border_rect)
        self.inner_rect = rect.inflate(-28, -8)

    def setCPULoad(self, load):
        last_load = self.load
        self.load = load
        self.percentage_label.setText(str(int(load)) + "%")
        if load < 40 and last_load >= 40:
            self.colour = pygame.color.THECOLORS['green']
            self.percentage_label.setColour(pygame.color.THECOLORS['black'])
        elif load >= 40 and load < 60 and (last_load < 40 or last_load >= 60):
            self.colour = pygame.color.THECOLORS['yellow']
            self.percentage_label.setColour(pygame.color.THECOLORS['black'])
        elif load >= 60 and load < 80 and (last_load < 60 or last_load >= 80):
            self.colour = pygame.color.THECOLORS['orange']
            self.percentage_label.setColour(pygame.color.THECOLORS['white'])
        elif load >= 80 and last_load < 80:
            self.colour = pygame.color.THECOLORS['red']
            self.percentage_label.setColour(pygame.color.THECOLORS['white'])

    def draw(self, surface):
        # pygame.draw.rect(surface, _uiFactory.colour, self.border_rect, 1)
        self.border.draw(surface)
        if self.load >= 0:
            total_y = self.inner_rect.height
            total_for_bars = total_y - self.bar_margin * 9
            bar_height = int(total_for_bars / 10)

            bars = int(self.load / 10)
            if bars > 0:
                for bar in range(1, bars + 1):
                    pygame.draw.rect(surface, self.colour, (self.inner_rect.x, self.inner_rect.bottom - bar_height * bar - self.bar_margin * (bar - 1), self.inner_rect.width, bar_height))

        self.percentage_label.draw(surface)
        self.cpu_label.draw(surface)


class StatusBarComponent(gccui.Collection):
    def __init__(self, rect):
        super(StatusBarComponent, self).__init__(rect)

        self.battery_grey_image = pygame.image.load("graphics/battery-grey.png")
        self.battery_red_image = pygame.image.load("graphics/battery-red.png")
        self.battery_white_image = pygame.image.load("graphics/battery-white.png")
        self.temp_warning_image = pygame.image.load("graphics/temp-warning.png")
        self.temp_critical_image = pygame.image.load("graphics/temp-critical.png")
        self.stop_image = pygame.image.load("graphics/pause.png")
        self.stop_black_image = pygame.image.load("graphics/play.png")
        self.joystick_white_image = pygame.image.load("graphics/joystick-white.png")
        self.joystick_black_image = pygame.image.load("graphics/joystick-black.png")
        self.battery_component = BatteryComponent(rect, self.battery_grey_image, self.battery_white_image, self.battery_red_image)
        self.temp_component = TemperatureStatusComponent(rect, self.temp_warning_image, self.temp_critical_image)
        self.stop_component = _uiFactory.image(rect, self.stop_image)
        self.joystick_component = _uiFactory.image(rect, self.joystick_black_image)
        self.uptime_component = _uiFactory.label(rect, "--:--", colour=pygame.color.THECOLORS['lightgrey'], h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.addComponent(self.stop_component)
        self.addComponent(self.battery_component)
        self.addComponent(self.temp_component)
        self.addComponent(self.joystick_component)
        self.addComponent(self.uptime_component)
        self.redefineRect(rect)

    def redefineRect(self, rect):
        self.rect = rect
        self.battery_component.redefineRect(Rect(rect.right - self.battery_grey_image.get_width() - 8, rect.y, self.battery_grey_image.get_width(), self.battery_grey_image.get_height()))
        self.uptime_component.redefineRect(Rect(self.battery_component.rect.x - 60, rect.y, 50, 24))  # font size is bodge to make it render to right place
        self.temp_component.redefineRect(Rect(self.uptime_component.rect.x - self.temp_warning_image.get_width() - 10, rect.y, self.temp_warning_image.get_width(), self.temp_warning_image.get_height()))
        self.joystick_component.redefineRect(Rect(self.temp_component.rect.x - self.joystick_white_image.get_width() - 10, rect.y, self.joystick_white_image.get_width(), self.joystick_white_image.get_height()))
        self.stop_component.redefineRect(Rect(rect.x + 20, rect.y, self.stop_image.get_width(), self.stop_image.get_height()))

    # def draw(self, surface):
    #     super(StatusBarComponent, self).draw(surface)

    def setWheelsStatus(self, status):
        if status == 'stopped':
            self.stop_component.setImage(self.stop_image)
            self.stop_component.setVisible(True)
        elif status == 'running':
            self.stop_component.setImage(self.stop_black_image)
            self.stop_component.setVisible(True)
        else:
            self.stop_component.setVisible(False)

    def setJoystickStatus(self, status):
        if status == 'connected':
            self.joystick_component.setImage(self.joystick_white_image)
            self.joystick_component.setVisible(True)
        elif status == 'none':
            self.joystick_component.setImage(self.joystick_black_image)
            self.joystick_component.setVisible(True)
        else:
            self.joystick_component.setVisible(False)

    def setUptime(self, uptime):
        if len(uptime) > 5:
            uptime = uptime[0:5]
        self.uptime_component.setText(uptime)

    def setBatteryStatus(self, status):
        self.battery_component.setBatteryStatus(status)

    def setBatteryPercentage(self, battery_percentage):
        self.battery_component.setBatteryPercentage(battery_percentage)

    def setTemperature(self, status):
        self.temp_component.setTemperature(status)

    def setTemperatureStatus(self, status):
        self.temp_component.setTemperatureStatus(status)


class Stats:
    def __init__(self):
        self.stats = []

    def add(self, value):
        self.stats.append((time.time(), value))

    def lastValue(self):
        if len(self.stats) == 0:
            return None
        else:
            return self.stats[len(self.stats) - 1][1]

    def last(self, seconds):
        if len(self.stats) == 0:
            return []

        l = len(self.stats)
        now = time.time()
        then = now - seconds
        index = 0
        while self.stats[index][0] < then and index < l:
            index += 1

        if index >= l:
            return []

        return self.stats[index:]


class StatsGraph(gccui.Component):
    def __init__(self, rect):
        super(StatsGraph, self).__init__(rect)
        self.stats = None
        self.border_colour = _uiFactory.colour
        self.inner_colour = pygame.Color(0, 0, 255, 128)
        self.background_colour = pygame.color.THECOLORS['black']
        self.line_colour = pygame.color.THECOLORS['gray']
        self.inner_rect = rect.inflate(10, 10)
        self.units = ''
        self.min_width_time = 60
        self.max_value = 3000
        self.max_label = _uiFactory.label(None, "", h_alignment=gccui.ALIGNMENT.RIGHT, v_alignment=gccui.ALIGNMENT.TOP)
        self.units_label = _uiFactory.label(None, "", h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.TOP)
        self.now_label = _uiFactory.label(None, "now", h_alignment=gccui.ALIGNMENT.RIGHT, v_alignment=gccui.ALIGNMENT.BOTTOM)
        self.time_label = _uiFactory.label(None, "", h_alignment=gccui.ALIGNMENT.LEFT, v_alignment=gccui.ALIGNMENT.BOTTOM)
        self.warning_value = -1
        self.critical_value = -1
        self.warning_colour = pygame.color.THECOLORS['orange']
        self.critical_colour = pygame.color.THECOLORS['red']

        self.redefineRect(rect)

    def redefineRect(self, rect):
        super(StatsGraph, self).redefineRect(rect)
        self.inner_rect = rect.inflate(-8, -8)
        self.units_label.redefineRect(self.inner_rect)
        self.max_label.redefineRect(self.inner_rect)
        self.now_label.redefineRect(self.inner_rect)
        self.time_label.redefineRect(self.inner_rect)

    def setStats(self, stats):
        self.stats = stats

    def setUnits(self, units):
        self.units = units
        self.units_label.setText("(" + units + ")")

    def setMaxValue(self, max_value):
        if len(self.units) > 0:
            self.max_label.setText(str(max_value) + " " + self.units)
        else:
            self.max_label.setText(str(max_value))
        self.max_value = max_value

    def setWarningValue(self, warning_value):
        self.warning_value = warning_value

    def setCriticalValue(self, critical_value):
        self.critical_value = critical_value

    def draw(self, surface):
        pygame.draw.rect(surface, self.border_colour, self.rect, 1)
        pygame.draw.rect(surface, self.background_colour, self.inner_rect)
        if self.stats is not None:
            data = self.stats.last(3600)
            if len(data) > 0:
                t0 = data[0][0]
                now = time.time()

                t_minutes = int((now - t0) / 60)
                if t_minutes == 0:
                    self.time_label.setText("")
                elif t_minutes == 1:
                    self.time_label.setText("1 min")
                else:
                    self.time_label.setText(str(t_minutes) + " mins")

                data_width = now - t0
                if data_width < self.min_width_time:
                    data_width = self.min_width_time
                t_max = t0 + data_width
                d_max = self.max_value

                if data_width <= 60:
                    minute_line_time = 5
                elif data_width <= 300:
                    minute_line_time = 25
                else:
                    minute_line_time = 300

                t = t0 + minute_line_time
                tl = data[len(data) - 1][0]
                while t < tl:
                    x = self.inner_rect.x + (t - t0) * self.inner_rect.width / data_width
                    pygame.draw.line(surface, self.line_colour, (x, self.inner_rect.y + 1), (x, self.inner_rect.bottom - 2), 1)
                    t += minute_line_time

                x = self.inner_rect.x
                points = []
                for d in data:
                    t = d[0]
                    p = d[1]
                    if p > self.max_value:
                        p = self.max_value
                    x = self.inner_rect.x + (t - t0) * self.inner_rect.width / data_width
                    y = self.inner_rect.bottom - p * self.inner_rect.height / self.max_value
                    points.append((x, y))

                points.append((x, self.inner_rect.bottom))
                points.append((self.inner_rect.x, self.inner_rect.bottom))

                pygame.draw.polygon(surface, self.inner_colour, points)
                pygame.draw.polygon(surface, self.border_colour, points, 1)

                if self.warning_value >= 0:
                    y = self.inner_rect.bottom - self.warning_value * self.inner_rect.height / self.max_value
                    pygame.draw.line(surface, self.warning_colour, (self.inner_rect.x + 1, y), (self.inner_rect.right - 2, y))

                if self.critical_value >= 0:
                    y = self.inner_rect.bottom - self.critical_value * self.inner_rect.height / self.max_value
                    pygame.draw.line(surface, self.critical_colour, (self.inner_rect.x + 1, y), (self.inner_rect.right - 2, y))

            self.units_label.draw(surface)
            self.max_label.draw(surface)
            self.now_label.draw(surface)
            self.time_label.draw(surface)
