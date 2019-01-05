
#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

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

wheelImage = None
wheelGreenImage = None
wheelOrangeImage = None
wheelRedImage = None
wheelRects = {'fl': None, 'fr': None, 'bl': None, 'br': None}

screen = pyros.gccui.initAll((480, 320), True)
font = pyros.gccui.font

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


def createTemplateWheel():
    return {
        'angle': 0,
        'max': 0,
        'min': 0,
        'status': 0,
        'cal': {}
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
    wheel = wheelsMap[selectedWheel]
    calDeg = wheel['cal']['deg']['0']
    angle = wheel['angle']
    value = angle + calDeg
    if value < 0:
        value += 360

    if value >= 360:
        value -= 360

    wheel['wanted'] = 0

    print("Old value " + str(calDeg) + ", angle " + str(angle) + ", new value " + str(value))

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
    dir = wheelsMap[str(selectedWheel)]['cal']['deg']['dir']
    dir = -dir
    wheelsMap[str(selectedWheel)]['cal']['deg']['dir'] = dir
    print("Old value " + str(-dir) + ", new value " + str(dir))
    pyros.publish("storage/write/wheels/cal/" + str(selectedWheel) + "/deg/dir", str(dir))


def directionSteerToggleButtonClick():
    wheel = wheelsMap[str(selectedWheel)]
    dir = wheelsMap[str(selectedWheel)]['cal']['steer']['dir']
    dir = -dir
    wheelsMap[str(selectedWheel)]['cal']['steer']['dir'] = dir
    print("Old value " + str(-dir) + ", new value " + str(dir))
    pyros.publish("storage/write/wheels/cal/" + str(selectedWheel) + "/steer/dir", str(dir))


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
        button = {'rect': rect, 'onClick': onClick}

        button['drawSelected'] = drawSelected
        button['draw'] = draw
        button['text'] = font.render(text, 20, WHITE)
        return button

    def makeBorderButton(rect, onClick):
        button = {'rect': rect, 'onClick': onClick}

        def drawSelected(button):
            rect = button['rect']
            pygame.draw.rect(screen, WHITE, rect, 1)

        def draw(button):
            rect = button['rect']
            pygame.draw.rect(screen, WHITE, rect, 1)

        button['drawSelected'] = drawSelected
        button['draw'] = draw
        return button

    def makeDirectionToggleButton(rect, text, calPath, onClick):
        button = {'rect': rect, 'onClick': onClick}

        def checkText(button):
            dir = wheelsMap[selectedWheel]['cal'][calPath]['dir']
            if 'text' not in button or button['prevdir'] != dir:

                button['text'] = font.render(text + "<---" if dir < 0 else text + "--->", 20, WHITE)
                button['prevdir'] = dir

        def drawToggleSelected(button):
            checkText(button)
            drawSelected(button)

        def drawToggle(button):
            checkText(button)
            draw(button)

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

    def updateWheel(wheelName, values, index):
        wheel = wheelsMap[wheelName]
        angleStr = values[index]
        if angleStr != '-':
            angle = int(angleStr)
            wheel['angle'] = angle
            wheel['status'] = int(values[index + 1])
            if 'wanted' not in wheel or mode != MODE_CALIBRATE_WHEEL:
                wheel['wanted'] = angle
            if angle < wheel['min']:
                wheel['min'] = angle
            if angle > wheel['max']:
                wheel['max'] = angle
        else:
            wheel['status'] = int(values[index + 1])

    received = True
    # print("** wheel positions = " + message)

    values = message.split(",")
    updateWheel('fl', values, 0)
    updateWheel('fr', values, 2)
    updateWheel('bl', values, 4)
    updateWheel('br', values, 6)


def handleStorageWrite(topic, message, groups):
    topics = topic[len("storage/write/wheels/cal/"):].split('/')

    wheelName = topics[0]

    if 'pid' == wheelName:
        pid = wheelsMap['pid']
        try:
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

    return hasCalibrationLoadedWheel('fr') and hasCalibrationLoadedWheel('fl') and \
           hasCalibrationLoadedWheel('br') and hasCalibrationLoadedWheel('bl') and \
           hasCalibrationLoadedPID()


def processButtons(buttons):
    global selectedButton, mousePreviousState

    def findButton():
        for button in buttons:
            if button['rect'].collidepoint(mousePos):
                return button

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
    text = font.render(str(text), 20, colour)
    screen.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))


