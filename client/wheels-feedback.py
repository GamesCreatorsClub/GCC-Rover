#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import math
import sys
import pygame
import pyros
import pyros.gcc
import pyros.gccui
import pyros.pygamehelper

SCALE = 2
WHITE = (255, 255, 255)
RED = (255, 128, 0)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (128, 128, 128)
BLACK = (0, 0, 0)

OFF = 10
XOFF = 0
YOFF = 15

MODE_STATUS = 1
MODE_CALIBRATE_SELECT_WHEEL = 2
MODE_CALIBRATE_WHEEL = 3
MODE_CALIBRATE_PID = 4

mode = MODE_STATUS

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

screen = pyros.gccui.initAll((480, 320), True)
font = pyros.gccui.font
smallFont = pyros.gccui.smallFont

received = False

mousePos = (0, 0)
mouseDown = False
mousePreviousState = False
selectedButton = None
selectedWheel = None

mainButtons = []
selectWheelButtons = []
calibrateWheelButtons = []
calibratePIDButtons = []
calibrateCancelButton = []

angle = 0.0


def createTemplateWheel():
    return {
        'angle': 0,
        'deg_status': 0,
        'speed_status': 0,
        'odo': 0,
        'cal': {},
        'd1': -1.0,
        'd2': -1.0
    }


wheelsMap = {'fl': createTemplateWheel(), 'fr': createTemplateWheel(), 'bl': createTemplateWheel(), 'br': createTemplateWheel(), 'pid': {}}


def selectWheelButtonClick():
    global mode
    mode = MODE_CALIBRATE_SELECT_WHEEL
    pyros.publish("storage/read/wheels/cal", "")


def returnToStatusButtonClick():
    global mode
    mode = MODE_STATUS


def pidButtonClick():
    global mode
    mode = MODE_CALIBRATE_PID
    pyros.publish("storage/read/wheels/cal", "")


def startLoadingCalibration():
    global mode
    mode = MODE_CALIBRATE_WHEEL


def selectFRWheelButtonClick():
    global selectedWheel
    selectedWheel = 'fr'
    startLoadingCalibration()


def selectFLWheelButtonClick():
    global selectedWheel
    selectedWheel = 'fl'
    startLoadingCalibration()


def selectBRWheelButtonClick():
    global selectedWheel
    selectedWheel = 'br'
    startLoadingCalibration()


def selectBLWheelButtonClick():
    global selectedWheel
    selectedWheel = 'bl'
    startLoadingCalibration()


def moveWheel(deltaAngle):
    wheel = wheelsMap[str(selectedWheel)]
    if 'wanted' in wheel:
        wanted = wheel['wanted']
        wanted += deltaAngle
        if wanted < 0:
            wanted += 360
        if wanted >= 360:
            wanted -= 360
        wheel['wanted'] = wanted

        pyros.publish("wheel/" + str(selectedWheel) + "/deg", str(wanted))


def leftButtonClick():
    moveWheel(-1)


def leftMoreButtonClick():
    moveWheel(-10)


def rightButtonClick():
    moveWheel(1)


def rightMoreButtonClick():
    moveWheel(10)


def saveCalibrationWheelButtonClick():
    wheel = wheelsMap[str(selectedWheel)]
    calDeg = wheel['cal']['deg']['0']
    _angle = wheel['angle']
    value = _angle + calDeg
    if value < 0:
        value += 360

    if value >= 360:
        value -= 360

    wheel['wanted'] = 0

    print("Old value " + str(calDeg) + ", angle " + str(_angle) + ", new value " + str(value))

    pyros.publish("storage/write/wheels/cal/" + str(selectedWheel) + "/deg/0", str(value))
    pyros.publish("wheel/" + str(selectedWheel) + "/deg", str(0))
    returnToStatusButtonClick()


