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

wheelImage = None
wheelOdoImage = None
wheelRects = {'fl': None, 'fr': None, 'bl': None, 'br': None}

received = False

radar = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0}

angle = 0.0

_uiFactory = None
_uiAdapter = None
_font = None
_smallFont = None
screensComponent = None
topComponent = None
statusBarComponent = None
_slaves_shutdown = False
_main_screen_image = None
_backgrounds = {}
_sounds = {}


def _createTemplateWheel(distance_index):
    return {
        'angle': 0,
        'deg_status': 0,
        'speed_status': 0,
        'odo': 0,
        'cal': {},
        'dindex': distance_index
    }


wheelsMap = {'fl': _createTemplateWheel(0), 'fr': _createTemplateWheel(2), 'bl': _createTemplateWheel(4), 'br': _createTemplateWheel(6), 'pid': {}}


def stopAllButtonClick(button, pos):
    # pyroslib.publish("wheel/fr/deg", "-")
    # pyroslib.publish("wheel/fl/deg", "-")
    # pyroslib.publish("wheel/br/deg", "-")
    # pyroslib.publish("wheel/bl/deg", "-")
    pyroslib.publish("wheel/stop", "toggle")


def initGui():
    global wheelImage, wheelOdoImage

    pygame.mixer.pre_init()
    pygame.mixer.init()

    screen_rect = _uiAdapter.getScreen().get_rect()

    wheelImage = pygame.image.load("graphics/wheel.png")
    wheelOdoImage = pygame.image.load("graphics/wheel-odo.png")

    imageWidth = wheelImage.get_width() // 2
    imageHeight = wheelImage.get_height() // 2

    wheelRects['fl'] = wheelImage.get_rect(center=screen_rect.center).move(-imageWidth - OFF + XOFF, -imageHeight - OFF + YOFF)
    wheelRects['fr'] = wheelImage.get_rect(center=screen_rect.center).move(imageWidth + OFF + XOFF, -imageHeight - OFF + YOFF)
    wheelRects['bl'] = wheelImage.get_rect(center=screen_rect.center).move(-imageWidth - OFF + XOFF, imageHeight + OFF + YOFF)
    wheelRects['br'] = wheelImage.get_rect(center=screen_rect.center).move(imageWidth + OFF + XOFF, imageHeight + OFF + YOFF)
    wheelRects['middle'] = wheelImage.get_rect(center=screen_rect.center).move(XOFF, -YOFF)


def handleWheelPositions(topic, message, groups):
    global received  # , angle

    def updateWheel(wheelName, _values, index):
        wheel = wheelsMap[wheelName]
        odoStr = _values[index]
        statusStr = _values[index + 1]
        wheel['speed_status'] = int(statusStr)
        if statusStr == "0":
            wheel['odo'] = int(odoStr)

    received = True

    values = message.split(",")
    updateWheel('fl', values, 1)
    updateWheel('fr', values, 3)
    updateWheel('bl', values, 5)
    updateWheel('br', values, 7)


def handleDistances(topic, message, groups):
    global received  # , angle

    values = {int(v[0]): int(v[1]) for v in [v.split(":") for v in message.split(" ")] if v[0] != 'timestamp'}

    for a in values:
        radar[a] = values[a]


def handleWheelOrientations(topic, message, groups):
    global received  # , angle

    def updateWheel(wheelName, _values, index):
        wheel = wheelsMap[wheelName]
        angleStr = _values[index]
        statusStr = _values[index + 1]
        wheel['deg_status'] = int(statusStr)
        if angleStr != '-':
            _angle = int(angleStr)
            wheel['angle'] = _angle
            if 'wanted' not in wheel or screensComponent.selectedCardName == 'calibrateWheel':
                wheel['wanted'] = _angle

    received = True
    # print("** wheel positions = " + message)

    values = message.split(",")
    updateWheel('fl', values, 1)
    updateWheel('fr', values, 3)
    updateWheel('bl', values, 5)
    updateWheel('br', values, 7)


def handleStorageWrite(topic, message, groups):
    topics = topic[len("storage/write/wheels/cal/"):].split('/')

    wheelName = topics[0]

    if 'pid' == wheelName:
        pid = wheelsMap['pid']
        try:
            # noinspection PyTypeChecker
            pid[topics[1]] = float(message)
        except:
            pid[topics[1]] = message

    else:
        wheel = wheelsMap[wheelName]['cal']

        if topics[1] not in wheel:
            wheel[topics[1]] = {}

        sub = wheel[topics[1]]

        try:
            sub[topics[2]] = int(message)
        except:
            sub[topics[2]] = message


def handleShutdown(topic, message, groups):
    global _slaves_shutdown
    if message == 'now':
        screensComponent.selectCard('shutdown')
    elif message == 'slaves':
        _slaves_shutdown = True


def handleWheelsStatus(topic, message, groups):
    statusBarComponent.setWheelsStatus(message)


def handleJoystickStatus(topic, message, groups):
    statusBarComponent.setJoystickStatus(message)


def handleUptimeStatus(topic, message, groups):
    statusBarComponent.setUptime(message)


def handleScreenImage(topic, message, groups):
    setMainScreenImage(message)


def handleScreenSound(topic, message, groups):
    playScreenSound(message)


def setMainScreenImage(imageName):
    global _main_screen_image
    if imageName in _backgrounds:
        image = _backgrounds[imageName]
        _main_screen_image = image
    elif (imageName + ".png") in _backgrounds:
        image = _backgrounds[imageName + ".png"]
        _main_screen_image = image
    elif (imageName + ".jpg") in _backgrounds:
        image = _backgrounds[imageName + ".jpg"]
        _main_screen_image = image
    else:
        if os.path.exists("images/" + imageName + ".png"):
            imageName = imageName + ".png"
        elif os.path.exists("images/" + imageName + ".jpg"):
            imageName = imageName + ".jpg"

        if os.path.exists("images/" + imageName):
            image = pygame.image.load("images/" + imageName)
            _backgrounds[imageName] = image
            _main_screen_image = image
        else:
            _main_screen_image = None


