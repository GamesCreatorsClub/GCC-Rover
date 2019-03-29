#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import gccui
import os
import pygame
import pyroslib
import roverscreencomponents
import time
from functools import partial
from pygame import Rect
from roverscreencomponents import WheelComponent, WheelStatusComponent, Radar, CPUComponent, TemperatureComponent, StatusBarComponent, StatsGraph, Stats

received = False

RADAR_ANGLES = [0, 45, 90, 135, 180, 225, 270, 315]

_radar = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0, 'status': '', 'timestamp': 0.0}
_last_radar = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0, 'status': '', 'timestamp': 0.0}
_radar_status = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0}

angle = 0.0

_uiFactory = None
_uiAdapter = None
_font = None
_smallFont = None
screensComponent = None
topComponent = None
statusBarComponent = None
systemStatusScreen = None
_slaves_shutdown = False
_main_screen_image = None
_backgrounds = {}
_sounds = {}
_wheelRects = {'fl': None, 'fr': None, 'bl': None, 'br': None}

_stats = {'mAh': Stats(), 'wtmAh': Stats(), 'rpimAh': Stats(), 'dmAh': Stats(), 'smAh': Stats(), 'ebp': Stats(), 'cpu_load': Stats(), 'cpu_temp': Stats()}

_stats_details_order = ['mAh', 'wtmAh', 'rpimAh', 'dmAh', 'smAh', 'ebp', 'cpu_load', 'cpu_temp']
_stats_details = {
    'mAh': {'name': 'mAh', 'units': 'mAh', 'max': 3000, 'warning': 1200, 'critical': 1600},
    'wtmAh': {'name': 'Wheels mAh', 'units': 'mAh', 'max': 3000},
    'rpimAh': {'name': 'RPis mAh', 'units': 'mAh', 'max': 3000},
    'dmAh': {'name': 'Steer mAh', 'units': 'mAh', 'max': 3000},
    'smAh': {'name': 'Drive mAh', 'units': 'mAh', 'max': 3000},
    'ebp': {'name': 'Battery %', 'units': '%', 'max': 100, 'warning': 40, 'critical': 20},
    'cpu_load': {'name': 'CPU Load', 'units': '%', 'max': 100, 'warning': 60, 'critical': 80},
    'cpu_temp': {'name': 'CPU Temp', 'units': 'ºC', 'max': 100, 'warning': 70, 'critical': 75}
}


def _createTemplateWheel(distance_index):
    return {
        'angle': 0,
        'deg_status': 0,
        'speed_status': 0,
        'odo': 0,
        'cal': {},
        'dindex': distance_index,
        'deg': {}
    }


_wheelsMap = {'fl': _createTemplateWheel(0), 'fr': _createTemplateWheel(2), 'bl': _createTemplateWheel(4), 'br': _createTemplateWheel(6), 'pid': {}}


def getRadar():
    return _radar, _last_radar, _radar_status


def getWheelAngleAndStatus(wheel_name):
    wheel = _wheelsMap[wheel_name]

    status = wheel['deg_status'] | wheel['speed_status']
    angle = wheel['angle']

    return angle, status


def getWheelOdoAndStatus(wheel_name):
    wheel = _wheelsMap[wheel_name]
    status = wheel['deg_status'] | wheel['speed_status']
    odo = wheel['odo']

    return odo, status


def stopAllButtonClick(button, pos):
    pyroslib.publish("wheel/stop", "toggle")


def initGui():
    pygame.mixer.pre_init()
    pygame.mixer.init()

    screen_rect = _uiAdapter.getScreen().get_rect()

    OFF = 10
    XOFF = 0
    YOFF = 15

    wheelImage = pygame.image.load("graphics/wheel.png")
    # wheelOdoImage = pygame.image.load("graphics/wheel-odo.png")

    imageWidth = wheelImage.get_width() // 2
    imageHeight = wheelImage.get_height() // 2

    _wheelRects['fl'] = wheelImage.get_rect(center=screen_rect.center).move(-imageWidth - OFF + XOFF, -imageHeight - OFF + YOFF)
    _wheelRects['fr'] = wheelImage.get_rect(center=screen_rect.center).move(imageWidth + OFF + XOFF, -imageHeight - OFF + YOFF)
    _wheelRects['bl'] = wheelImage.get_rect(center=screen_rect.center).move(-imageWidth - OFF + XOFF, imageHeight + OFF + YOFF)
    _wheelRects['br'] = wheelImage.get_rect(center=screen_rect.center).move(imageWidth + OFF + XOFF, imageHeight + OFF + YOFF)
    _wheelRects['middle'] = wheelImage.get_rect(center=screen_rect.center).move(XOFF, -YOFF)

    roverscreencomponents.init(_uiFactory, _uiAdapter, _font, _smallFont, screen_rect, _wheelRects)


