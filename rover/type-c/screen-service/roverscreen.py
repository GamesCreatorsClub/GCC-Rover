#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import math
import pygame
import pyroslib
import gccui
from functools import partial


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
wheelGreenImage = None
wheelOrangeImage = None
wheelRedImage = None
wheelRects = {'fl': None, 'fr': None, 'bl': None, 'br': None}

received = False

distances = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

angle = 0.0

_uiFactory = None
_uiAdapter = None
_font = None
_smallFont = None
screensComponent = None
_slaves_shutdown = False


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
    pyroslib.publish("wheel/fr/deg", "-")
    pyroslib.publish("wheel/fl/deg", "-")
    pyroslib.publish("wheel/br/deg", "-")
    pyroslib.publish("wheel/bl/deg", "-")


def initGui():
    global wheelImage, wheelGreenImage, wheelOrangeImage, wheelRedImage

    screen_rect = _uiAdapter.getScreen().get_rect()

    wheelImage = pygame.image.load("wheel.png")

    wheelImageAlpha = wheelImage.copy()
    wheelImageAlpha.fill((0, 0, 0, 255), None, pygame.BLEND_RGBA_MULT)

    wheelGreenImage = wheelImageAlpha.copy()
    wheelGreenImage.fill((0, 255, 0, 0), None, pygame.BLEND_RGBA_ADD)

    wheelOrangeImage = wheelImageAlpha.copy()
    wheelOrangeImage.fill((255, 220, 0, 0), None, pygame.BLEND_RGBA_ADD)

    wheelRedImage = wheelImageAlpha.copy()
    wheelRedImage.fill((255, 0, 0, 0), None, pygame.BLEND_RGBA_ADD)

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
        wheel['odo'] = int(odoStr)
        wheel['speed_status'] = int(statusStr)

    received = True
    # print("** wheel positions = " + message)

    values = message.split(",")
    updateWheel('fl', values, 1)
    updateWheel('fr', values, 3)
    updateWheel('bl', values, 5)
    updateWheel('br', values, 7)


def handleDistance(topic, message, groups):
    global received  # , angle

    values = message.split(",")
    for i in range(8):
        distances[i] = float(values[i + 1])
        if distances[i] < 0:
            distances[i] = 0


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