def drawAngle(wheel, wheelRect):

    def wheelStatusToString(status):
        if status == 1:
            return "ERR"
        else:
            return ("O" if status & 2 else "") + ("H" if status & 8 else "") + ("L" if status & 16 else "") + ("D" if status & 32 else "")

    status = wheel['status']
    text = font.render(str(wheel['angle']), 20, BLACK)
    screen.blit(text, (wheelRect.centerx - text.get_width() // 2, wheelRect.centery - text.get_height() // 2))

    if status != 32:
        font.set_bold(True)
        statusText = font.render(wheelStatusToString(status), 24, WHITE)
        font.set_bold(False)
        # statusText = font.render(str(status), 20, BLACK)

        screen.blit(statusText, (wheelRect.centerx - statusText.get_width() // 2, wheelRect.centery - statusText.get_height() // 2 + text.get_height() + 2))


def drawCalibration(wheel, wheelRect):
    value = wheel['cal']['deg']['0']
    angle = wheel['angle']

    value += angle
    if value < 0:
        value += 360
    if value >= 360:
        value -= 360

    text = font.render(str(value), 20, BLACK)
    screen.blit(text, (wheelRect.centerx - text.get_width() // 2, wheelRect.centery - text.get_height() // 2))


def drawWheel(wheelName, middleTextCallback, rect):

    wheel = wheelsMap[wheelName]

    selectedWheelImage = wheelImage
    status = wheel['status']
    if status == 32:
        selectedWheelImage = wheelGreenImage
    elif not status & 1 and not status & 2 and status & 32 and (status & 8 or status & 16):
        selectedWheelImage = wheelOrangeImage
    else:
        selectedWheelImage = wheelRedImage

    angle = float(wheel['angle'])

    rotatedWheelImage = pygame.transform.rotate(selectedWheelImage, -angle)
    imageRect = rotatedWheelImage.get_rect(center=rect.center)
    screen.blit(rotatedWheelImage, imageRect)

    if middleTextCallback is not None:
        middleTextCallback(wheel, rect)


def drawWheels(middleTextCallback):
    drawWheel('fr', middleTextCallback, wheelRects['fr'])
    drawWheel('fl', middleTextCallback, wheelRects['fl'])
    drawWheel('br', middleTextCallback, wheelRects['br'])
    drawWheel('bl', middleTextCallback, wheelRects['bl'])


def drawStatusScreen():
    drawWheels(drawAngle)
    processButtons(mainButtons)


def drawCalibrateSelectWheel():
    drawWheels(None)
    processButtons(selectWheelButtons)


def drawCalibrateWheel():
    if not hasCalibrationLoaded():
        drawTextInCentre("Loading calibration", WHITE, screen.get_rect())
        processButtons(calibrateCancelButton)
    else:
        drawWheel(selectedWheel, drawCalibration, wheelRects['middle'])

        processButtons(calibrateWheelButtons)


def drawCalibratePID():
    def renderPID(label, name, y):
        screen.blit(font.render(label, 20, WHITE), (204, y))

        value = wheelsMap['pid'][name]

        s = "{0:.2f}".format(value)
        i = s.index('.')
        left = s[0:i+1]
        right = s[i+1:]

        leftSurface = font.render(left, 20, WHITE)
        rightSurface = font.render(right, 20, WHITE)
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


pyros.subscribe("wheel/status/pos", handleWheelPositions)
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