def handleWheelPositions(topic, message, groups):
    global received  # , angle

    def updateWheel(wheelName, _values, index):
        wheel = _wheelsMap[wheelName]
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

    def convertValue(k, v):
        if k == 'timestamp':
            return float(v)
        elif k == 'status':
            return str(v)
        else:
            return int(v)

    def convertKey(k):
        if k == 'timestamp':
            return k
        elif k == 'status':
            return k
        else:
            return int(k)

    values = {convertKey(v[0]): convertValue(v[0], v[1]) for v in [v.split(":") for v in message.split(" ")]}

    for k, v in _radar.items():
        _last_radar[k] = v

    for a in values:
        _radar[a] = values[a]

    status_str = _radar['status']
    del _radar['status']
    i = 0
    # print("Received status: " + str(status_str))
    for angle in RADAR_ANGLES:
        _radar_status[angle] = int(status_str[i:i+2], 16)
        i += 2


def handleWheelOrientations(topic, message, groups):
    global received  # , angle

    def updateWheel(wheelName, _values, index):
        wheel = _wheelsMap[wheelName]
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
        pid = _wheelsMap['pid']
        try:
            # noinspection PyTypeChecker
            pid[topics[1]] = float(message)
        except:
            pid[topics[1]] = message

    else:
        wheel = _wheelsMap[wheelName]['cal']

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
    status = {s[0]: s[1] for s in [s.split(":") for s in message.split(" ")]}
    if 's' in status:
        statusBarComponent.setWheelsStatus(status['s'])


def handleJoystickStatus(topic, message, groups):
    statusBarComponent.setJoystickStatus(message)


def handleUptimeStatus(topic, message, groups):
    statusBarComponent.setUptime(message)


def handleCurrentStatus(topic, message, groups):

    status = {s[0]: s[1] for s in [s.split(":") for s in message.split(" ")]}
    mAh = None

    if 't' in status:
        mAh = int(float(status['t']))
        last_mAh = _stats['mAh'].lastValue()
        _stats['mAh'].add(mAh)

    if 'wtmAh' in status:
        wtmAh = int(float(status['wtmAh']))
        _stats['wtmAh'].add(wtmAh)
        if mAh is not None:
            _stats['rpimAh'].add(mAh - wtmAh)

    if 'dmAh' in status:
        _stats['dmAh'].add(int(float(status['dmAh'])))

    if 'smAh' in status:
        _stats['smAh'].add(int(float(status['smAh'])))

    if 'ebp' in status:
        ebp = int(float(status['ebp']))
        _stats['ebp'].add(ebp)
        statusBarComponent.setBatteryPercentage(ebp)

    if 'bs' in status:
        bs = status['bs']
        statusBarComponent.setBatteryStatus(bs)

    systemStatusScreen.updateCurrent(_stats)