class PIDCallback:
    def __init__(self, name):
        self.name = name

    def onClickPlus1(self):
        pid = wheelsMap['pid']
        value = pid[self.name]
        value += 1.0
        pid[self.name] = value

    def onClickMinus1(self):
        pid = wheelsMap['pid']
        value = pid[self.name]
        value -= 1.0
        pid[self.name] = value

    def onClickPlus01(self):
        pid = wheelsMap['pid']
        value = pid[self.name]
        value += 0.1
        pid[self.name] = value

    def onClickMinus01(self):
        pid = wheelsMap['pid']
        value = pid[self.name]
        value -= 0.1
        pid[self.name] = value

    def onClickPlus001(self):
        pid = wheelsMap['pid']
        value = pid[self.name]
        value += 0.01
        pid[self.name] = value

    def onClickMinus001(self):
        pid = wheelsMap['pid']
        value = pid[self.name]
        value -= 0.01
        pid[self.name] = value


def saveCalibrationPIDButtonClick():
    pyros.publish("storage/write/wheels/cal/pid/p", str(wheelsMap['pid']['p']))
    pyros.publish("storage/write/wheels/cal/pid/i", str(wheelsMap['pid']['i']))
    pyros.publish("storage/write/wheels/cal/pid/d", str(wheelsMap['pid']['d']))
    pyros.publish("storage/write/wheels/cal/pid/g", str(wheelsMap['pid']['g']))
    pyros.publish("storage/write/wheels/cal/pid/deadband", str(wheelsMap['pid']['deadband']))

    returnToStatusButtonClick()


def directionDegToggleButtonClick():
    wheel = wheelsMap[str(selectedWheel)]
    _direction = wheelsMap[str(selectedWheel)]['cal']['deg']['dir']
    _direction = -_direction
    wheelsMap[str(selectedWheel)]['cal']['deg']['dir'] = _direction
    print("Old value " + str(-_direction) + ", new value " + str(_direction))
    pyros.publish("storage/write/wheels/cal/" + str(selectedWheel) + "/deg/dir", str(_direction))


def directionSteerToggleButtonClick():
    wheel = wheelsMap[str(selectedWheel)]
    _direction = wheelsMap[str(selectedWheel)]['cal']['steer']['dir']
    _direction = -_direction
    wheelsMap[str(selectedWheel)]['cal']['steer']['dir'] = _direction
    print("Old value " + str(-_direction) + ", new value " + str(_direction))
    pyros.publish("storage/write/wheels/cal/" + str(selectedWheel) + "/steer/dir", str(_direction))


def stopAllButtonClick():
    pyros.publish("wheel/fr/deg", "-")
    pyros.publish("wheel/fl/deg", "-")
    pyros.publish("wheel/br/deg", "-")
    pyros.publish("wheel/bl/deg", "-")