class Wheel(gccui.Collection):
    def __init__(self, rect, wheel_name, draw_angle):
        super(Wheel, self).__init__(rect)
        self.wheel_name = wheel_name
        self.draw_angle = draw_angle
        self.image = _uiFactory.image(rect, None, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.addComponent(self.image)
        self.angle_text = _uiFactory.label(self.rect,
                                          '',
                                          h_alignment=gccui.ALIGNMENT.CENTER,
                                          v_alignment=gccui.ALIGNMENT.MIDDLE,
                                          colour=pygame.color.THECOLORS['black'])
        self.odo_text = _uiFactory.label(self.rect,
                                        '',
                                        font=_smallFont,
                                        h_alignment=gccui.ALIGNMENT.CENTER,
                                        v_alignment=gccui.ALIGNMENT.MIDDLE,
                                        colour=pygame.color.THECOLORS['violet'])
        self.status_text = _uiFactory.label(self.rect,
                                           '',
                                           h_alignment=gccui.ALIGNMENT.CENTER,
                                           v_alignment=gccui.ALIGNMENT.MIDDLE,
                                           colour=pygame.color.THECOLORS['white'])

        self.addComponent(self.angle_text)
        self.addComponent(self.odo_text)
        self.addComponent(self.status_text)

        if not self.draw_angle:
            self.angle_text.setVisible(False)
            self.odo_text.setVisible(False)
            self.status_text.setVisible(False)

        self.redefineRect(self.rect)

    def redefineRect(self, rect):
        self.rect = rect
        self.image.redefineRect(rect)
        self.angle_text.redefineRect(pygame.Rect(rect.x, rect.centery - self.angle_text.font.get_height() // 2, rect.width, self.angle_text.font.get_height()))
        self.odo_text.redefineRect(pygame.Rect(rect.x, self.angle_text.rect.bottom, rect.width, self.odo_text.font.get_height()))
        self.status_text.redefineRect(pygame.Rect(rect.x, self.angle_text.rect.top - self.status_text.font.get_height(), rect.width, self.status_text.font.get_height()))

    @staticmethod
    def wheelStatusToString(_status):
        return " ".join([f for f in [("i2c_W" if _status & STATUS_ERROR_I2C_WRITE else ""),
                                     ("i2c_R" if _status & STATUS_ERROR_I2C_READ else ""),
                                     ("O" if _status & STATUS_ERROR_MOTOR_OVERHEAT else ""),
                                     ("MH" if _status & STATUS_ERROR_MAGNET_HIGH else ""),
                                     ("ML" if _status & STATUS_ERROR_MAGNET_LOW else ""),
                                     ("MND" if _status & STATUS_ERROR_MAGNET_NOT_DETECTED else ""),
                                     ("RX" if _status & STATUS_ERROR_RX_FAILED else ""),
                                     ("TX" if _status & STATUS_ERROR_TX_FAILED else "")] if f != ""])

    def draw(self, surface):
        wheel = wheelsMap[self.wheel_name]

        selectedWheelImage = wheelImage
        status = wheel['deg_status'] | wheel['speed_status']
        if status == 32:
            selectedWheelImage = wheelGreenImage
        elif not status & 1 and not status & 2 and status & 32 and (status & 8 or status & 16):
            selectedWheelImage = wheelOrangeImage
        else:
            selectedWheelImage = wheelRedImage

        _angle = float(wheel['angle'])

        rotatedWheelImage = pygame.transform.rotate(selectedWheelImage, -_angle)
        rotatedWheelImage.get_rect(center=self.rect.center)
        self.image._surface = rotatedWheelImage

        if self.draw_angle:
            self.angle_text.setText(str(wheel['angle']))
            self.odo_text.setText(str(wheel['odo']))

            if status != 32:
                # font.set_bold(True)
                self.status_text.setText(self.wheelStatusToString(status))
                # font.set_bold(False)
            else:
                self.status_text.setText('')

        super(Wheel, self).draw(surface)


class Radar(gccui.Component):
    def __init__(self, rect, limit_distance):
        super(Radar, self).__init__(rect)
        self.limit_distance = limit_distance

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

        pygame.draw.arc(_uiAdapter.getScreen(), (255, 0, 255), self.rect.inflate(limit(distances[0]), limit(distances[0])), pi8 * 3, pi8 * 5)  # 0º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(distances[1]), limit(distances[1])), pi8 * 1, pi8 * 3)  # 45º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(distances[2]), limit(distances[2])), pi8 * 15, pi8 * 1)  # 90º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(distances[3]), limit(distances[3])), pi8 * 13, pi8 * 15)  # 135º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(distances[4]), limit(distances[4])), pi8 * 11, pi8 * 13)  # 180º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(distances[5]), limit(distances[5])), pi8 * 9, pi8 * 11)  # 225º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(distances[6]), limit(distances[6])), pi8 * 7, pi8 * 9)  # 270º
        pygame.draw.arc(_uiAdapter.getScreen(), WHITE, self.rect.inflate(limit(distances[7]), limit(distances[7])), pi8 * 5, pi8 * 7)  # 315º


def returnToStatusButtonClick(button, pos):
    screensComponent.selectCard('main')


class ScreenComponent(gccui.Collection):
    def __init__(self):
        super(ScreenComponent, self).__init__(_uiAdapter.getScreen().get_rect())

    def backToMainScreen(self):
        self.selectScreen('main')

    def backToMainScreenButtonClick(self, button, pos):
        self.selectScreen('main')

    @staticmethod
    def selectScreen(name):
        screensComponent.selectCard(name)

    @staticmethod
    def selectScreenButtonClick(name, button, pos):
        screensComponent.selectCard(name)


class StatusScreen(ScreenComponent):
    def __init__(self):
        super(StatusScreen, self).__init__()

        self.addComponent(_uiFactory.text_button(pygame.Rect(10, 430, 80, 40), "STOP", stopAllButtonClick))
        self.addComponent(_uiFactory.text_button(pygame.Rect(230, 430, 80, 40), "MENU", partial(self.selectScreenButtonClick, 'menu')))
        self.addComponent(Wheel(wheelRects['fr'], 'fr', True))
        self.addComponent(Wheel(wheelRects['fl'], 'fl', True))
        self.addComponent(Wheel(wheelRects['br'], 'br', True))
        self.addComponent(Wheel(wheelRects['bl'], 'bl', True))


class MenuScreen(ScreenComponent):
    def __init__(self):
        super(MenuScreen, self).__init__()

        self.addComponent(_uiFactory.text_button(pygame.Rect(50, 60, 220, 40), "CAL", partial(self.selectScreenButtonClick, 'calibrateWheel')))
        self.addComponent(_uiFactory.text_button(pygame.Rect(50, 110, 220, 40), "PID", partial(self.selectScreenButtonClick, 'calibratePID')))
        self.addComponent(_uiFactory.text_button(pygame.Rect(50, 160, 220, 40), "RADAR", partial(self.selectScreenButtonClick, 'radar')))
        self.addComponent(_uiFactory.text_button(pygame.Rect(50, 380, 220, 40), "SHUTDOWN", partial(self.selectScreenButtonClick, 'shutdownConfirmation')))
        self.addComponent(_uiFactory.text_button(pygame.Rect(50, 430, 220, 40), "BACK", self.backToMainScreenButtonClick))


class ShutdownConfirmationScreen(ScreenComponent):
    def __init__(self):
        super(ShutdownConfirmationScreen, self).__init__()

        self.addComponent(_uiFactory.label(pygame.Rect(50, 60, 220, 40), "Are you sure to shutdown?"))
        self.addComponent(_uiFactory.text_button(pygame.Rect(50, 110, 220, 40), "SHUTDOWN", self.startShutdownButtonClick))
        self.addComponent(_uiFactory.text_button(pygame.Rect(50, 430, 220, 40), "BACK", self.backToMainScreenButtonClick))

    @staticmethod
    def startShutdownButtonClick(button, pos):
        pyroslib.publish("system/shutdown", "secret_message_now")


class ShutdownScreen(ScreenComponent):
    def __init__(self):
        super(ShutdownScreen, self).__init__()

        self.addComponent(_uiFactory.label(pygame.Rect(50, 160, 220, 40), "Shutdown in progress..."))
        self.slaves_label = _uiFactory.label(pygame.Rect(50, 200, 220, 40), "Slaves have shutdown")
        self.addComponent(self.slaves_label)

    def draw(self, surface):
        self.slaves_label.setVisible(_slaves_shutdown)
        super(ShutdownScreen, self).draw(surface)


class CalibrateWheelScreen(ScreenComponent):

    def __init__(self):
        super(CalibrateWheelScreen, self).__init__()
        self.card = gccui.CardsCollection(self.rect)
        self.addComponent(self.card)
        self.select = gccui.Collection(self.rect)
        self.loading = gccui.Collection(self.rect)
        self.calibrate = gccui.Collection(self.rect)
        self.card.addCard('select', self.select)
        self.card.addCard('loading', self.loading)
        self.card.addCard('calibrate', self.calibrate)
        self.card.selectCard('select')

        self.select.addComponent(_uiFactory.text_button(pygame.Rect(10, 430, 80, 40), "STOP", stopAllButtonClick))
        self.select.addComponent(_uiFactory.text_button(pygame.Rect(230, 430, 80, 40), "CANCEL", self.backToMainScreenButtonClick))
        self.select.addComponent(_uiFactory.button(wheelRects['fr'], partial(self.selectWheelButtonClick, 'fr')))
        self.select.addComponent(_uiFactory.button(wheelRects['fl'], partial(self.selectWheelButtonClick, 'fl')))
        self.select.addComponent(_uiFactory.button(wheelRects['br'], partial(self.selectWheelButtonClick, 'br')))
        self.select.addComponent(_uiFactory.button(wheelRects['bl'], partial(self.selectWheelButtonClick, 'bl')))
        self.select.addComponent(Wheel(wheelRects['fr'], 'fr', False))
        self.select.addComponent(Wheel(wheelRects['fl'], 'fl', False))
        self.select.addComponent(Wheel(wheelRects['br'], 'br', False))
        self.select.addComponent(Wheel(wheelRects['bl'], 'bl', False))

        self.calibrate.addComponent(_uiFactory.text_button(pygame.Rect(10, 430, 80, 40), "STOP", stopAllButtonClick))
        self.calibrate.addComponent(_uiFactory.text_button(pygame.Rect(140, 430, 80, 40), "SAVE", self.saveCalibrationWheelButtonClick))
        self.calibrate.addComponent(_uiFactory.text_button(pygame.Rect(230, 430, 80, 40), "CANCEL", self.backToMainScreenButtonClick))
        self.calibrate.addComponent(_uiFactory.text_button(pygame.Rect(8, 170, 80, 40), "<", partial(self.moveWheelClick, -1)))
        self.calibrate.addComponent(_uiFactory.text_button(pygame.Rect(8, 240, 80, 40), "<<", partial(self.moveWheelClick, -10)))
        self.calibrate.addComponent(_uiFactory.text_button(pygame.Rect(232, 170, 80, 40), ">", partial(self.moveWheelClick, 1)))
        self.calibrate.addComponent(_uiFactory.text_button(pygame.Rect(232, 240, 80, 40), ">>", partial(self.moveWheelClick, 10)))
        self.degToggleButton = _uiFactory.text_button(pygame.Rect(70, 330, 80, 40), "D: --->", self.degToggleButtonClick)
        self.steerToggleButton = _uiFactory.text_button(pygame.Rect(170, 330, 80, 40), "S: --->", self.steerToggleButtonClick)
        self.calibrate.addComponent(self.degToggleButton)
        self.calibrate.addComponent(self.steerToggleButton)

        self.wheel = Wheel(wheelRects['middle'], '', True)
        self.calibrate.addComponent(self.wheel)

        self.loading.addComponent(_uiFactory.text_button(pygame.Rect(10, 430, 80, 40), "STOP", stopAllButtonClick))
        self.loading.addComponent(_uiFactory.text_button(pygame.Rect(230, 430, 80, 40), "CANCEL", self.backToMainScreenButtonClick))
        self.loading.addComponent(_uiFactory.label(self.rect, "Loading calibration", h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE))

        self.selected_wheel_name = None

    def setVisible(self, visible):
        super(CalibrateWheelScreen, self).setVisible(visible)
        self.card.selectCard('select')
        pyroslib.publish("storage/read/wheels/cal", "")

    def setSelectedWheelName(self, selected_wheel_name):
        self.selected_wheel_name = selected_wheel_name
        self.wheel.wheel_name = selected_wheel_name
        self._updateToggleButton(self.degToggleButton, 'D', wheelsMap[selected_wheel_name]['cal']['deg']['dir'])
        self._updateToggleButton(self.steerToggleButton, 'S', wheelsMap[selected_wheel_name]['cal']['steer']['dir'])

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
        self._updateToggleButton(self.degToggleButton, 'D', direction)

    def steerToggleButtonClick(self, button, pos):
        wheel = wheelsMap[self.selected_wheel_name]
        direction = wheelsMap[self.selected_wheel_name]['cal']['steer']['dir']
        direction = -direction
        wheelsMap[self.selected_wheel_name]['cal']['steer']['dir'] = direction
        print("Old value " + str(-direction) + ", new value " + str(direction))
        pyroslib.publish("storage/write/wheels/cal/" + self.selected_wheel_name + "/steer/dir", str(direction))
        self._updateToggleButton(self.steerToggleButton, 'S', direction)

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
    def __init__(self, rect, name):
        super(PIDUIComponent, self).__init__(rect)
        self.name = name

        self.addComponent(_uiFactory.label(pygame.Rect(rect.x + 112, rect.y, 30, 50), name, v_alignment=gccui.ALIGNMENT.MIDDLE))

        self.left = _uiFactory.label(pygame.Rect(rect.x + 100, rect.y, 64, 50), '', h_alignment=gccui.ALIGNMENT.RIGHT, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.right = _uiFactory.label(pygame.Rect(rect.x + 164, rect.y, 30, 50), '', h_alignment=gccui.ALIGNMENT.LEFT, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.addComponent(self.left)
        self.addComponent(self.right)

        self.addComponent(_uiFactory.text_button(pygame.Rect(rect.x, rect.y, 30, 40), "<", self.onClickMinus1))
        self.addComponent(_uiFactory.text_button(pygame.Rect(rect.x + 34, rect.y, 30, 40), "<<", self.onClickMinus01))
        self.addComponent(_uiFactory.text_button(pygame.Rect(rect.x + 34 * 2, rect.y, 30, 40), "<<<", self.onClickMinus001))
        self.addComponent(_uiFactory.text_button(pygame.Rect(rect.right - 30 - 34 * 2, rect.y, 30, 40), ">>>", self.onClickPlus001))
        self.addComponent(_uiFactory.text_button(pygame.Rect(rect.right - 30 - 34, rect.y, 30, 40), ">>", self.onClickPlus01))
        self.addComponent(_uiFactory.text_button(pygame.Rect(rect.right - 30, rect.y, 30, 40), ">", self.onClickPlus1))

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
    def __init__(self):
        super(CalibratePIDScreen, self).__init__()

        self.card = gccui.CardsCollection(self.rect)
        self.addComponent(self.card)
        self.loading = gccui.Collection(self.rect)
        self.calibrate = gccui.Collection(self.rect)
        self.card.addCard('loading', self.loading)
        self.card.addCard('calibrate', self.calibrate)
        self.card.selectCard('loading')

        self.calibrate.addComponent(_uiFactory.text_button(pygame.Rect(10, 430, 80, 40), "STOP", stopAllButtonClick))
        self.calibrate.addComponent(_uiFactory.text_button(pygame.Rect(140, 430, 80, 40), "SAVE", self.saveCalibrationPIDButtonClick))
        self.calibrate.addComponent(_uiFactory.text_button(pygame.Rect(230, 430, 80, 40), "CANCEL", self.backToMainScreenButtonClick))
        self.calibrate.addComponent(PIDUIComponent(pygame.Rect(10, 72, 300, 50), 'p'))
        self.calibrate.addComponent(PIDUIComponent(pygame.Rect(10, 122, 300, 50), 'i'))
        self.calibrate.addComponent(PIDUIComponent(pygame.Rect(10, 172, 300, 50), 'd'))
        self.calibrate.addComponent(PIDUIComponent(pygame.Rect(10, 222, 300, 50), 'g'))
        self.calibrate.addComponent(PIDUIComponent(pygame.Rect(10, 272, 300, 50), 'd'))

        self.loading.addComponent(_uiFactory.label(self.rect, "Loading calibration", h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE))
        self.loading.addComponent(_uiFactory.text_button(pygame.Rect(10, 430, 80, 40), "STOP", stopAllButtonClick))
        self.loading.addComponent(_uiFactory.text_button(pygame.Rect(230, 430, 80, 40), "CANCEL", self.backToMainScreenButtonClick))

    def draw(self, surface):
        super(CalibratePIDScreen, self).draw(surface)
        if self.card.selectedCardComponent == self.loading and hasCalibrationLoaded():
            self.card.selectCard('calibrate')

    def setVisible(self, visible):
        super(CalibratePIDScreen, self).setVisible(visible)
        self.card.selectCard('loading')
        pyroslib.publish("storage/read/wheels/cal", "")

    @staticmethod
    def saveCalibrationPIDButtonClick(button, pos):
        pyroslib.publish("storage/write/wheels/cal/pid/p", str(wheelsMap['pid']['p']))
        pyroslib.publish("storage/write/wheels/cal/pid/i", str(wheelsMap['pid']['i']))
        pyroslib.publish("storage/write/wheels/cal/pid/d", str(wheelsMap['pid']['d']))
        pyroslib.publish("storage/write/wheels/cal/pid/g", str(wheelsMap['pid']['g']))
        pyroslib.publish("storage/write/wheels/cal/pid/deadband", str(wheelsMap['pid']['deadband']))

        returnToStatusButtonClick(button, pos)


class RadarScreen(ScreenComponent):
    def __init__(self):
        super(RadarScreen, self).__init__()
        self.addComponent(_uiFactory.text_button(pygame.Rect(10, 430, 80, 40), "STOP", stopAllButtonClick))
        self.addComponent(_uiFactory.text_button(pygame.Rect(230, 430, 80, 40), "BACK", self.backToMainScreenButtonClick))
        self.addComponent(Radar(pygame.Rect(50, 50, 220, 220), 1300))
        self.distance_labels = [
            _uiFactory.label(pygame.Rect(160, 40, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE),
            _uiFactory.label(pygame.Rect(260, 70, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE),
            _uiFactory.label(pygame.Rect(290, 160, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE),
            _uiFactory.label(pygame.Rect(260, 260, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE),
            _uiFactory.label(pygame.Rect(160, 290, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE),
            _uiFactory.label(pygame.Rect(70, 260, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE),
            _uiFactory.label(pygame.Rect(40, 160, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE),
            _uiFactory.label(pygame.Rect(70, 70, 0, 0), '', font=_smallFont, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE)
        ]
        for label in self.distance_labels:
            self.addComponent(label)

    def draw(self, surface):
        for i in range(len(distances)):
            self.distance_labels[i].setText(str(distances[i]))
        super(RadarScreen, self).draw(surface)


def init(uiFactory, uiAdapter, font, smallFont):
    global _uiFactory, _uiAdapter, screensComponent, _font, _smallFont
    _uiFactory = uiFactory
    _uiAdapter = uiAdapter
    _font = font
    _smallFont = smallFont

    pyroslib.subscribe("wheel/deg/status", handleWheelOrientations)
    pyroslib.subscribe("wheel/speed/status", handleWheelPositions)
    pyroslib.subscribe("distance/deg", handleDistance)
    pyroslib.subscribe("storage/write/wheels/cal/#", handleStorageWrite)
    pyroslib.subscribe("shutdown/announce", handleShutdown)

    initGui()

    screensComponent = gccui.CardsCollection(_uiAdapter.getScreen().get_rect())
    screensComponent.addCard('main', StatusScreen())
    screensComponent.addCard('menu', MenuScreen())
    screensComponent.addCard('calibrateWheel', CalibrateWheelScreen())
    screensComponent.addCard('calibratePID', CalibratePIDScreen())
    screensComponent.addCard('radar', RadarScreen())
    screensComponent.addCard('shutdown', ShutdownScreen())
    screensComponent.addCard('shutdownConfirmation', ShutdownConfirmationScreen())

    screensComponent.selectCard('main')

    uiAdapter.setTopComponent(screensComponent)