def handleCPUStatus(topic, message, groups):
    status = {s[0]: s[1] for s in [s.split(":") for s in message.split(" ")]}
    if 'temp' in status:
        temp = int(float(status['temp']))
        last_temp = _stats['cpu_temp'].lastValue()
        _stats['cpu_temp'].add(temp)
        statusBarComponent.setTemperature(temp)
        systemStatusScreen.setTemperature(temp)
        if temp >= 70 and temp < 75 and (last_temp is None or last_temp < 70):
            statusBarComponent.setTemperatureStatus('warning')
            systemStatusScreen.setTemperatureStatus('warning')
        elif temp >= 75 and (last_temp is None or last_temp < 75):
            statusBarComponent.setTemperatureStatus('critical')
            systemStatusScreen.setTemperatureStatus('critical')
        elif temp < 70 and (last_temp is None or last_temp >= 70):
            statusBarComponent.setTemperatureStatus('nominal')
            systemStatusScreen.setTemperatureStatus('nominal')

        if 'load' in status:
            cpu_load = int(float(status['load']))
            _stats['cpu_load'].add(cpu_load)
            systemStatusScreen.setCPULoad(cpu_load)


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
        wheel = _wheelsMap[wheelName]['cal']
        if 'deg' in wheel:
            deg = wheel['deg']

            return '0' in deg and 'dir' in deg

        return False

    def hasCalibrationLoadedPID():
        pid = _wheelsMap['pid']
        return 'p' in pid and 'i' in pid and 'd' in pid and 'd' in pid and 'g' in pid and 'deadband' in pid

    return hasCalibrationLoadedWheel('fr') and \
        hasCalibrationLoadedWheel('fl') and \
        hasCalibrationLoadedWheel('br') and \
        hasCalibrationLoadedWheel('bl') and \
        hasCalibrationLoadedPID()


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

    def selectScreenCallback(self, screen_name):
        return partial(self.selectScreenButtonClick, screen_name)

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
        self.addComponent(_uiFactory.text_button(Rect(180, 410, 120, 50), "MENU", self.selectScreenCallback('main_menu')))
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
        wheelImage = pygame.image.load("graphics/wheel.png")
        wheelOdoImage = pygame.image.load("graphics/wheel-odo.png")

        self.addComponent(_uiFactory.text_button(Rect(10, 430, 90, 40), "STOP", stopAllButtonClick))
        self.addComponent(_uiFactory.text_button(Rect(220, 430, 90, 40), "MENU", self.selectScreenCallback('main_menu')))
        self.addComponent(WheelComponent(_wheelRects['fr'], _uiFactory, wheelImage, partial(getWheelAngleAndStatus, 'fr'), True))
        self.addComponent(WheelComponent(_wheelRects['fl'], _uiFactory, wheelImage, partial(getWheelAngleAndStatus, 'fl'), True))
        self.addComponent(WheelComponent(_wheelRects['br'], _uiFactory, wheelImage, partial(getWheelAngleAndStatus, 'br'), True))
        self.addComponent(WheelComponent(_wheelRects['bl'], _uiFactory, wheelImage, partial(getWheelAngleAndStatus, 'bl'), True))
        self.addComponent(WheelStatusComponent(Rect(5, 38, 152, 32), _uiFactory, wheelOdoImage, partial(getWheelOdoAndStatus, 'fl')))
        self.addComponent(WheelStatusComponent(Rect(163, 38, 152, 32), _uiFactory, wheelOdoImage, partial(getWheelOdoAndStatus, 'fr')))
        self.addComponent(WheelStatusComponent(Rect(5, 74, 152, 32), _uiFactory, wheelOdoImage, partial(getWheelOdoAndStatus, 'bl')))
        self.addComponent(WheelStatusComponent(Rect(163, 74, 152, 32), _uiFactory, wheelOdoImage, partial(getWheelOdoAndStatus, 'br')))
        self.redefineRect(rect)

    def redefineRect(self, rect):
        super(WheelsScreen, self).redefineRect(rect)
        self.components[0].redefineRect(Rect(rect.x + 10, rect.bottom - 50, 90, 40))
        self.components[1].redefineRect(Rect(rect.right - 100, rect.bottom - 50, 90, 40))
        self.components[2].redefineRect(Rect(_wheelRects['fr'].move(rect.x, rect.y)))
        self.components[3].redefineRect(Rect(_wheelRects['fl'].move(rect.x, rect.y)))
        self.components[4].redefineRect(Rect(_wheelRects['br'].move(rect.x, rect.y)))
        self.components[5].redefineRect(Rect(_wheelRects['bl'].move(rect.x, rect.y)))
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
    def __init__(self, rect, backButtonClick):
        super(MenuScreen, self).__init__(rect)
        self.menu_items = []
        self.addComponent(_uiFactory.text_button(Rect(50, 430, 220, 40), "BACK", backButtonClick))

    def addMenuItem(self, label, callback=None):
        if isinstance(label, str):
            component = _uiFactory.text_button(Rect(50, 60, 220, 40), label, callback)
        elif isinstance(label, gccui.Label):
            component = _uiFactory.button(Rect(50, 60, 220, 40), label, callback)
        else:
            component = label

        self.menu_items.append(component)
        self.addComponent(component)

    def redefineRect(self, rect):
        super(MenuScreen, self).redefineRect(rect)
        self.components[0].redefineRect(Rect(rect.x + 50, rect.bottom - 50, 220, 40))
        y = 60
        for item in self.menu_items:
            item.redefineRect(Rect(rect.x + 50, rect.y + y, 220, 40))
            y += 50