def initGui():
    global wheelImage, wheelGreenImage, wheelOrangeImage, wheelRedImage

    def drawSelected(button):
        rect = button['rect']
        text = button['text']
        pygame.draw.rect(screen, LIGHT_GRAY, rect)
        screen.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))
        pygame.draw.rect(screen, WHITE, rect, 1)

    def draw(button):
        rect = button['rect']
        text = button['text']
        pygame.draw.rect(screen, DARK_GRAY, rect)
        screen.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))
        pygame.draw.rect(screen, WHITE, rect, 1)

    def makeTextButton(rect, text, onClick):
        return {'rect': rect, 'onClick': onClick, 'drawSelected': drawSelected, 'draw': draw, 'text': font.render(text, 0, WHITE)}

    def makeBorderButton(rect, onClick):
        button = {'rect': rect, 'onClick': onClick}

        def _drawSelected(_button):
            _rect = _button['rect']
            pygame.draw.rect(screen, WHITE, _rect, 1)

        def _draw(_button):
            _rect = _button['rect']
            pygame.draw.rect(screen, WHITE, _rect, 1)

        button['drawSelected'] = _drawSelected
        button['draw'] = _draw
        return button

    def makeDirectionToggleButton(rect, text, calPath, onClick):
        button = {'rect': rect, 'onClick': onClick}

        def checkText(_button):
            _direction = wheelsMap[str(selectedWheel)]['cal'][calPath]['dir']
            if 'text' not in _button or _button['prevdir'] != _direction:
                _button['text'] = font.render(text + "<---" if _direction < 0 else text + "--->", 20, WHITE)
                _button['prevdir'] = _direction

        def drawToggleSelected(_button):
            checkText(_button)
            drawSelected(_button)

        def drawToggle(_button):
            checkText(_button)
            draw(_button)

        button['drawSelected'] = drawToggleSelected
        button['draw'] = drawToggle
        return button

    def makePIDButton(name, y):
        callback = PIDCallback(name)

        calibratePIDButtons.append(makeTextButton(pygame.Rect(92, y, 30, 40), "<", callback.onClickMinus1))
        calibratePIDButtons.append(makeTextButton(pygame.Rect(126, y, 30, 40), "<<", callback.onClickMinus01))
        calibratePIDButtons.append(makeTextButton(pygame.Rect(160, y, 30, 40), "<<<", callback.onClickMinus001))
        calibratePIDButtons.append(makeTextButton(pygame.Rect(290, y, 30, 40), ">>>", callback.onClickPlus001))
        calibratePIDButtons.append(makeTextButton(pygame.Rect(324, y, 30, 40), ">>", callback.onClickPlus01))
        calibratePIDButtons.append(makeTextButton(pygame.Rect(358, y, 30, 40), ">", callback.onClickPlus1))

    screen_rect = screen.get_rect()

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

    mainButtons.append(makeTextButton(pygame.Rect(392, 60, 80, 40), "CAL", selectWheelButtonClick))
    mainButtons.append(makeTextButton(pygame.Rect(392, 110, 80, 40), "PID", pidButtonClick))
    mainButtons.append(makeTextButton(pygame.Rect(392, 272, 80, 40), "STOP", stopAllButtonClick))

    selectWheelButtons.append(makeTextButton(pygame.Rect(392, 272, 80, 40), "CANCEL", returnToStatusButtonClick))
    selectWheelButtons.append(makeBorderButton(wheelRects['fr'], selectFRWheelButtonClick))
    selectWheelButtons.append(makeBorderButton(wheelRects['fl'], selectFLWheelButtonClick))
    selectWheelButtons.append(makeBorderButton(wheelRects['br'], selectBRWheelButtonClick))
    selectWheelButtons.append(makeBorderButton(wheelRects['bl'], selectBLWheelButtonClick))
    selectWheelButtons.append(makeTextButton(pygame.Rect(8, 272, 80, 40), "STOP", stopAllButtonClick))

    calibrateWheelButtons.append(makeTextButton(pygame.Rect(392, 222, 80, 40), "SAVE", saveCalibrationWheelButtonClick))
    calibrateWheelButtons.append(makeTextButton(pygame.Rect(392, 272, 80, 40), "CANCEL", returnToStatusButtonClick))
    calibrateWheelButtons.append(makeTextButton(pygame.Rect(8, 92, 80, 40), "<", leftButtonClick))
    calibrateWheelButtons.append(makeTextButton(pygame.Rect(8, 142, 80, 40), "<<", leftMoreButtonClick))
    calibrateWheelButtons.append(makeTextButton(pygame.Rect(392, 92, 80, 40), ">", rightButtonClick))
    calibrateWheelButtons.append(makeTextButton(pygame.Rect(392, 142, 80, 40), ">>", rightMoreButtonClick))
    calibrateWheelButtons.append(makeTextButton(pygame.Rect(8, 272, 80, 40), "STOP", stopAllButtonClick))

    calibratePIDButtons.append(makeTextButton(pygame.Rect(392, 222, 80, 40), "SAVE", saveCalibrationPIDButtonClick))
    calibratePIDButtons.append(makeTextButton(pygame.Rect(392, 272, 80, 40), "CANCEL", returnToStatusButtonClick))
    makePIDButton('p', 72)
    makePIDButton('i', 122)
    makePIDButton('d', 172)
    makePIDButton('g', 222)
    makePIDButton('deadband', 272)
    calibratePIDButtons.append(makeTextButton(pygame.Rect(8, 272, 80, 40), "STOP", stopAllButtonClick))

    calibrateWheelButtons.append(makeDirectionToggleButton(pygame.Rect(200, 222, 80, 40), "D: ", 'deg', directionDegToggleButtonClick))
    calibrateWheelButtons.append(makeDirectionToggleButton(pygame.Rect(200, 272, 80, 40), "S: ", 'steer', directionSteerToggleButtonClick))
    calibrateCancelButton.append(calibrateWheelButtons[0])


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


