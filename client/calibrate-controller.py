
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import pygame
import sys
import time
import pyros
import pyros.gcc
import pyros.pygamehelper

storageMap = {}
wheelMap = {}

pygame.init()
bigFont = pygame.font.SysFont("apple casual", 64)
normalFont = pygame.font.SysFont("apple casual", 32)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600, 800))
mousePos = [0, 0]

mouseDown = False
# lastMouseDown = False

selectedWheel = "fl"
selectedDeg = "0"

initialisationDone = False


def connected():
    print("Requesting calibration data from rover... ", end="")
    pyros.publish("storage/read", "READ")
    print("Done.")


def processStorageResponse(topic, message, groups):
    global initialisationDone, wheelMap

    print("Received storage map as \n" + message)
    lines = message.split("\n")
    for line in lines:
        processLine(line)

    initialisationDone = True

    wheelMap = storageMap["wheels"]["cal"]
    initWheel("fr", 0, 1)
    initWheel("fl", 2, 3)
    initWheel("br", 4, 5)
    initWheel("bl", 6, 7)


def processLine(line):
    splitline = line.split("=")
    if not len(splitline) == 2:
        print("Received an invalid value '" + line + "'")
    else:
        path = splitline[0].split("/")
        value = splitline[1]
        m = storageMap
        for i in range(0, len(path) - 1):
            if path[i] not in m:
                m[path[i]] = {}
            m = m[path[i]]
        m[path[len(path) - 1]] = value


def initWheel(wheelName, motorServo, steerServo):

    defaultWheelCal = {
        "deg": {
            "servo": steerServo,
            "90": "70",
            "0": "160",
            "-90": "230"
        },
        "speed": {
            "servo": motorServo,
            "-300": "95",
            "-0": "155",
            "0": "155",
            "300": "215"
        }
    }

    if wheelName not in wheelMap:
        wheelMap[wheelName] = defaultWheelCal

    if "deg" not in wheelMap[wheelName]:
        wheelMap[wheelName]["deg"] = defaultWheelCal["deg"]

    if "speed" not in wheelMap[wheelName]:
        wheelMap[wheelName]["speed"] = defaultWheelCal["speed"]

    if "servo" not in wheelMap[wheelName]["deg"]:
        wheelMap[wheelName]["deg"]["servo"] = defaultWheelCal["deg"]["servo"]
    if "90" not in wheelMap[wheelName]["deg"]:
        wheelMap[wheelName]["deg"]["90"] = defaultWheelCal["deg"]["90"]
    if "0" not in wheelMap[wheelName]["deg"]:
        wheelMap[wheelName]["deg"]["0"] = defaultWheelCal["deg"]["0"]
    if "-90" not in wheelMap[wheelName]["deg"]:
        wheelMap[wheelName]["deg"]["-90"] = defaultWheelCal["deg"]["-90"]

    if "servo" not in wheelMap[wheelName]["speed"]:
        wheelMap[wheelName]["speed"]["servo"] = defaultWheelCal["speed"]["servo"]
    if "-300" not in wheelMap[wheelName]["speed"]:
        wheelMap[wheelName]["-300"]["servo"] = defaultWheelCal["speed"]["-300"]
    if "-0" not in wheelMap[wheelName]["speed"]:
        wheelMap[wheelName]["speed"]["-0"] = defaultWheelCal["speed"]["-0"]
    if "0" not in wheelMap[wheelName]["speed"]:
        wheelMap[wheelName]["speed"]["0"] = defaultWheelCal["speed"]["0"]
    if "300" not in wheelMap[wheelName]["speed"]:
        wheelMap[wheelName]["speed"]["300"] = defaultWheelCal["speed"]["300"]

initWheel("fr", 0, 1)
initWheel("fl", 2, 3)
initWheel("br", 4, 5)
initWheel("bl", 6, 7)