class MainMenuScreen(MenuScreen):
    def __init__(self, rect):
        super(MainMenuScreen, self).__init__(rect, self.backToMainScreenButtonClick)
        self.addMenuItem("WHEELS", partial(self.selectScreenButtonClick, 'wheels'))
        self.addMenuItem("RADAR", partial(self.selectScreenButtonClick, 'radar'))
        self.addMenuItem("STATUS", partial(self.selectScreenButtonClick, 'system_status'))
        self.addMenuItem("CALIBRATION", partial(self.selectScreenButtonClick, 'calibration_menu'))
        self.addMenuItem("SYSTEM", partial(self.selectScreenButtonClick, 'prefernces'))
        self.shutdown_button = _uiFactory.text_button(Rect(50, 380, 220, 40), "SHUTDOWN", self.selectScreenCallback('shutdown_confirmation'), hint=gccui.UI_HINT.WARNING)
        self.addComponent(self.shutdown_button)
        self.redefineRect(rect)

    def redefineRect(self, rect):
        super(MainMenuScreen, self).redefineRect(rect)
        self.shutdown_button.redefineRect(Rect(rect.x + 50, rect.bottom - 100, 220, 40))


class CalibrationMenuScreen(MenuScreen):
    def __init__(self, rect):
        super(CalibrationMenuScreen, self).__init__(rect, self.selectScreenCallback('main_menu'))
        self.addMenuItem("CAL WHEELS", self.selectScreenCallback('calibrate_wheel'))
        self.addMenuItem("CAL PID", self.selectScreenCallback('calibratePID'))
        self.redefineRect(rect)