def playScreenSound(soundName):
    if soundName in _sounds:
        sound = _sounds[soundName]
        sound.play()
    elif soundName + ".wav" in _sounds:
        sound = _sounds[soundName + ".wav"]
        sound.play()
    elif soundName + ".ogg" in _sounds:
        sound = _sounds[soundName + ".ogg"]
        sound.play()
    else:
        if os.path.exists("sounds/" + soundName + ".wav"):
            soundName = soundName + ".wav"
        elif os.path.exists("sounds/" + soundName + ".ogg"):
            soundName = soundName + ".ogg"
        if os.path.exists("sounds/" + soundName):
            sound = pygame.mixer.Sound("sounds/" + soundName)
            sound.set_volume(1.0)
            _sounds[soundName] = sound
            print("Playing " + soundName + " ...")
            sound.play()
            print("Played " + soundName)


def hasCalibrationLoaded():
    def hasCalibrationLoadedWheel(wheelName):
        wheel = wheelsMap[wheelName]['cal']
        if 'deg' in wheel:
            deg = wheel['deg']

            return '0' in deg and 'dir' in deg

        return False

    def hasCalibrationLoadedPID():
        pid = wheelsMap['pid']
        return 'p' in pid and 'i' in pid and 'd' in pid and 'd' in pid and 'g' in pid and 'deadband' in pid

    return hasCalibrationLoadedWheel('fr') and \
        hasCalibrationLoadedWheel('fl') and \
        hasCalibrationLoadedWheel('br') and \
        hasCalibrationLoadedWheel('bl') and \
        hasCalibrationLoadedPID()


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

        self.wheelImageAlpha = wheelImage.copy()
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
        wheel = wheelsMap[self.wheel_name]

        selectedWheelImage = wheelImage
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
        self.odo_image = _uiFactory.image(rect, wheelOdoImage, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.margin = (rect.width - wheelOdoImage.get_rect().width) // 2

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
        wheel = wheelsMap[self.wheel_name]

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
        self.gray = pygame.color.THECOLORS['gray48']

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

        pygame.draw.circle(surface, self.gray, self.rect.center, int(self.rect.width / 2.3), 1)
        pygame.draw.circle(surface, self.gray, self.rect.center, int(self.rect.width / 2.9), 1)
        pygame.draw.circle(surface, self.gray, self.rect.center, int(self.rect.width / 3.9), 1)
        pygame.draw.circle(surface, self.gray, self.rect.center, int(self.rect.width / 6), 1)
        pygame.draw.circle(surface, self.gray, self.rect.center, int(self.rect.width / 12), 1)
        for d in [pi8, pi8 * 3, pi8 * 5, pi8 * 7, pi8 * 9, pi8 * 11, pi8 * 13, pi8 * 15]:
            x1 = math.cos(d) * int(self.rect.width / 2.3) + self.rect.centerx
            y1 = math.sin(d) * int(self.rect.width / 2.3) + self.rect.centery
            x2 = math.cos(d) * int(self.rect.width / 12) + self.rect.centerx
            y2 = math.sin(d) * int(self.rect.width / 12) + self.rect.centery
            pygame.draw.line(surface, self.gray, (x1, y1), (x2, y2))

        pygame.draw.arc(_uiAdapter.getScreen(), (255, 0, 255), self.rect.inflate(limit(radar[0]), limit(radar[0])), pi8 * 3, pi8 * 5)  # 0º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(radar[45]), limit(radar[45])), pi8 * 1, pi8 * 3)  # 45º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(radar[90]), limit(radar[90])), pi8 * 15, pi8 * 1)  # 90º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(radar[135]), limit(radar[135])), pi8 * 13, pi8 * 15)  # 135º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(radar[180]), limit(radar[180])), pi8 * 11, pi8 * 13)  # 180º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(radar[225]), limit(radar[225])), pi8 * 9, pi8 * 11)  # 225º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(radar[270]), limit(radar[270])), pi8 * 7, pi8 * 9)  # 270º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(radar[315]), limit(radar[315])), pi8 * 5, pi8 * 7)  # 315º


class StatusBarComponent(gccui.Collection):
    def __init__(self, rect):
        super(StatusBarComponent, self).__init__(rect)

        self.battery_gray_image = pygame.image.load("graphics/battery-gray.png")
        self.stop_image = pygame.image.load("graphics/pause.png")
        self.stop_black_image = pygame.image.load("graphics/play.png")
        self.joystick_white_image = pygame.image.load("graphics/joystick-white.png")
        self.joystick_black_image = pygame.image.load("graphics/joystick-black.png")
        self.battery_component = _uiFactory.image(rect, self.battery_gray_image)
        self.stop_component = _uiFactory.image(rect, self.stop_image)
        self.joystick_component = _uiFactory.image(rect, self.joystick_black_image)
        self.uptime_component = _uiFactory.label(rect, "--:--", colour=pygame.color.THECOLORS['lightgray'], h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.addComponent(self.stop_component)
        self.addComponent(self.battery_component)
        self.addComponent(self.joystick_component)
        self.addComponent(self.uptime_component)
        self.redefineRect(rect)

    def redefineRect(self, rect):
        self.rect = rect
        self.battery_component.redefineRect(Rect(rect.right - self.battery_gray_image.get_width() - 8, rect.y, self.battery_gray_image.get_width(), self.battery_gray_image.get_height()))
        self.uptime_component.redefineRect(Rect(self.battery_component.rect.x - 60, rect.y, 50, 24))  # font size is bodge to make it render to right place
        self.joystick_component.redefineRect(Rect(self.uptime_component.rect.x - self.joystick_white_image.get_width() - 10, rect.y, self.joystick_white_image.get_width(), self.joystick_white_image.get_height()))
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
        self.uptime_component.setText(uptime)

    def setBatteryStatus(self, status):
        pass


def returnToStatusButtonClick(button, pos):
    screensComponent.selectCard('main')


class ScreenComponent(gccui.Collection):
    def __init__(self, rect):
        super(ScreenComponent, self).__init__(rect)

    def enter(self):
        pass

    def leave(self):
        pass

    def backToMainScreen(self):
        self.selectScreen('main')

    def backToMainScreenButtonClick(self, button, pos):
        self.selectScreen('main')

    def selectScreenButtonClick(self, name, button, pos):
        self.selectScreen(name)

    @staticmethod
    def selectScreen(name):
        selectedCardName = screensComponent.selectedCardName()
        if selectedCardName is not None:
            selectedComponent = screensComponent.cards[selectedCardName]
            selectedComponent.leave()
        selectedComponent = screensComponent.selectCard(name)
        if selectedComponent is not None:
            selectedComponent.enter()


class MainScreen(ScreenComponent):
    def __init__(self, rect):
        super(MainScreen, self).__init__(rect)

        self._last_activity = time.time()
        self.activity_timeout = 5
        self.image_only = False
        self.image = _uiFactory.image(_uiAdapter.getScreen().get_rect(), None)
        self.image.setVisible(False)
        self.addComponent(self.image)
        self.addComponent(_uiFactory.text_button(Rect(20, 410, 120, 50), "STOP", stopAllButtonClick))
        self.addComponent(_uiFactory.text_button(Rect(180, 410, 120, 50), "MENU", partial(self.selectScreenButtonClick, 'menu')))
        self.redefineRect(rect)

    def redefineRect(self, rect):
        super(MainScreen, self).redefineRect(rect)
        self.components[0].redefineRect(rect)
        self.components[1].redefineRect(Rect(rect.x + 20, rect.bottom - 70, 120, 50))
        self.components[2].redefineRect(Rect(rect.right - 140, rect.bottom - 70, 120, 50))

    def draw(self, surface):
        if self.image.getImage() != _main_screen_image:
            if self.image.isVisible() and _main_screen_image is None:
                self.image.setVisible(False)
            else:
                self.image.setImage(_main_screen_image)
                self.image.setVisible(True)
        if time.time() - self._last_activity > self.activity_timeout:
            if not self.image_only:
                for i in range(len(self.components) - 1):
                    self.components[i + 1].setVisible(False)
                self.image_only = True
        else:
            if self.image_only:
                for i in range(len(self.components) - 1):
                    self.components[i + 1].setVisible(True)
                self.image_only = False

        super(MainScreen, self).draw(surface)

    def mouseOver(self, mousePos):
        super(MainScreen, self).mouseOver(mousePos)
        self._last_activity = time.time()

    def mouseLeft(self, mousePos):
        super(MainScreen, self).mouseLeft(mousePos)
        self._last_activity = time.time()

    def mouseDown(self, mousePos):
        super(MainScreen, self).mouseDown(mousePos)
        self._last_activity = time.time()

    def mouseUp(self, mousePos):
        super(MainScreen, self).mouseUp(mousePos)
        self._last_activity = time.time()


class WheelsScreen(ScreenComponent):
    def __init__(self, rect):
        super(WheelsScreen, self).__init__(rect)

        self.addComponent(_uiFactory.text_button(Rect(10, 430, 90, 40), "STOP", stopAllButtonClick))
        self.addComponent(_uiFactory.text_button(Rect(220, 430, 90, 40), "MENU", partial(self.selectScreenButtonClick, 'menu')))
        self.addComponent(WheelComponent(wheelRects['fr'], 'fr', True))
        self.addComponent(WheelComponent(wheelRects['fl'], 'fl', True))
        self.addComponent(WheelComponent(wheelRects['br'], 'br', True))
        self.addComponent(WheelComponent(wheelRects['bl'], 'bl', True))
        self.addComponent(WheelStatusComponent(Rect(5, 38, 152, 32), 'fl'))
        self.addComponent(WheelStatusComponent(Rect(163, 38, 152, 32), 'fr'))
        self.addComponent(WheelStatusComponent(Rect(5, 74, 152, 32), 'bl'))
        self.addComponent(WheelStatusComponent(Rect(163, 74, 152, 32), 'br'))
        self.redefineRect(rect)

    def redefineRect(self, rect):
        super(WheelsScreen, self).redefineRect(rect)
        self.components[0].redefineRect(Rect(rect.x + 10, rect.bottom - 50, 90, 40))
        self.components[1].redefineRect(Rect(rect.right - 100, rect.bottom - 50, 90, 40))
        self.components[2].redefineRect(Rect(wheelRects['fr'].move(rect.x, rect.y)))
        self.components[3].redefineRect(Rect(wheelRects['fl'].move(rect.x, rect.y)))
        self.components[4].redefineRect(Rect(wheelRects['br'].move(rect.x, rect.y)))
        self.components[5].redefineRect(Rect(wheelRects['bl'].move(rect.x, rect.y)))
        self.components[6].redefineRect(Rect(rect.x + 5, rect.y + 38, 152, 32))
        self.components[7].redefineRect(Rect(rect.x + 163, rect.y + 38, 152, 32))
        self.components[8].redefineRect(Rect(rect.x + 5, rect.y + 74, 152, 32))
        self.components[9].redefineRect(Rect(rect.x + 163, rect.y + 74, 152, 32))

    def enter(self):
        super(WheelsScreen, self).enter()
        pyroslib.subscribe("wheel/deg/status", handleWheelOrientations)
        pyroslib.subscribe("wheel/speed/status", handleWheelPositions)

    def leave(self):
        super(WheelsScreen, self).enter()
        pyroslib.unsubscribe("wheel/deg/status")
        pyroslib.unsubscribe("wheel/speed/status")


class MenuScreen(ScreenComponent):
    def __init__(self, rect):
        super(MenuScreen, self).__init__(rect)

        self.addComponent(_uiFactory.text_button(Rect(50, 60, 220, 40), "WHEELS", partial(self.selectScreenButtonClick, 'wheels')))
        self.addComponent(_uiFactory.text_button(Rect(50, 110, 220, 40), "RADAR", partial(self.selectScreenButtonClick, 'radar')))
        self.addComponent(_uiFactory.text_button(Rect(50, 160, 220, 40), "CAL WHEELS", partial(self.selectScreenButtonClick, 'calibrateWheel')))
        self.addComponent(_uiFactory.text_button(Rect(50, 210, 220, 40), "CAL PID", partial(self.selectScreenButtonClick, 'calibratePID')))
        self.addComponent(_uiFactory.text_button(Rect(50, 380, 220, 40), "SHUTDOWN", partial(self.selectScreenButtonClick, 'shutdownConfirmation'), hint=gccui.UI_HINT.WARNING))
        self.addComponent(_uiFactory.text_button(Rect(50, 430, 220, 40), "MAIN", self.backToMainScreenButtonClick))
        self.redefineRect(rect)

    def redefineRect(self, rect):
        super(MenuScreen, self).redefineRect(rect)
        self.components[0].redefineRect(Rect(rect.x + 50, rect.y + 60, 220, 40))
        self.components[1].redefineRect(Rect(rect.x + 50, rect.y + 110, 220, 40))
        self.components[2].redefineRect(Rect(rect.x + 50, rect.y + 160, 220, 40))
        self.components[3].redefineRect(Rect(rect.x + 50, rect.y + 210, 220, 40))
        self.components[4].redefineRect(Rect(rect.x + 50, rect.bottom - 100, 220, 40))
        self.components[5].redefineRect(Rect(rect.x + 50, rect.bottom - 50, 220, 40))


class ShutdownConfirmationScreen(ScreenComponent):
    def __init__(self, rect):
        super(ShutdownConfirmationScreen, self).__init__(rect)

        self.addComponent(_uiFactory.label(Rect(50, 60, 220, 40), "Are you sure to shutdown?"))
        self.addComponent(_uiFactory.text_button(Rect(50, 110, 220, 40), "SHUTDOWN", self.startShutdownButtonClick, hint=gccui.UI_HINT.ERROR))
        self.addComponent(_uiFactory.text_button(Rect(50, 430, 220, 40), "BACK", self.backToMainScreenButtonClick))
        self.redefineRect(rect)

    def redefineRect(self, rect):
        super(ShutdownConfirmationScreen, self).redefineRect(rect)
        self.components[0].redefineRect(Rect(rect.x + 50, rect.y + 60, 220, 40))
        self.components[1].redefineRect(Rect(rect.x + 50, rect.y + 110, 220, 40))
        self.components[2].redefineRect(Rect(rect.x + 50, rect.bottom - 50, 220, 40))

    @staticmethod
    def startShutdownButtonClick(button, pos):
        pyroslib.publish("system/shutdown", "secret_message_now")
        pyroslib.publish("screen/say", "Shutdown, initiated, , ,  Waiting for wheels to stop.")


class ShutdownScreen(ScreenComponent):
    def __init__(self, rect):
        super(ShutdownScreen, self).__init__(rect)

        self.addComponent(_uiFactory.label(Rect(50, 160, 220, 40), "Shutdown in progress..."))
        self.slaves_label = _uiFactory.label(Rect(50, 200, 220, 40), "Slaves have shutdown")
        self.addComponent(self.slaves_label)

    def redefineRect(self, rect):
        super(ShutdownScreen, self).redefineRect(rect)
        self.components[0].redefineRect(Rect(rect.x + 50, rect.y + 160, 220, 40))
        self.components[1].redefineRect(Rect(rect.x + 50, rect.y + 200, 220, 40))

    def draw(self, surface):
        self.slaves_label.setVisible(_slaves_shutdown)
        super(ShutdownScreen, self).draw(surface)


class CalibrateWheelScreen(ScreenComponent):

    class RectangleDecoration(gccui.Component):
        def __init__(self, colour):
            super(CalibrateWheelScreen.RectangleDecoration, self).__init__(None)  # Call super constructor to store rectable
            self.colour = colour
            self.corner_width = 20

        def draw(self, surface):
            pygame.draw.ellipse(surface, self.colour, self.rect)
            # pygame.draw.rect(surface, self.colour, self.rect)

    @staticmethod
    def back_deco():
        return CalibrateWheelScreen.RectangleDecoration(pygame.color.THECOLORS['gray24'])

    @staticmethod
    def over_deco():
        return CalibrateWheelScreen.RectangleDecoration(pygame.color.THECOLORS['gray64'])

    def createWheelButton(self, name):
        return gccui.Button(wheelRects[name],
                            partial(self.selectWheelButtonClick, name),
                            label=WheelComponent(wheelRects[name], name, False),
                            background_decoration=self.back_deco(),
                            mouse_over_decoration=self.over_deco())

    def __init__(self, rect):
        super(CalibrateWheelScreen, self).__init__(rect)
        self.card = gccui.CardsCollection(self.rect)
        self.addComponent(self.card)
        self.select = gccui.Collection(self.rect)
        self.loading = gccui.Collection(self.rect)
        self.calibrate = gccui.Collection(self.rect)
        self.card.addCard('select', self.select)
        self.card.addCard('loading', self.loading)
        self.card.addCard('calibrate', self.calibrate)
        self.card.selectCard('select')

        self.select.addComponent(_uiFactory.text_button(Rect(10, 430, 90, 40), "STOP", stopAllButtonClick))
        self.select.addComponent(_uiFactory.text_button(Rect(220, 430, 90, 40), "CANCEL", self.backToMainScreenButtonClick))
        self.select.addComponent(self.createWheelButton('fr'))
        self.select.addComponent(self.createWheelButton('fl'))
        self.select.addComponent(self.createWheelButton('br'))
        self.select.addComponent(self.createWheelButton('bl'))

        self.wheel_name_label = _uiFactory.label(Rect(10, 50, 310, 20), "", h_alignment=gccui.ALIGNMENT.CENTER)
        self.calibrate.addComponent(self.wheel_name_label)
        self.calibrate.addComponent(_uiFactory.text_button(Rect(10, 430, 90, 40), "STOP", stopAllButtonClick))
        self.calibrate.addComponent(_uiFactory.text_button(Rect(120, 430, 90, 40), "SAVE", self.saveCalibrationWheelButtonClick))
        self.calibrate.addComponent(_uiFactory.text_button(Rect(220, 430, 90, 40), "CANCEL", self.backToMainScreenButtonClick))
        self.calibrate.addComponent(_uiFactory.text_button(Rect(8, 170, 80, 40), "<", partial(self.moveWheelClick, -1)))
        self.calibrate.addComponent(_uiFactory.text_button(Rect(8, 240, 80, 40), "<<", partial(self.moveWheelClick, -10)))
        self.calibrate.addComponent(_uiFactory.text_button(Rect(232, 170, 80, 40), ">", partial(self.moveWheelClick, 1)))
        self.calibrate.addComponent(_uiFactory.text_button(Rect(232, 240, 80, 40), ">>", partial(self.moveWheelClick, 10)))
        self.degToggleButton = _uiFactory.text_button(Rect(20, 330, 80, 40), "A: --->", self.degToggleButtonClick)
        self.steerToggleButton = _uiFactory.text_button(Rect(120, 330, 80, 40), "S: --->", self.steerToggleButtonClick)
        self.speedToggleButton = _uiFactory.text_button(Rect(220, 330, 80, 40), "D: --->", self.speedToggleButtonClick)
        self.calibrate.addComponent(self.degToggleButton)
        self.calibrate.addComponent(self.steerToggleButton)
        self.calibrate.addComponent(self.speedToggleButton)

        self.wheel = WheelComponent(wheelRects['middle'], '', True)
        self.calibrate.addComponent(self.wheel)

        self.loading.addComponent(_uiFactory.text_button(Rect(10, 430, 90, 40), "STOP", stopAllButtonClick))
        self.loading.addComponent(_uiFactory.text_button(Rect(220, 430, 90, 40), "CANCEL", self.backToMainScreenButtonClick))
        self.loading.addComponent(_uiFactory.label(self.rect, "Loading calibration", h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE))

        self.selected_wheel_name = None
        self.redefineRect(rect)

    def redefineRect(self, rect):
        super(CalibrateWheelScreen, self).redefineRect(rect)
        self.card.redefineRect(rect)
        self.select.components[0].redefineRect(Rect(rect.x + 10, rect.bottom - 50, 90, 40))
        self.select.components[1].redefineRect(Rect(rect.right - 100, rect.bottom - 50, 90, 40))
        self.select.components[2].redefineRect(wheelRects['fr'].move(rect.x, rect.y))
        self.select.components[3].redefineRect(wheelRects['fl'].move(rect.x, rect.y))
        self.select.components[4].redefineRect(wheelRects['br'].move(rect.x, rect.y))
        self.select.components[5].redefineRect(wheelRects['bl'].move(rect.x, rect.y))

        self.calibrate.components[0].redefineRect(Rect(rect.x + 10, rect.y + 50, 310, 20))
        self.calibrate.components[1].redefineRect(Rect(rect.x + 10, rect.bottom - 50, 90, 40))
        self.calibrate.components[2].redefineRect(Rect(rect.x + 120, rect.bottom - 50, 90, 40))
        self.calibrate.components[3].redefineRect(Rect(rect.x + 220, rect.bottom - 50, 90, 40))
        self.calibrate.components[4].redefineRect(Rect(rect.x + 8, rect.y + 170, 80, 40))
        self.calibrate.components[5].redefineRect(Rect(rect.x + 8, rect.y + 240, 80, 40))
        self.calibrate.components[6].redefineRect(Rect(rect.x + 232, rect.y + 170, 80, 40))
        self.calibrate.components[7].redefineRect(Rect(rect.x + 232, rect.y + 240, 80, 40))
        self.calibrate.components[8].redefineRect(Rect(rect.x + 20, rect.y + 330, 80, 40))
        self.calibrate.components[9].redefineRect(Rect(rect.x + 120, rect.y + 330, 80, 40))
        self.calibrate.components[10].redefineRect(Rect(rect.x + 220, rect.y + 330, 80, 40))
        self.calibrate.components[11].redefineRect(wheelRects['middle'].move(rect.x, rect.y))

        self.loading.components[0].redefineRect(Rect(rect.x + 10, rect.bottom - 50, 90, 40))
        self.loading.components[1].redefineRect(Rect(rect.right - 100, rect.bottom - 50, 90, 40))
        self.loading.components[2].redefineRect(rect)

    def enter(self):
        super(CalibrateWheelScreen, self).enter()
        pyroslib.subscribe("wheel/deg/status", handleWheelOrientations)
        pyroslib.subscribe("wheel/speed/status", handleWheelPositions)
        self.card.selectCard('select')
        pyroslib.publish("storage/read/wheels/cal", "")

    def leave(self):
        super(CalibrateWheelScreen, self).leave()
        pyroslib.unsubscribe("wheel/deg/status")
        pyroslib.unsubscribe("wheel/speed/status")

    def setSelectedWheelName(self, selected_wheel_name):
        self.selected_wheel_name = selected_wheel_name
        self.wheel.wheel_name = selected_wheel_name
        self._updateToggleButton(self.degToggleButton, 'A', wheelsMap[selected_wheel_name]['cal']['deg']['dir'])
        self._updateToggleButton(self.steerToggleButton, 'S', wheelsMap[selected_wheel_name]['cal']['steer']['dir'])
        self._updateToggleButton(self.speedToggleButton, 'D', wheelsMap[selected_wheel_name]['cal']['speed']['dir'])
        self.wheel_name_label.setText("Wheel " + selected_wheel_name.upper())

    def draw(self, surface):
        super(CalibrateWheelScreen, self).draw(surface)
        if self.card.selectedCardComponent == self.loading and hasCalibrationLoaded():
            self.card.selectCard('calibrate')

    @staticmethod
    def _updateToggleButton(toggleButton, kind, direction):
        toggleButton.getLabel().setText(kind + ": <---" if direction < 0 else kind + ": --->")

    def degToggleButtonClick(self, button, pos):
        wheel = wheelsMap[self.selected_wheel_name]
        direction = wheelsMap[self.selected_wheel_name]['cal']['deg']['dir']
        direction = -direction
        wheelsMap[self.selected_wheel_name]['cal']['deg']['dir'] = direction
        print("Old value " + str(-direction) + ", new value " + str(direction))
        pyroslib.publish("storage/write/wheels/cal/" + self.selected_wheel_name + "/deg/dir", str(direction))
        self._updateToggleButton(self.degToggleButton, 'A', direction)

    def steerToggleButtonClick(self, button, pos):
        wheel = wheelsMap[self.selected_wheel_name]
        direction = wheelsMap[self.selected_wheel_name]['cal']['steer']['dir']
        direction = -direction
        wheelsMap[self.selected_wheel_name]['cal']['steer']['dir'] = direction
        print("Old value " + str(-direction) + ", new value " + str(direction))
        pyroslib.publish("storage/write/wheels/cal/" + self.selected_wheel_name + "/steer/dir", str(direction))
        self._updateToggleButton(self.steerToggleButton, 'S', direction)

    def speedToggleButtonClick(self, button, pos):
        wheel = wheelsMap[self.selected_wheel_name]
        direction = wheelsMap[self.selected_wheel_name]['cal']['speed']['dir']
        direction = -direction
        wheelsMap[self.selected_wheel_name]['cal']['speed']['dir'] = direction
        print("Old value " + str(-direction) + ", new value " + str(direction))
        pyroslib.publish("storage/write/wheels/cal/" + self.selected_wheel_name + "/speed/dir", str(direction))
        self._updateToggleButton(self.speedToggleButton, 'D', direction)

    def saveCalibrationWheelButtonClick(self, button, pos):
        wheel = wheelsMap[self.selected_wheel_name]
        calDeg = wheel['cal']['deg']['0']
        _angle = wheel['angle']
        value = _angle + calDeg
        if value < 0:
            value += 360

        if value >= 360:
            value -= 360

        wheel['wanted'] = 0

        print("Old value " + str(calDeg) + ", angle " + str(_angle) + ", new value " + str(value))

        pyroslib.publish("storage/write/wheels/cal/" + self.selected_wheel_name + "/deg/0", str(value))
        pyroslib.publish("wheel/" + self.selected_wheel_name + "/deg", str(0))
        screensComponent.selectCard('main')

    def moveWheel(self, deltaAngle):
        wheel = wheelsMap[self.selected_wheel_name]
        if 'wanted' in wheel:
            wanted = wheel['wanted']
            wanted += deltaAngle
            if wanted < 0:
                wanted += 360
            if wanted >= 360:
                wanted -= 360
            wheel['wanted'] = wanted

            pyroslib.publish("wheel/" + self.selected_wheel_name + "/deg", str(wanted))

    def moveWheelClick(self, amount, button, pos):
        self.moveWheel(amount)

    def selectWheelButtonClick(self, wheel_name, button, pos):
        self.card.selectCard('loading')
        self.setSelectedWheelName(wheel_name)


class PIDUIComponent(gccui.Collection):
    def __init__(self, rect, name, ui_label_text):
        super(PIDUIComponent, self).__init__(rect)
        self.name = name

        self.addComponent(_uiFactory.label(Rect(rect.x + 112, rect.y, 30, 50), ui_label_text, v_alignment=gccui.ALIGNMENT.MIDDLE))

        self.left = _uiFactory.label(Rect(rect.x + 100, rect.y, 64, 50), '', h_alignment=gccui.ALIGNMENT.RIGHT, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.right = _uiFactory.label(Rect(rect.x + 164, rect.y, 30, 50), '', h_alignment=gccui.ALIGNMENT.LEFT, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.addComponent(self.left)
        self.addComponent(self.right)

        self.addComponent(_uiFactory.text_button(Rect(rect.x, rect.y, 30, 40), "<", self.onClickMinus1))
        self.addComponent(_uiFactory.text_button(Rect(rect.x + 34, rect.y, 30, 40), "<<", self.onClickMinus01))
        self.addComponent(_uiFactory.text_button(Rect(rect.x + 34 * 2, rect.y, 30, 40), "<<<", self.onClickMinus001))
        self.addComponent(_uiFactory.text_button(Rect(rect.right - 30 - 34 * 2, rect.y, 30, 40), ">>>", self.onClickPlus001))
        self.addComponent(_uiFactory.text_button(Rect(rect.right - 30 - 34, rect.y, 30, 40), ">>", self.onClickPlus01))
        self.addComponent(_uiFactory.text_button(Rect(rect.right - 30, rect.y, 30, 40), ">", self.onClickPlus1))
        self.redefineRect(rect)

    def redefineRect(self, rect):
        super(PIDUIComponent, self).redefineRect(rect)
        self.components[0].redefineRect(Rect(rect.x + 112, rect.y, 30, 50))
        self.components[1].redefineRect(Rect(rect.x + 100, rect.y, 64, 50))
        self.components[2].redefineRect(Rect(rect.x + 164, rect.y, 30, 50))

        self.components[3].redefineRect(Rect(rect.x, rect.y, 30, 40))
        self.components[4].redefineRect(Rect(rect.x + 34, rect.y, 30, 40))
        self.components[5].redefineRect(Rect(rect.x + 34 * 2, rect.y, 30, 40))
        self.components[6].redefineRect(Rect(rect.right - 30 - 34 * 2, rect.y, 30, 40))
        self.components[7].redefineRect(Rect(rect.right - 30 - 34, rect.y, 30, 40))
        self.components[8].redefineRect(Rect(rect.right - 30, rect.y, 30, 40))
        self.components[8].redefineRect(Rect(rect.right - 30, rect.y, 30, 40))

    def draw(self, surace):
        value = wheelsMap['pid'][self.name]

        s = "{0:.2f}".format(value)
        i = s.index('.')
        left = s[0:i + 1]
        right = s[i + 1:]
        self.left.setText(left)
        self.right.setText(right)

        super(PIDUIComponent, self).draw(surace)

    def onClickPlus1(self, button, pos):
        pid = wheelsMap['pid']
        value = pid[self.name]
        value += 1.0
        pid[self.name] = value

    def onClickMinus1(self, button, pos):
        pid = wheelsMap['pid']
        value = pid[self.name]
        value -= 1.0
        pid[self.name] = value

    def onClickPlus01(self, button, pos):
        pid = wheelsMap['pid']
        value = pid[self.name]
        value += 0.1
        pid[self.name] = value

    def onClickMinus01(self, button, pos):
        pid = wheelsMap['pid']
        value = pid[self.name]
        value -= 0.1
        pid[self.name] = value

    def onClickPlus001(self, button, pos):
        pid = wheelsMap['pid']
        value = pid[self.name]
        value += 0.01
        pid[self.name] = value

    def onClickMinus001(self, button, pos):
        pid = wheelsMap['pid']
        value = pid[self.name]
        value -= 0.01
        pid[self.name] = value


class CalibratePIDScreen(ScreenComponent):
    def __init__(self, rect):
        super(CalibratePIDScreen, self).__init__(rect)

        self.card = gccui.CardsCollection(self.rect)
        self.addComponent(self.card)
        self.loading = gccui.Collection(self.rect)
        self.calibrate = gccui.Collection(self.rect)
        self.card.addCard('loading', self.loading)
        self.card.addCard('calibrate', self.calibrate)
        self.card.selectCard('loading')

        self.calibrate.addComponent(_uiFactory.text_button(Rect(10, 430, 90, 40), "STOP", stopAllButtonClick))
        self.calibrate.addComponent(_uiFactory.text_button(Rect(120, 430, 90, 40), "SAVE", self.saveCalibrationPIDButtonClick))
        self.calibrate.addComponent(_uiFactory.text_button(Rect(220, 430, 90, 40), "BACK", self.backToMainScreenButtonClick))
        self.calibrate.addComponent(PIDUIComponent(Rect(10, 72, 300, 50), 'p', 'p'))
        self.calibrate.addComponent(PIDUIComponent(Rect(10, 122, 300, 50), 'i', 'i'))
        self.calibrate.addComponent(PIDUIComponent(Rect(10, 172, 300, 50), 'd', 'd'))
        self.calibrate.addComponent(PIDUIComponent(Rect(10, 222, 300, 50), 'g', 'g'))
        self.calibrate.addComponent(PIDUIComponent(Rect(10, 272, 300, 50), 'deadband', 'db'))

        self.loading.addComponent(_uiFactory.label(self.rect, "Loading calibration", h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE))
        self.loading.addComponent(_uiFactory.text_button(Rect(10, 430, 90, 40), "STOP", stopAllButtonClick))
        self.loading.addComponent(_uiFactory.text_button(Rect(220, 430, 90, 40), "CANCEL", self.backToMainScreenButtonClick))

        self.redefineRect(rect)

    def redefineRect(self, rect):
        super(CalibratePIDScreen, self).redefineRect(rect)
        self.calibrate.components[0].redefineRect(Rect(rect.x + 10, rect.bottom - 50, 90, 40))
        self.calibrate.components[1].redefineRect(Rect(rect.x + 120, rect.bottom - 50, 90, 40))
        self.calibrate.components[2].redefineRect(Rect(rect.right - 100, rect.bottom - 50, 90, 40))
        self.calibrate.components[3].redefineRect(Rect(rect.x + 10, rect.y + 72, 300, 50))
        self.calibrate.components[4].redefineRect(Rect(rect.x + 10, rect.y + 122, 300, 50))
        self.calibrate.components[5].redefineRect(Rect(rect.x + 10, rect.y + 172, 300, 50))
        self.calibrate.components[6].redefineRect(Rect(rect.x + 10, rect.y + 222, 300, 50))
        self.calibrate.components[7].redefineRect(Rect(rect.x + 10, rect.y + 272, 300, 50))

        self.loading.components[0].redefineRect(rect)
        self.loading.components[1].redefineRect(Rect(rect.x + 10, rect.bottom - 50, 90, 40))
        self.loading.components[2].redefineRect(Rect(rect.right - 100, rect.bottom - 50, 90, 40))

    def draw(self, surface):
        super(CalibratePIDScreen, self).draw(surface)
        if self.card.selectedCardComponent == self.loading and hasCalibrationLoaded():
            self.card.selectCard('calibrate')

    def enter(self):
        super(CalibratePIDScreen, self).enter()
        self.card.selectCard('loading')
        pyroslib.publish("storage/read/wheels/cal", "")

    def leave(self):
        super(CalibratePIDScreen, self).leave()

    @staticmethod
    def saveCalibrationPIDButtonClick(button, pos):
        pyroslib.publish("storage/write/wheels/cal/pid/p", str(wheelsMap['pid']['p']))
        pyroslib.publish("storage/write/wheels/cal/pid/i", str(wheelsMap['pid']['i']))
        pyroslib.publish("storage/write/wheels/cal/pid/d", str(wheelsMap['pid']['d']))
        pyroslib.publish("storage/write/wheels/cal/pid/g", str(wheelsMap['pid']['g']))
        pyroslib.publish("storage/write/wheels/cal/pid/deadband", str(wheelsMap['pid']['deadband']))

        # returnToStatusButtonClick(button, pos)


class RadarScreen(ScreenComponent):
    def __init__(self, rect):
        super(RadarScreen, self).__init__(rect)
        self.addComponent(_uiFactory.text_button(Rect(10, 430, 90, 40), "STOP", stopAllButtonClick))
        self.addComponent(_uiFactory.text_button(Rect(220, 430, 90, 40), "BACK", self.backToMainScreenButtonClick))
        y_off = 100
        self.addComponent(Radar(Rect(50, 50, 220, 220), 1300))
        self.distance_labels = {
            0: _uiFactory.label(Rect(160, 40, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE),
            45: _uiFactory.label(Rect(260, 70, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE),
            90: _uiFactory.label(Rect(290, 160, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE),
            135: _uiFactory.label(Rect(260, 260, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE),
            180: _uiFactory.label(Rect(160, 290, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE),
            225: _uiFactory.label(Rect(70, 260, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE),
            270: _uiFactory.label(Rect(40, 160, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE),
            315: _uiFactory.label(Rect(70, 70, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE)
        }
        for a in self.distance_labels:
            self.addComponent(self.distance_labels[a])

        self.right_distance_label = _uiFactory.label(Rect(290, 290, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.addComponent(self.right_distance_label)
        self.redefineRect(rect)

    def redefineRect(self, rect):
        super(RadarScreen, self).redefineRect(rect)
        y_off = 100
        self.components[0].redefineRect(Rect(rect.x + 10, rect.bottom - 50, 90, 40))
        self.components[1].redefineRect(Rect(rect.right - 100, rect.bottom - 50, 90, 40))

        self.components[2].redefineRect(Rect(rect.x + 50, rect.y + y_off + 10, 220, 220))
        self.components[3].redefineRect(Rect(rect.x + 160, rect.y + y_off, 0, 0))
        self.components[4].redefineRect(Rect(rect.x + 260, rect.y + y_off + 30, 0, 0))
        self.components[5].redefineRect(Rect(rect.x + 290, rect.y + y_off + 120, 0, 0))
        self.components[6].redefineRect(Rect(rect.x + 260, rect.y + y_off + 220, 0, 0))
        self.components[7].redefineRect(Rect(rect.x + 160, rect.y + y_off + 250, 0, 0))
        self.components[8].redefineRect(Rect(rect.x + 70, rect.y + y_off + 220, 0, 0))
        self.components[9].redefineRect(Rect(rect.x + 40, rect.y + y_off + 120, 0, 0))
        self.components[10].redefineRect(Rect(rect.x + 70, rect.y + y_off + 30, 0, 0))
        self.components[11].redefineRect(Rect(rect.x + 290, rect.y + y_off + 250, 0, 0))

    def draw(self, surface):
        for a in radar:
            self.distance_labels[a].setText(str(radar[a]))

        super(RadarScreen, self).draw(surface)

    def enter(self):
        super(RadarScreen, self).enter()
        pyroslib.subscribe("sensor/distance", handleDistances)

    def leave(self):
        super(RadarScreen, self).leave()
        pyroslib.unsubscribe("distance/deg")


def init(uiFactory, uiAdapter, font, smallFont):
    global _uiFactory, _uiAdapter, screensComponent, topComponent, statusBarComponent, _font, _smallFont
    _uiFactory = uiFactory
    _uiAdapter = uiAdapter
    _font = font
    _smallFont = smallFont

    pyroslib.subscribe("screen/image", handleScreenImage)
    pyroslib.subscribe("screen/sound", handleScreenSound)
    pyroslib.subscribe("storage/write/wheels/cal/#", handleStorageWrite)
    pyroslib.subscribe("wheel/feedback/status", handleWheelsStatus)
    pyroslib.subscribe("joystick/status", handleJoystickStatus)
    pyroslib.subscribe("rover/status/uptime", handleUptimeStatus)
    pyroslib.subscribe("shutdown/announce", handleShutdown)

    initGui()

    screen_rect = _uiAdapter.getScreen().get_rect()

    topComponent = gccui.Collection(screen_rect)
    statusBarComponent = StatusBarComponent(Rect(0, 0, screen_rect.width, 20))
    topComponent.addComponent(statusBarComponent)

    screensComponent = gccui.CardsCollection(screen_rect)
    screensComponent.addCard('main', MainScreen(screen_rect))
    screensComponent.addCard('wheels', WheelsScreen(screen_rect))
    screensComponent.addCard('menu', MenuScreen(screen_rect))
    screensComponent.addCard('calibrateWheel', CalibrateWheelScreen(screen_rect))
    screensComponent.addCard('calibratePID', CalibratePIDScreen(screen_rect))
    screensComponent.addCard('radar', RadarScreen(screen_rect))
    screensComponent.addCard('shutdown', ShutdownScreen(screen_rect))
    screensComponent.addCard('shutdownConfirmation', ShutdownConfirmationScreen(screen_rect))
    topComponent.addComponent(screensComponent)

    main = screensComponent.selectCard('main')
    main.enter()
    setMainScreenImage("gcc-portrait.png")

    uiAdapter.setTopComponent(topComponent)