texts = {
    "Wheel Calibration": bigFont.render("Wheel Calibration", True, (0, 255, 0)),
    "fl": bigFont.render("fl", True, (0, 255, 0)),
    "fr": bigFont.render("fr", True, (0, 255, 0)),
    "bl": bigFont.render("bl", True, (0, 255, 0)),
    "br": bigFont.render("br", True, (0, 255, 0)),
    "all": bigFont.render("all", True, (0, 255, 0)),

    "-90": bigFont.render("-90", True, (0, 255, 0)),
    "-45": bigFont.render("-45", True, (0, 255, 0)),
    "0": bigFont.render("0", True, (0, 255, 0)),
    "45": bigFont.render("45", True, (0, 255, 0)),
    "90": bigFont.render("90", True, (0, 255, 0)),

    "+": bigFont.render("+", True, (0, 255, 0)),
    "-": bigFont.render("-", True, (0, 255, 0)),
    "SWP": bigFont.render("SWP", True, (0, 255, 0)),
}


def getTextWidth(t):
    return texts[t].get_rect().width


def getTextHeight(t):
    return texts[t].get_rect().height


buttons = {
    "br select": {
        "texture": texts["br"],
        "rect": pygame.Rect(64, 64, getTextWidth("br"), getTextHeight("br")),
    },
    "bl select": {
        "texture": texts["bl"],
        "rect": pygame.Rect(4, 64, getTextWidth("bl"), getTextHeight("bl")),
    },
    "fl select": {
        "texture": texts["fl"],
        "rect": pygame.Rect(124, 64, getTextWidth("fl"), getTextHeight("fl")),
    },
    "fr select": {
        "texture": texts["fr"],
        "rect": pygame.Rect(184, 64, getTextWidth("fr"), getTextHeight("fr")),
    },
    "all select": {
        "texture": texts["all"],
        "rect": pygame.Rect(244, 64, getTextWidth("all"), getTextHeight("all")),
    },

    "-90deg select": {
        "texture": texts["-90"],
        "rect": pygame.Rect(4, 184, getTextWidth("-90"), getTextHeight("-90")),
    },
    "-45deg select": {
        "texture": texts["-45"],
        "rect": pygame.Rect(4, 244, getTextWidth("-45"), getTextHeight("-45")),
    },
    "0deg select": {
        "texture": texts["0"],
        "rect": pygame.Rect(4, 304, getTextWidth("0"), getTextHeight("0")),
    },
    "45deg select": {
        "texture": texts["45"],
        "rect": pygame.Rect(4, 364, getTextWidth("45"), getTextHeight("45")),
    },
    "90deg select": {
        "texture": texts["90"],
        "rect": pygame.Rect(4, 424, getTextWidth("90"), getTextHeight("90")),
    },

    "deg -90 add": {
        "texture": texts["+"],
        "rect": pygame.Rect(240, 184, getTextWidth("+"), getTextHeight("+")),
    },
    "deg -90 minus": {
        "texture": texts["-"],
        "rect": pygame.Rect(128, 184, getTextWidth("-"), getTextHeight("-")),
    },

    "deg 0 add": {
        "texture": texts["+"],
        "rect": pygame.Rect(240, 304, getTextWidth("+"), getTextHeight("+")),
    },
    "deg 0 minus": {
        "texture": texts["-"],
        "rect": pygame.Rect(128, 304, getTextWidth("-"), getTextHeight("-")),
    },

    "deg 90 add": {
        "texture": texts["+"],
        "rect": pygame.Rect(240, 424, getTextWidth("+"), getTextHeight("+")),
    },
    "deg 90 minus": {
        "texture": texts["-"],
        "rect": pygame.Rect(128, 424, getTextWidth("-"), getTextHeight("-")),
    },
    "deg swap": {
        "texture": texts["SWP"],
        "rect": pygame.Rect(128, 544, getTextWidth("SWP"), getTextHeight("SWP")),
    },

    "speed next": {
        "texture": texts["+"],
        "rect": pygame.Rect(440, 188, getTextWidth("+"), getTextHeight("+")),
    },
    "speed back": {
        "texture": texts["-"],
        "rect": pygame.Rect(328, 188, getTextWidth("-"), getTextHeight("-")),
    },

    "speed -300 add": {
        "texture": texts["+"],
        "rect": pygame.Rect(540, 304, getTextWidth("+"), getTextHeight("+")),
    },
    "speed -300 minus": {
        "texture": texts["-"],
        "rect": pygame.Rect(428, 304, getTextWidth("-"), getTextHeight("-")),
    },

    "speed -0 add": {
        "texture": texts["+"],
        "rect": pygame.Rect(540, 394, getTextWidth("+"), getTextHeight("+")),
    },
    "speed -0 minus": {
        "texture": texts["-"],
        "rect": pygame.Rect(428, 394, getTextWidth("-"), getTextHeight("-")),
    },

    "speed 0 add": {
        "texture": texts["+"],
        "rect": pygame.Rect(540, 454, getTextWidth("+"), getTextHeight("+")),
    },
    "speed 0 minus": {
        "texture": texts["-"],
        "rect": pygame.Rect(428, 454, getTextWidth("-"), getTextHeight("-")),
    },

    "speed 300 add": {
        "texture": texts["+"],
        "rect": pygame.Rect(540, 544, getTextWidth("+"), getTextHeight("+")),
    },
    "speed 300 minus": {
        "texture": texts["-"],
        "rect": pygame.Rect(428, 544, getTextWidth("-"), getTextHeight("-")),
    },
    "speed swap": {
        "texture": texts["SWP"],
        "rect": pygame.Rect(500, 188, getTextWidth("SWP"), getTextHeight("SWP")),
    },

}