class SystemMenuScreen(MenuScreen):
    def __init__(self, rect):
        super(SystemMenuScreen, self).__init__(rect, self.selectScreenCallback('main_menu'))
        self.addMenuItem("WHEELS", self.selectScreenCallback('wheels'))
        self.redefineRect(rect)


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
        pyroslib.publish("screen/say", "Shutdown, initiated, , ,  Waiting for satellite pies to stop.")


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
        return CalibrateWheelScreen.RectangleDecoration(pygame.color.THECOLORS['grey24'])

    @staticmethod
    def over_deco():
        return CalibrateWheelScreen.RectangleDecoration(pygame.color.THECOLORS['grey64'])

    def createWheelButton(self, wheel_name):
        return gccui.Button(_wheelRects[wheel_name],
                            partial(self.selectWheelButtonClick, wheel_name),
                            label=WheelComponent(_wheelRects[wheel_name], _uiFactory, self.wheel_image, partial(getWheelAngleAndStatus, wheel_name), False),
                            background_decoration=self.back_deco(),
                            mouse_over_decoration=self.over_deco())

    def __init__(self, rect):
        super(CalibrateWheelScreen, self).__init__(rect)
        self.wheel_image = pygame.image.load("graphics/wheel.png")
        self.wheel_name = ''
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
        self.select.addComponent(_uiFactory.text_button(Rect(220, 430, 90, 40), "CANCEL", self.selectScreenCallback('calibration_menu')))
        self.select.addComponent(self.createWheelButton('fr'))
        self.select.addComponent(self.createWheelButton('fl'))
        self.select.addComponent(self.createWheelButton('br'))
        self.select.addComponent(self.createWheelButton('bl'))

        self.wheel_name_label = _uiFactory.label(Rect(10, 50, 310, 20), "", h_alignment=gccui.ALIGNMENT.CENTER)
        self.calibrate.addComponent(self.wheel_name_label)
        self.calibrate.addComponent(_uiFactory.text_button(Rect(10, 430, 90, 40), "STOP", stopAllButtonClick))
        self.calibrate.addComponent(_uiFactory.text_button(Rect(120, 430, 90, 40), "SAVE", self.saveCalibrationWheelButtonClick))
        self.calibrate.addComponent(_uiFactory.text_button(Rect(220, 430, 90, 40), "CANCEL", self.selectScreenCallback('calibration_menu')))
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

        self.wheel = WheelComponent(_wheelRects['middle'], _uiFactory, self.wheel_image, self.getWheelAngleAndStatus, True)
        self.calibrate.addComponent(self.wheel)

        self.loading.addComponent(_uiFactory.text_button(Rect(10, 430, 90, 40), "STOP", stopAllButtonClick))
        self.loading.addComponent(_uiFactory.text_button(Rect(220, 430, 90, 40), "CANCEL", self.selectScreenCallback('calibration_menu')))
        self.loading.addComponent(_uiFactory.label(self.rect, "Loading calibration", h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE))

        self.selected_wheel_name = None
        self.redefineRect(rect)

    def redefineRect(self, rect):
        super(CalibrateWheelScreen, self).redefineRect(rect)
        self.card.redefineRect(rect)
        self.select.components[0].redefineRect(Rect(rect.x + 10, rect.bottom - 50, 90, 40))
        self.select.components[1].redefineRect(Rect(rect.right - 100, rect.bottom - 50, 90, 40))
        self.select.components[2].redefineRect(_wheelRects['fr'].move(rect.x, rect.y))
        self.select.components[3].redefineRect(_wheelRects['fl'].move(rect.x, rect.y))
        self.select.components[4].redefineRect(_wheelRects['br'].move(rect.x, rect.y))
        self.select.components[5].redefineRect(_wheelRects['bl'].move(rect.x, rect.y))

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
        self.calibrate.components[11].redefineRect(_wheelRects['middle'].move(rect.x, rect.y))

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
        self.wheel_name = selected_wheel_name
        self._updateToggleButton(self.degToggleButton, 'A', _wheelsMap[selected_wheel_name]['cal']['deg']['dir'])
        self._updateToggleButton(self.steerToggleButton, 'S', _wheelsMap[selected_wheel_name]['cal']['steer']['dir'])
        self._updateToggleButton(self.speedToggleButton, 'D', _wheelsMap[selected_wheel_name]['cal']['speed']['dir'])
        self.wheel_name_label.setText("Wheel " + selected_wheel_name.upper())

    def draw(self, surface):
        super(CalibrateWheelScreen, self).draw(surface)
        if self.card.selectedCardComponent == self.loading and hasCalibrationLoaded():
            self.card.selectCard('calibrate')

    @staticmethod
    def _updateToggleButton(toggleButton, kind, direction):
        toggleButton.getLabel().setText(kind + ": <---" if direction < 0 else kind + ": --->")

    def degToggleButtonClick(self, button, pos):
        wheel = _wheelsMap[self.selected_wheel_name]
        direction = _wheelsMap[self.selected_wheel_name]['cal']['deg']['dir']
        direction = -direction
        _wheelsMap[self.selected_wheel_name]['cal']['deg']['dir'] = direction
        print("Old value " + str(-direction) + ", new value " + str(direction))
        pyroslib.publish("storage/write/wheels/cal/" + self.selected_wheel_name + "/deg/dir", str(direction))
        self._updateToggleButton(self.degToggleButton, 'A', direction)

    def steerToggleButtonClick(self, button, pos):
        wheel = _wheelsMap[self.selected_wheel_name]
        direction = _wheelsMap[self.selected_wheel_name]['cal']['steer']['dir']
        direction = -direction
        _wheelsMap[self.selected_wheel_name]['cal']['steer']['dir'] = direction
        print("Old value " + str(-direction) + ", new value " + str(direction))
        pyroslib.publish("storage/write/wheels/cal/" + self.selected_wheel_name + "/steer/dir", str(direction))
        self._updateToggleButton(self.steerToggleButton, 'S', direction)

    def speedToggleButtonClick(self, button, pos):
        wheel = _wheelsMap[self.selected_wheel_name]
        direction = _wheelsMap[self.selected_wheel_name]['cal']['speed']['dir']
        direction = -direction
        _wheelsMap[self.selected_wheel_name]['cal']['speed']['dir'] = direction
        print("Old value " + str(-direction) + ", new value " + str(direction))
        pyroslib.publish("storage/write/wheels/cal/" + self.selected_wheel_name + "/speed/dir", str(direction))
        self._updateToggleButton(self.speedToggleButton, 'D', direction)

    def saveCalibrationWheelButtonClick(self, button, pos):
        wheel = _wheelsMap[self.selected_wheel_name]
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
        wheel = _wheelsMap[self.selected_wheel_name]
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

    def getWheelAngleAndStatus(self):
        wheel = _wheelsMap[self.wheel_name]

        status = wheel['deg_status'] | wheel['speed_status']
        angle = wheel['angle']

        return angle, status


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
        value = _wheelsMap['pid'][self.name]

        s = "{0:.2f}".format(value)
        i = s.index('.')
        left = s[0:i + 1]
        right = s[i + 1:]
        self.left.setText(left)
        self.right.setText(right)

        super(PIDUIComponent, self).draw(surace)

    def onClickPlus1(self, button, pos):
        pid = _wheelsMap['pid']
        value = pid[self.name]
        value += 1.0
        pid[self.name] = value

    def onClickMinus1(self, button, pos):
        pid = _wheelsMap['pid']
        value = pid[self.name]
        value -= 1.0
        pid[self.name] = value

    def onClickPlus01(self, button, pos):
        pid = _wheelsMap['pid']
        value = pid[self.name]
        value += 0.1
        pid[self.name] = value

    def onClickMinus01(self, button, pos):
        pid = _wheelsMap['pid']
        value = pid[self.name]
        value -= 0.1
        pid[self.name] = value

    def onClickPlus001(self, button, pos):
        pid = _wheelsMap['pid']
        value = pid[self.name]
        value += 0.01
        pid[self.name] = value

    def onClickMinus001(self, button, pos):
        pid = _wheelsMap['pid']
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
        self.calibrate.addComponent(_uiFactory.text_button(Rect(220, 430, 90, 40), "BACK", self.selectScreenCallback('calibration_menu')))
        self.calibrate.addComponent(PIDUIComponent(Rect(10, 72, 300, 50), 'p', 'p'))
        self.calibrate.addComponent(PIDUIComponent(Rect(10, 122, 300, 50), 'i', 'i'))
        self.calibrate.addComponent(PIDUIComponent(Rect(10, 172, 300, 50), 'd', 'd'))
        self.calibrate.addComponent(PIDUIComponent(Rect(10, 222, 300, 50), 'g', 'g'))
        self.calibrate.addComponent(PIDUIComponent(Rect(10, 272, 300, 50), 'deadband', 'db'))

        self.loading.addComponent(_uiFactory.label(self.rect, "Loading calibration", h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE))
        self.loading.addComponent(_uiFactory.text_button(Rect(10, 430, 90, 40), "STOP", stopAllButtonClick))
        self.loading.addComponent(_uiFactory.text_button(Rect(220, 430, 90, 40), "CANCEL", self.selectScreenCallback('calibration_menu')))

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
        pyroslib.publish("storage/write/wheels/cal/pid/p", str(_wheelsMap['pid']['p']))
        pyroslib.publish("storage/write/wheels/cal/pid/i", str(_wheelsMap['pid']['i']))
        pyroslib.publish("storage/write/wheels/cal/pid/d", str(_wheelsMap['pid']['d']))
        pyroslib.publish("storage/write/wheels/cal/pid/g", str(_wheelsMap['pid']['g']))
        pyroslib.publish("storage/write/wheels/cal/pid/deadband", str(_wheelsMap['pid']['deadband']))

        # returnToStatusButtonClick(button, pos)