def handleWheelOrientations(topic, message, groups):
    global received  # , angle

    def updateWheel(wheelName, _values, index, distance_index):
        wheel = wheelsMap[wheelName]
        angleStr = _values[index]
        statusStr = _values[index + 1]
        wheel['deg_status'] = int(statusStr)
        if angleStr != '-':
            _angle = int(angleStr)
            wheel['angle'] = _angle
            if 'wanted' not in wheel or mode != MODE_CALIBRATE_WHEEL:
                wheel['wanted'] = _angle

        d1 = _values[distance_index]
        d2 = _values[distance_index + 1]
        wheel['d1'] = float(d1)
        wheel['d2'] = float(d2)

    received = True
    # print("** wheel positions = " + message)

    values = message.split(",")
    updateWheel('fl', values, 1, 9)
    updateWheel('fr', values, 3, 11)
    updateWheel('bl', values, 5, 13)
    updateWheel('br', values, 7, 15)


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


def processButtons(buttons):
    global selectedButton, mousePreviousState

    def findButton():
        for _button in buttons:
            if _button['rect'].collidepoint(mousePos):
                return _button

        return None

    if mouseDown:
        if not mousePreviousState:
            selectedButton = findButton()
    else:  # not mouseDown:
        if mousePreviousState and selectedButton is not None and selectedButton['rect'].collidepoint(mousePos):
            selectedButton['onClick']()
        selectedButton = None

    mousePreviousState = mouseDown

    for button in buttons:
        if button == selectedButton:
            button['drawSelected'](button)
        else:
            button['draw'](button)


def drawTextInCentre(text, colour, rect):
    text = font.render(str(text), 0, colour)
    screen.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))