splitingRects = [
    pygame.Rect(2, 2, 596, 126),
    pygame.Rect(2, 130, 298, 468),
    pygame.Rect(302, 130, 296, 468),
]

speeds = ["-300", "-150", "-75", "-50", "-25", "-24", "-23", "-22", "-19", "-18", "-17", "-16", "-15", "-14", "-13", "-12", "-11", "-10", "-9", "-8", "-7", "-6", "-5", "-4", "-3", "-2", "-1", "-0", "0", "+0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "22", "23", "24", "25", "50", "75", "150", "300"]
selectedSpeedIndex = 9
selectedSpeed = speeds[selectedSpeedIndex]
lastButton = None
lastPressed = time.time()


def drawButton(surface, button, pressed):
    if pressed:
        pygame.draw.rect(screen, (255, 255, 255), button["rect"])
    else:
        pygame.draw.rect(screen, (150, 150, 150), button["rect"])
    surface.blit(button["texture"], button["rect"])


def buttonPressed(button, mousePosition, mouseButtonDown):
    global lastButton, lastPressed

    if mouseButtonDown:
        if lastButton != button:
            if button["rect"].collidepoint(mousePosition):
                lastPressed = time.time()
                lastButton = button
                return True
        else:
            if time.time() - lastPressed > 1:
                    return True
    else:
        lastButton = None

    return False


def drawText(surface, t, position, font):
    surface.blit(font.render(t, True, (0, 255, 0)), position)


def doCalStuff():
    global buttons
    global selectedDeg
    global selectedWheel
    global selectedSpeedIndex
    global speeds

    todo = ["-90", "0", "90"]

    for calDeg in todo:
        buttona = buttons["deg " + calDeg + " add"]
        buttonm = buttons["deg " + calDeg + " minus"]
        plusDown = buttonPressed(buttona, mousePos, mouseDown)
        drawButton(screen, buttona, plusDown)
        drawText(screen, str(wheelMap[selectedWheel]["deg"][calDeg]), (172, buttona["rect"].y), bigFont)
        minusDown = buttonPressed(buttonm, mousePos, mouseDown)
        drawButton(screen, buttonm, minusDown)
        if plusDown:
            wheelMap[selectedWheel]["deg"][calDeg] = int(wheelMap[selectedWheel]["deg"][calDeg]) + 1
            pyros.publish("storage/write/wheels/cal/" + selectedWheel + "/deg/" + calDeg, str(wheelMap[selectedWheel]["deg"][calDeg]))
            pyros.publish("wheel/" + selectedWheel + "/deg", selectedDeg)
        elif minusDown:
            wheelMap[selectedWheel]["deg"][calDeg] = int(wheelMap[selectedWheel]["deg"][calDeg]) - 1
            pyros.publish("storage/write/wheels/cal/" + selectedWheel + "/deg/" + calDeg, str(wheelMap[selectedWheel]["deg"][calDeg]))
            pyros.publish("wheel/" + selectedWheel + "/deg", selectedDeg)

    degSwap = buttons["deg swap"]
    degSwapDown = buttonPressed(degSwap, mousePos, mouseDown)
    drawButton(screen, degSwap, degSwapDown)

    speedSwap = buttons["speed swap"]
    speedSwapDown = buttonPressed(speedSwap, mousePos, mouseDown)
    drawButton(screen, speedSwap, speedSwapDown)

    speedLimitsChanged = False
    if selectedWheel != "all" and speedSwapDown:
        print("Swap pressed")
        speedTemp = wheelMap[selectedWheel]["speed"]["-300"]
        wheelMap[selectedWheel]["speed"]["-300"] = wheelMap[selectedWheel]["speed"]["300"]
        wheelMap[selectedWheel]["speed"]["300"] = speedTemp

        speedTemp = wheelMap[selectedWheel]["speed"]["-0"]
        wheelMap[selectedWheel]["speed"]["-0"] = wheelMap[selectedWheel]["speed"]["0"]
        wheelMap[selectedWheel]["speed"]["0"] = speedTemp
        speedLimitsChanged = True



    todo = ["-300", "-0", "0", "300"]

    for calSpeed in todo:
        buttona = buttons["speed " + calSpeed + " add"]
        buttonm = buttons["speed " + calSpeed + " minus"]
        plusDown = buttonPressed(buttona, mousePos, mouseDown)
        drawButton(screen, buttona, plusDown)
        drawText(screen, str(wheelMap[selectedWheel]["speed"][calSpeed]), (442, buttona["rect"].y), bigFont)
        minusDown = buttonPressed(buttonm, mousePos, mouseDown)
        drawButton(screen, buttonm, minusDown)
        if plusDown:
            wheelMap[selectedWheel]["speed"][calSpeed] = int(wheelMap[selectedWheel]["speed"][calSpeed]) + 1
            speedLimitsChanged = True
        elif minusDown:
            wheelMap[selectedWheel]["speed"][calSpeed] = int(wheelMap[selectedWheel]["speed"][calSpeed]) - 1
            speedLimitsChanged = True

        if speedLimitsChanged:
            pyros.publish("storage/write/wheels/cal/" + selectedWheel + "/speed/" + calSpeed, str(wheelMap[selectedWheel]["speed"][calSpeed]))
            pyros.publish("wheel/" + selectedWheel + "/speed", selectedSpeed)



def doSpeedStettingstuff():
    global buttons
    global selectedDeg
    global selectedWheel
    global selectedSpeedIndex
    global speeds

    buttona = buttons["speed next"]
    buttonm = buttons["speed back"]
    plusDown = buttonPressed(buttona, mousePos, mouseDown)
    drawButton(screen, buttona, plusDown)
    drawText(screen, speeds[selectedSpeedIndex], (372, buttona["rect"].y), bigFont)
    minusDown = buttonPressed(buttonm, mousePos, mouseDown)
    drawButton(screen, buttonm, minusDown)

    if plusDown:
        if selectedSpeedIndex + 1 > len(speeds) - 1:
            pass
        else:
            selectedSpeedIndex += 1

    if minusDown:
        if selectedSpeedIndex - 1 < 0:
            pass
        else:
            selectedSpeedIndex -= 1


def onKeyDown(key):
    if key == pygame.K_ESCAPE:
        sys.exit()
    else:
        pyros.gcc.handleConnectKeys(key)


def onKeyUp(key):
    return


wheelsList = ["fr", "fl", "br", "bl"]

pyros.subscribe("storage/values", processStorageResponse)
pyros.init("drive-controller-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)

while True:
    lastMouseDown = mouseDown
    selectedSpeed = speeds[selectedSpeedIndex]
    if selectedWheel == "all":
        for wheel in wheelsList:
            pyros.publish("wheel/" + wheel + "/speed", selectedSpeed)
    else:
        pyros.publish("wheel/" + selectedWheel + "/speed", selectedSpeed)

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

    screen.fill((0, 0, 0))

    if pyros.isConnected():
        text = normalFont.render("Connected to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (128, 255, 128))
    else:
        text = normalFont.render("Connecting to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (255, 128, 128))
    screen.blit(text, pygame.Rect(0, 620, 0, 0))

    for rect in splitingRects:
        pygame.draw.rect(screen, (100, 100, 100), rect)

    screen.blit(texts["Wheel Calibration"], (4, 4))

    drawButton(screen, buttons["bl select"], selectedWheel == "bl")
    drawButton(screen, buttons["br select"], selectedWheel == "br")
    drawButton(screen, buttons["fl select"], selectedWheel == "fl")
    drawButton(screen, buttons["fr select"], selectedWheel == "fr")

    drawButton(screen, buttons["all select"], selectedWheel == "all")

    drawButton(screen, buttons["-90deg select"], selectedDeg == "-90")
    drawButton(screen, buttons["-45deg select"], selectedDeg == "-45")
    drawButton(screen, buttons["0deg select"], selectedDeg == "0")
    drawButton(screen, buttons["45deg select"], selectedDeg == "45")
    drawButton(screen, buttons["90deg select"], selectedDeg == "90")

    drawText(screen, "-300", (328, buttons["speed -300 minus"]["rect"].y), bigFont)
    drawText(screen, "-0", (328, buttons["speed -0 minus"]["rect"].y), bigFont)
    drawText(screen, "0", (328, buttons["speed 0 minus"]["rect"].y), bigFont)
    drawText(screen, "300", (328, buttons["speed 300 minus"]["rect"].y), bigFont)
    if not selectedWheel == "all":
        doCalStuff()
    doSpeedStettingstuff()

    # if mouseDown and not lastMouseDown:
    if mouseDown:
        if buttonPressed(buttons["bl select"], mousePos, True):
            selectedWheel = "bl"
        if buttonPressed(buttons["br select"], mousePos, True):
            selectedWheel = "br"
        if buttonPressed(buttons["fl select"], mousePos, True):
            selectedWheel = "fl"
        if buttonPressed(buttons["fr select"], mousePos, True):
            selectedWheel = "fr"
        if buttonPressed(buttons["all select"], mousePos, True):
            selectedWheel = "all"

        wheelstodo = [selectedWheel]

        if selectedWheel == "all":
            wheelstodo = ["bl", "br", "fr", "fl"]

        for wheel in wheelstodo:
            if buttonPressed(buttons["-90deg select"], mousePos, True):
                selectedDeg = "-90"
                pyros.publish("wheel/" + wheel + "/deg", "-90")
            if buttonPressed(buttons["-45deg select"], mousePos, True):
                selectedDeg = "-45"
                pyros.publish("wheel/" + wheel + "/deg", "-45")
            if buttonPressed(buttons["0deg select"], mousePos, True):
                pyros.publish("wheel/" + wheel + "/deg", "0")
                selectedDeg = "0"
            if buttonPressed(buttons["45deg select"], mousePos, True):
                selectedDeg = "45"
                pyros.publish("wheel/" + wheel + "/deg", "45")
            if buttonPressed(buttons["90deg select"], mousePos, True):
                selectedDeg = "90"
                pyros.publish("wheel/" + wheel + "/deg", "90")

    drawText(screen, "Degrees:           Speed:", (4, 128), bigFont)

    pygame.display.flip()
    frameclock.tick(30)