class RadarScreen(ScreenComponent):
    def __init__(self, rect, uiFactory):
        super(RadarScreen, self).__init__(rect)
        self.uiFactory = uiFactory
        self.addComponent(_uiFactory.text_button(Rect(10, 430, 90, 40), "STOP", stopAllButtonClick))
        self.addComponent(_uiFactory.text_button(Rect(220, 430, 90, 40), "BACK", self.selectScreenCallback('main_menu')))
        self.addComponent(Radar(Rect(0, 50, 300, 300), self.uiFactory, getRadar, 1300))

    def redefineRect(self, rect):
        super(RadarScreen, self).redefineRect(rect)
        self.components[0].redefineRect(Rect(rect.x, rect.bottom - 50, 90, 40))
        self.components[1].redefineRect(Rect(rect.right - 100, rect.bottom - 50, 90, 40))

        self.components[2].redefineRect(Rect(rect.x + 10, rect.y + 70, 300, 300))

    def enter(self):
        super(RadarScreen, self).enter()
        pyroslib.subscribe("sensor/distance", handleDistances)
        pyroslib.publish("sensor/distance/resume", "")

    def leave(self):
        super(RadarScreen, self).leave()
        pyroslib.unsubscribe("distance/deg")
        pyroslib.publish("sensor/distance/pause", "")