def drawAngle(wheel, wheelRect):
    def wheelStatusToString(_status):
        return " ".join([f for f in [("i2c_W" if _status & STATUS_ERROR_I2C_WRITE else ""),
                                     ("i2c_R" if _status & STATUS_ERROR_I2C_READ else ""),
                                     ("O" if _status & STATUS_ERROR_MOTOR_OVERHEAT else ""),
                                     ("MH" if _status & STATUS_ERROR_MAGNET_HIGH else ""),
                                     ("ML" if _status & STATUS_ERROR_MAGNET_LOW else ""),
                                     ("MND" if _status & STATUS_ERROR_MAGNET_NOT_DETECTED else ""),
                                     ("RX" if _status & STATUS_ERROR_RX_FAILED else ""),
                                     ("TX" if _status & STATUS_ERROR_TX_FAILED else "")] if f != ""])

    status = wheel['deg_status'] | wheel['speed_status']
    angle_text = font.render(str(wheel['angle']), 0, BLACK)
    screen.blit(angle_text, (wheelRect.centerx - angle_text.get_width() // 2, wheelRect.centery - angle_text.get_height() // 2))
    odo_text = smallFont.render(str(wheel['odo']), 0, BLACK)
    screen.blit(odo_text, (wheelRect.centerx - odo_text.get_width() // 2, wheelRect.centery - odo_text.get_height() // 2 + angle_text.get_height() + 3))

    d1_text = smallFont.render(str(wheel['d1']), 0, WHITE)
    d2_text = smallFont.render(str(wheel['d2']), 0, WHITE)
    screen.blit(d1_text, (wheelRect.x, wheelRect.y))
    screen.blit(d2_text, (wheelRect.right - d2_text.get_width(), wheelRect.y))


    if status != 32:
        font.set_bold(True)
        statusText = font.render(wheelStatusToString(status), 24, WHITE)
        font.set_bold(False)
        # statusText = font.render(str(status), 0, BLACK)

        screen.blit(statusText, (wheelRect.centerx - statusText.get_width() // 2, wheelRect.centery - statusText.get_height() // 2 + 16))


def drawCalibration(wheel, wheelRect):
    value = wheel['cal']['deg']['0']
    _angle = wheel['angle']

    value += _angle
    if value < 0:
        value += 360
    if value >= 360:
        value -= 360

    text = font.render(str(value), 0, BLACK)
    screen.blit(text, (wheelRect.centerx - text.get_width() // 2, wheelRect.centery - text.get_height() // 2))


def drawWheel(wheelName, middleTextCallback, rect):
    wheel = wheelsMap[wheelName]

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
    imageRect = rotatedWheelImage.get_rect(center=rect.center)
    screen.blit(rotatedWheelImage, imageRect)

    if middleTextCallback is not None:
        middleTextCallback(wheel, rect)


# noinspection PyTypeChecker
def drawWheels(middleTextCallback):
    drawWheel('fr', middleTextCallback, wheelRects['fr'])
    drawWheel('fl', middleTextCallback, wheelRects['fl'])
    drawWheel('br', middleTextCallback, wheelRects['br'])
    drawWheel('bl', middleTextCallback, wheelRects['bl'])


def drawRadar():

    def limit(d):
        if d < 0:
            d = 0
        if d > 900:
            d = 900
        return 80 - d / 20.0

    rect = pygame.Rect(0, 100, 100, 100)

    d1Fl = limit(wheelsMap['fl']['d1'])
    d2Fl = limit(wheelsMap['fl']['d2'])
    d1Fr = limit(wheelsMap['fr']['d1'])
    d2Fr = limit(wheelsMap['fr']['d2'])
    d1Bl = limit(wheelsMap['bl']['d1'])
    d2Bl = limit(wheelsMap['bl']['d2'])
    d1Br = limit(wheelsMap['br']['d1'])
    d2Br = limit(wheelsMap['br']['d2'])

    # pygame.draw.arc(screen, WHITE, rect.inflate(-d1Fl, -d1Fl), 202.5, 247.5)
    # pygame.draw.arc(screen, WHITE, rect.inflate(-d2Fl, -d2Fl), 247.5, 292.5)
    # pygame.draw.arc(screen, WHITE, rect.inflate(-d1Fr, -d1Fr), 292.5, 337.5)
    # pygame.draw.arc(screen, WHITE, rect.inflate(-d1Fr, -d2Fr), 337.55, 22.5)
    #
    # pygame.draw.arc(screen, WHITE, rect.inflate(-d1Bl, -d1Bl), 22.5, 67.5)
    # pygame.draw.arc(screen, WHITE, rect.inflate(-d2Bl, -d2Bl), 67.5, 112.5)
    # pygame.draw.arc(screen, WHITE, rect.inflate(-d1Br, -d1Br), 112.5, 157.5)
    # pygame.draw.arc(screen, WHITE, rect.inflate(-d1Br, -d2Br), 157.55, 202.5)

    pi8 = math.pi / 8

    pygame.draw.arc(screen, WHITE, rect.inflate(-d2Fr, -d2Fr), pi8 * 15, pi8 * 1)  # 90º
    pygame.draw.arc(screen, WHITE, rect.inflate(-d1Fr, -d1Fr), pi8 * 1, pi8 * 3)  # 45º
    pygame.draw.arc(screen, WHITE, rect.inflate(-d2Fl, -d2Fl), pi8 * 3, pi8 * 5)  # 0º
    pygame.draw.arc(screen, WHITE, rect.inflate(-d1Fl, -d1Fl), pi8 * 5, pi8 * 7)  # 315º

    pygame.draw.arc(screen, WHITE, rect.inflate(-d2Bl, -d2Bl), pi8 * 7, pi8 * 9)  # 270º
    pygame.draw.arc(screen, WHITE, rect.inflate(-d1Bl, -d1Bl), pi8 * 9, pi8 * 11)  # 225º
    pygame.draw.arc(screen, WHITE, rect.inflate(-d1Br, -d2Br), pi8 * 11, pi8 * 13)  # 180º
    pygame.draw.arc(screen, WHITE, rect.inflate(-d1Br, -d1Br), pi8 * 13, pi8 * 15)  # 135º


def drawStatusScreen():
    drawWheels(drawAngle)
    drawRadar()
    processButtons(mainButtons)


def drawCalibrateSelectWheel():
    drawWheels(None)
    processButtons(selectWheelButtons)


def drawCalibrateWheel():
    if not hasCalibrationLoaded():
        drawTextInCentre("Loading calibration", WHITE, screen.get_rect())
        processButtons(calibrateCancelButton)
    else:
        # noinspection PyTypeChecker
        drawWheel(selectedWheel, drawCalibration, wheelRects['middle'])

        processButtons(calibrateWheelButtons)


def drawCalibratePID():
    def renderPID(label, name, y):
        screen.blit(font.render(label, 0, WHITE), (204, y))

        value = wheelsMap['pid'][name]

        s = "{0:.2f}".format(value)
        i = s.index('.')
        left = s[0:i + 1]
        right = s[i + 1:]

        leftSurface = font.render(left, 0, WHITE)
        rightSurface = font.render(right, 0, WHITE)
        screen.blit(leftSurface, (256 - leftSurface.get_width(), y))
        screen.blit(rightSurface, (256, y))

    if not hasCalibrationLoaded():
        drawTextInCentre("Loading calibration", WHITE, screen.get_rect())
        processButtons(calibrateCancelButton)
    else:
        renderPID("P", 'p', 78)
        renderPID("I", 'i', 128)
        renderPID("D", 'd', 178)
        renderPID("G", 'g', 228)
        renderPID("D", 'deadband', 278)

        processButtons(calibratePIDButtons)


def onKeyDown(key):
    global angle

    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif key == pygame.K_s:
        pyros.publish("sensor/distance/scan", "scan")
        print("** asked for distance")
    elif key == pygame.K_r:
        pyros.publish("sensor/distance/read", str(angle))
        print("** asked for distance")
    elif key == pygame.K_o:
        angle -= 11.25
        if angle < -90:
            angle = -90
    elif key == pygame.K_p:
        angle += 11.25
        if angle > 90:
            angle = 90
    else:
        pyros.gcc.handleConnectKeyDown(key)


def onKeyUp(key):
    if pyros.gcc.handleConnectKeyUp(key):
        pass


pyros.subscribe("wheel/deg/status", handleWheelOrientations)
pyros.subscribe("wheel/speed/status", handleWheelPositions)
pyros.subscribe("storage/write/wheels/cal/#", handleStorageWrite)
pyros.init("radar-client-#", unique=True, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)

initGui()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.MOUSEMOTION:
            mousePos = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouseDown = True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            mouseDown = False

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)
    pyros.gccui.background(True)

    if mode == MODE_STATUS:
        drawStatusScreen()
    elif mode == MODE_CALIBRATE_SELECT_WHEEL:
        drawCalibrateSelectWheel()
    elif mode == MODE_CALIBRATE_WHEEL:
        drawCalibrateWheel()
    elif mode == MODE_CALIBRATE_PID:
        drawCalibratePID()

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()