class SystemStatusScreen(ScreenComponent):
    def __init__(self, rect):
        super(SystemStatusScreen, self).__init__(rect)
        self.addComponent(_uiFactory.text_button(Rect(10, 430, 90, 40), "STOP", stopAllButtonClick))
        self.addComponent(_uiFactory.text_button(Rect(10, 430, 900, 40), "SELECT", self.startSelectingGraph))
        self.addComponent(_uiFactory.text_button(Rect(220, 430, 90, 40), "BACK", self.selectScreenCallback('main_menu')))

        self.temperature_component = TemperatureComponent(Rect(256, 30, 64, 200), _uiFactory)
        self.cpu_component = CPUComponent(Rect(0, 30, 64, 200))
        self.addComponent(self.temperature_component)
        self.addComponent(self.cpu_component)

        self.table = [[None, None, None], [None, None, None], [None, None, None], [None, None, None]]
        self.table[0][1] = _uiFactory.label(None, "mAh", colour=pygame.color.THECOLORS['gray'], font=_smallFont, h_alignment=gccui.ALIGNMENT.RIGHT, v_alignment=gccui.ALIGNMENT.TOP)

        self.table[1][0] = _uiFactory.label(None, "Wheels", colour=pygame.color.THECOLORS['gray'], font=_smallFont, h_alignment=gccui.ALIGNMENT.LEFT, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.table[2][0] = _uiFactory.label(None, "RPis", colour=pygame.color.THECOLORS['gray'], font=_smallFont, h_alignment=gccui.ALIGNMENT.LEFT, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.table[3][0] = _uiFactory.label(None, "Total:", colour=pygame.color.THECOLORS['gray'], font=_smallFont, h_alignment=gccui.ALIGNMENT.LEFT, v_alignment=gccui.ALIGNMENT.MIDDLE)

        self.table[1][1] = _uiFactory.label(None, "-", colour=pygame.color.THECOLORS['white'], font=_font, h_alignment=gccui.ALIGNMENT.RIGHT, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.table[2][1] = _uiFactory.label(None, "-", colour=pygame.color.THECOLORS['white'], font=_font, h_alignment=gccui.ALIGNMENT.RIGHT, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.table[3][1] = _uiFactory.label(None, "-", colour=pygame.color.THECOLORS['white'], font=_font, h_alignment=gccui.ALIGNMENT.RIGHT, v_alignment=gccui.ALIGNMENT.MIDDLE)

        for row in self.table:
            for cell in row:
                if cell is not None:
                    self.addComponent(cell)

        self.stats_graph = StatsGraph(rect)
        self.addComponent(self.stats_graph)

        self.graph_label = _uiFactory.label(None, _stats_details['mAh']['name'], h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.addComponent(self.graph_label)
        self.graph_menu = _uiFactory.menu(Rect(0, 0, 150, 200), background_colour=pygame.color.THECOLORS['black'])
        for stats_id in _stats_details_order:
            details = _stats_details[stats_id]
            self.graph_menu.addMenuItem(details['name'], partial(self.selectGraph, stats_id), height=40)
        self.addComponent(self.graph_menu)

        self.selectGraph('mAh', None, None)

        self.redefineRect(rect)

    def redefineRect(self, rect):
        # super(SystemStatusScreen, self).redefineRect(rect)
        self.rect = rect
        self.components[0].redefineRect(Rect(rect.x + 10, rect.bottom - 50, 90, 40))
        self.components[1].redefineRect(Rect(rect.x + 115, rect.bottom - 50, 90, 40))
        self.components[2].redefineRect(Rect(rect.right - 100, rect.bottom - 50, 90, 40))
        self.graph_menu.redefineRect(Rect(rect.x + 85, rect.bottom - 60 - self.graph_menu.size()[1], self.graph_menu.size()[0], self.graph_menu.size()[1]))
        self.temperature_component.redefineRect(Rect(rect.right - 64, rect.y + 30, 64, 200))
        self.cpu_component.redefineRect(Rect(rect.x, rect.y + 30, 64, 195))
        self.graph_label.redefineRect(Rect(rect.x + 10, rect.bottom - 265, rect.width - 20, 30))
        self.stats_graph.redefineRect(Rect(rect.x + 10, rect.bottom - 235, rect.width - 20, 180))
        for r in range(0, 4):
            for c in range(0, 2):
                if r != 0 or c != 0:
                    cell = self.table[r][c]
                    cell.redefineRect(Rect(rect.x + 64 * c + 100, rect.y + 30 * r + 80, 50, 30))

    def setTemperatureStatus(self, status):
        self.temperature_component.setTemperatureStatus(status)

    def setTemperature(self, temp):
        self.temperature_component.setTemperature(temp)

    def setCPULoad(self, cpu_load):
        self.cpu_component.setCPULoad(cpu_load)

    def updateCurrent(self, _stats):
        def updateLabel(row, stat_name):
            stat = _stats[stat_name]
            last_value = stat.lastValue()
            total_label = row[1]
            if last_value is None:
                total_label.setText("-")
            else:
                total_label.setText(str(int(last_value)))

        updateLabel(self.table[1], 'wtmAh')
        updateLabel(self.table[2], 'rpimAh')
        updateLabel(self.table[3], 'mAh')

    def draw(self, surface):
        super(SystemStatusScreen, self).draw(surface)

    def enter(self):
        super(SystemStatusScreen, self).enter()

    def leave(self):
        super(SystemStatusScreen, self).leave()

    def startSelectingGraph(self, button, pos):
        self.graph_menu.show()

    def selectGraph(self, stats_id, button, pos):
        print("Selecting graph " + str(stats_id))
        stats_details = _stats_details[stats_id]
        self.stats_graph.setStats(_stats[stats_id])
        self.stats_graph.setUnits(stats_details['units'])
        self.stats_graph.setMaxValue(stats_details['max'])
        self.graph_menu.hide()
        self.graph_label.setText(stats_details['name'])
        if 'warning' in stats_details:
            self.stats_graph.setWarningValue(stats_details['warning'])
        else:
            self.stats_graph.setWarningValue(-1)
        if 'critical' in stats_details:
            self.stats_graph.setCriticalValue(stats_details['critical'])
        else:
            self.stats_graph.setCriticalValue(-1)


def init(uiFactory, uiAdapter, font, smallFont):
    global _uiFactory, _uiAdapter, screensComponent, topComponent, statusBarComponent, systemStatusScreen, _font, _smallFont
    _uiFactory = uiFactory

    roverscreencomponents._uiFactory = uiFactory

    _uiAdapter = uiAdapter
    _font = font
    _smallFont = smallFont

    pyroslib.subscribe("screen/image", handleScreenImage)
    pyroslib.subscribe("screen/sound", handleScreenSound)
    pyroslib.subscribe("storage/write/wheels/cal/#", handleStorageWrite)
    pyroslib.subscribe("wheel/feedback/status", handleWheelsStatus)
    pyroslib.subscribe("joystick/status", handleJoystickStatus)
    pyroslib.subscribe("power/uptime", handleUptimeStatus)
    pyroslib.subscribe("power/current", handleCurrentStatus)
    pyroslib.subscribe("power/cpu", handleCPUStatus)
    pyroslib.subscribe("shutdown/announce", handleShutdown)

    initGui()

    screen_rect = _uiAdapter.getScreen().get_rect()

    topComponent = gccui.Collection(screen_rect)
    statusBarComponent = StatusBarComponent(Rect(0, 0, screen_rect.width, 20))
    topComponent.addComponent(statusBarComponent)

    systemStatusScreen = SystemStatusScreen(screen_rect)
    screensComponent = gccui.CardsCollection(screen_rect)
    screensComponent.addCard('main', MainScreen(screen_rect))
    screensComponent.addCard('main_menu', MainMenuScreen(screen_rect))
    screensComponent.addCard('system_status', systemStatusScreen)
    screensComponent.addCard('wheels', WheelsScreen(screen_rect))
    screensComponent.addCard('radar', RadarScreen(screen_rect, uiFactory))
    screensComponent.addCard('calibration_menu', CalibrationMenuScreen(screen_rect))
    screensComponent.addCard('calibrate_wheel', CalibrateWheelScreen(screen_rect))
    screensComponent.addCard('calibratePID', CalibratePIDScreen(screen_rect))
    screensComponent.addCard('system_menu', SystemMenuScreen(screen_rect))
    screensComponent.addCard('shutdown', ShutdownScreen(screen_rect))
    screensComponent.addCard('shutdown_confirmation', ShutdownConfirmationScreen(screen_rect))
    topComponent.addComponent(screensComponent)

    main = screensComponent.selectCard('main')
    main.enter()
    setMainScreenImage("gcc-portrait.png")

    uiAdapter.setTopComponent(topComponent)
