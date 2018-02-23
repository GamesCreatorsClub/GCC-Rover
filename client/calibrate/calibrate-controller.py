
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import pygame
import sys
import time
import pyros.gccui

storageMap = {}
wheelMap = {}

pyros.gccui.initAll((600, 800), True)

screen = pyros.gccui.screen

bigFont = pyros.gccui.bigFont
normalFont = pyros.gccui.font

mousePos = [0, 0]

import pyros
import pyros.agent
import pyros.gcc
import pyros.pygamehelper

mouseDown = False
# lastMouseDown = False

selectedWheel = "fl"
selectedDeg = "0"
selectedSpeed = "0"
selectedRPM = 240

initialisationDone = False


def connected():
    print("Requesting calibration data from rover... ", end="")
    pyros.publish("storage/read", "READ")
    print("Done.")

    print("Starting agent... ", end="")
    pyros.agent.init(pyros.client, "calibrate-agent.py")
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
            "-240": "107",
            "-0": "155",
            "0": "155",
            "240": "203",
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
        wheelMap[wheelName]["speed"]["-300"] = defaultWheelCal["speed"]["-300"]
    if "-240" not in wheelMap[wheelName]["speed"]:
        wheelMap[wheelName]["speed"]["-240"] = {}
        wheelMap[wheelName]["speed"]["-240"] = defaultWheelCal["speed"]["-240"]
    if "-0" not in wheelMap[wheelName]["speed"]:
        wheelMap[wheelName]["speed"]["-0"] = defaultWheelCal["speed"]["-0"]
    if "0" not in wheelMap[wheelName]["speed"]:
        wheelMap[wheelName]["speed"]["0"] = defaultWheelCal["speed"]["0"]
    if "240" not in wheelMap[wheelName]["speed"]:
        wheelMap[wheelName]["speed"]["240"] = {}
        wheelMap[wheelName]["speed"]["240"] = defaultWheelCal["speed"]["240"]
    if "300" not in wheelMap[wheelName]["speed"]:
        wheelMap[wheelName]["speed"]["300"] = defaultWheelCal["speed"]["300"]


initWheel("fr", 0, 1)
initWheel("fl", 2, 3)
initWheel("br", 4, 5)
initWheel("bl", 6, 7)

texts = {
    "Wheel Calibration": bigFont.render("Wheel Calibration", True, (0, 255, 0)),
    "fl": bigFont.render("  fl  ", True, (0, 255, 0)),
    "fr": bigFont.render("  fr  ", True, (0, 255, 0)),
    "bl": bigFont.render("  bl  ", True, (0, 255, 0)),
    "br": bigFont.render("  br  ", True, (0, 255, 0)),
    "all": bigFont.render(" all ", True, (0, 255, 0)),

    "-90": bigFont.render(" -90 ", True, (0, 255, 0)),
    "-45": bigFont.render(" -45 ", True, (0, 255, 0)),
    "0": bigFont.render("  0  ", True, (0, 255, 0)),
    "45": bigFont.render(" 45 ", True, (0, 255, 0)),
    "90": bigFont.render(" 90 ", True, (0, 255, 0)),

    "+": bigFont.render("  +  ", True, (0, 255, 0)),
    "-": bigFont.render("  -  ", True, (0, 255, 0)),
    ">": bigFont.render("  <  ", True, (0, 255, 0)),
    "<": bigFont.render("  >  ", True, (0, 255, 0)),
    "SWP": bigFont.render("SWP", True, (0, 255, 0)),
}


def getTextWidth(t):
    return texts[t].get_rect().width


def getTextHeight(t):
    return texts[t].get_rect().height


buttons = {
    "bl select": {
        "texture": texts["bl"],
        "rect": pygame.Rect(304, 80, getTextWidth("bl"), getTextHeight("bl")),
    },
    "br select": {
        "texture": texts["br"],
        "rect": pygame.Rect(364, 80, getTextWidth("br"), getTextHeight("br")),
    },
    "fl select": {
        "texture": texts["fl"],
        "rect": pygame.Rect(424, 80, getTextWidth("fl"), getTextHeight("fl")),
    },
    "fr select": {
        "texture": texts["fr"],
        "rect": pygame.Rect(484, 80, getTextWidth("fr"), getTextHeight("fr")),
    },
    "all select": {
        "texture": texts["all"],
        "rect": pygame.Rect(544, 80, getTextWidth("all"), getTextHeight("all")),
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

    "speed next2": {
        "texture": texts["<"],
        "rect": pygame.Rect(470, 188, getTextWidth("+"), getTextHeight("+")),
    },
    "speed back2": {
        "texture": texts[">"],
        "rect": pygame.Rect(308, 188, getTextWidth("-"), getTextHeight("-")),
    },

    "speed -300 add": {
        "texture": texts["+"],
        "rect": pygame.Rect(510, 304, getTextWidth("+"), getTextHeight("+")),
    },
    "speed -300 minus": {
        "texture": texts["-"],
        "rect": pygame.Rect(390, 304, getTextWidth("-"), getTextHeight("-")),
    },

    "speed -240 add": {
        "texture": texts["+"],
        "rect": pygame.Rect(510, 349, getTextWidth("+"), getTextHeight("+")),
    },
    "speed -240 minus": {
        "texture": texts["-"],
        "rect": pygame.Rect(390, 349, getTextWidth("-"), getTextHeight("-")),
    },

    "speed -0 add": {
        "texture": texts["+"],
        "rect": pygame.Rect(510, 394, getTextWidth("+"), getTextHeight("+")),
    },
    "speed -0 minus": {
        "texture": texts["-"],
        "rect": pygame.Rect(390, 394, getTextWidth("-"), getTextHeight("-")),
    },

    "speed 0 add": {
        "texture": texts["+"],
        "rect": pygame.Rect(510, 454, getTextWidth("+"), getTextHeight("+")),
    },
    "speed 0 minus": {
        "texture": texts["-"],
        "rect": pygame.Rect(390, 454, getTextWidth("-"), getTextHeight("-")),
    },

    "speed 240 add": {
        "texture": texts["+"],
        "rect": pygame.Rect(510, 495, getTextWidth("+"), getTextHeight("+")),
    },
    "speed 240 minus": {
        "texture": texts["-"],
        "rect": pygame.Rect(390, 495, getTextWidth("-"), getTextHeight("-")),
    },

    "speed 300 add": {
        "texture": texts["+"],
        "rect": pygame.Rect(510, 544, getTextWidth("+"), getTextHeight("+")),
    },
    "speed 300 minus": {
        "texture": texts["-"],
        "rect": pygame.Rect(390, 544, getTextWidth("-"), getTextHeight("-")),
    },
    "speed swap": {
        "texture": texts["SWP"],
        "rect": pygame.Rect(530, 188, getTextWidth("SWP"), getTextHeight("SWP")),
    },

    "RPM next": {
        "texture": texts["+"],
        "rect": pygame.Rect(440, 600, getTextWidth("+"), getTextHeight("+")),
    },
    "RPM back": {
        "texture": texts["-"],
        "rect": pygame.Rect(328, 600, getTextWidth("-"), getTextHeight("-")),
    },

    "RPM next2": {
        "texture": texts["<"],
        "rect": pygame.Rect(470, 600, getTextWidth("+"), getTextHeight("+")),
    },
    "RPM back2": {
        "texture": texts[">"],
        "rect": pygame.Rect(308, 600, getTextWidth("-"), getTextHeight("-")),
    },

}


splitingRects = [
    pygame.Rect(2, 72, 596, 56),
    pygame.Rect(2, 130, 298, 468),
    pygame.Rect(302, 130, 296, 468),
]

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

        speedTemp = wheelMap[selectedWheel]["speed"]["-240"]
        wheelMap[selectedWheel]["speed"]["-240"] = wheelMap[selectedWheel]["speed"]["240"]
        wheelMap[selectedWheel]["speed"]["240"] = speedTemp

        speedTemp = wheelMap[selectedWheel]["speed"]["-0"]
        wheelMap[selectedWheel]["speed"]["-0"] = wheelMap[selectedWheel]["speed"]["0"]
        wheelMap[selectedWheel]["speed"]["0"] = speedTemp
        speedLimitsChanged = True

    # calibrationPoints = ["-300", "-0", "0", "300"]
    calibrationPoints = ["-300", "-240", "-0", "0", "240", "300"]

    for calSpeed in calibrationPoints:
        speedLimitsChanged = False
        buttona = buttons["speed " + calSpeed + " add"]
        buttonm = buttons["speed " + calSpeed + " minus"]

        plusDown = buttonPressed(buttona, mousePos, mouseDown)
        minusDown = buttonPressed(buttonm, mousePos, mouseDown)

        drawButton(screen, buttona, plusDown)
        drawButton(screen, buttonm, minusDown)

        if calSpeed in wheelMap[selectedWheel]["speed"]:
            drawText(screen, str(wheelMap[selectedWheel]["speed"][calSpeed]), (442, buttona["rect"].y), bigFont)

        if plusDown:
            if calSpeed in wheelMap[selectedWheel]["speed"]:
                wheelMap[selectedWheel]["speed"][calSpeed] = int(wheelMap[selectedWheel]["speed"][calSpeed]) + 1
            speedLimitsChanged = True
        elif minusDown:
            if calSpeed in wheelMap[selectedWheel]["speed"]:
                wheelMap[selectedWheel]["speed"][calSpeed] = int(wheelMap[selectedWheel]["speed"][calSpeed]) - 1
            speedLimitsChanged = True

        if calSpeed in wheelMap[selectedWheel]["speed"] and speedLimitsChanged:
            pyros.publish("storage/write/wheels/cal/" + selectedWheel + "/speed/" + calSpeed, str(wheelMap[selectedWheel]["speed"][calSpeed]))
            pyros.publish("wheel/" + selectedWheel + "/speed", selectedSpeed)


def doSpeedStettingstuff():
    global buttons
    global selectedDeg
    global selectedWheel
    global selectedSpeed

    buttona = buttons["speed next"]
    buttonm = buttons["speed back"]
    buttona2 = buttons["speed next2"]
    buttonm2 = buttons["speed back2"]

    plusDown = buttonPressed(buttona, mousePos, mouseDown)
    plusDown2 = buttonPressed(buttona2, mousePos, mouseDown)
    drawButton(screen, buttona, plusDown)
    drawButton(screen, buttona2, plusDown2)
    drawText(screen, selectedSpeed, (372, buttona["rect"].y), bigFont)
    minusDown = buttonPressed(buttonm, mousePos, mouseDown)
    minusDown2 = buttonPressed(buttonm2, mousePos, mouseDown)
    drawButton(screen, buttonm, minusDown)
    drawButton(screen, buttonm2, minusDown2)

    if plusDown:
        if selectedSpeed == "-1":
            selectedSpeed = "-0"
        elif selectedSpeed == "-0":
            selectedSpeed = "0"
        elif selectedSpeed == "0":
            selectedSpeed = "+0"
        else:
            selectedSpeed = str(int(selectedSpeed) + 1)
            if selectedSpeed == "301":
                selectedSpeed = "300"

    if plusDown2:
        s = int(selectedSpeed)
        if selectedSpeed == "-1":
            selectedSpeed = "-0"
        elif selectedSpeed == "-0":
            selectedSpeed = "0"
        elif selectedSpeed == "0":
            selectedSpeed = "+0"
        elif s > -11 and s < 0:
            selectedSpeed = "-0"
        elif s > 290:
            selectedSpeed = "300"
        else:
            selectedSpeed = str(s + 10)

    if minusDown:
        if selectedSpeed == "1":
            selectedSpeed = "+0"
        elif selectedSpeed == "+0":
            selectedSpeed = "0"
        elif selectedSpeed == "0":
            selectedSpeed = "-0"
        else:
            selectedSpeed = str(int(selectedSpeed) - 1)
            if selectedSpeed == "-301":
                selectedSpeed = "-300"

    if minusDown2:
        s = int(selectedSpeed)
        if selectedSpeed == "1":
            selectedSpeed = "+0"
        elif selectedSpeed == "+0":
            selectedSpeed = "0"
        elif selectedSpeed == "0":
            selectedSpeed = "-0"
        elif s < 11 and s > 0:
            selectedSpeed = "+0"
        elif s < -290:
            selectedSpeed = "-300"
        else:
            selectedSpeed = str(s - 10)


def doRPMStuff():
    global buttons
    global selectedRPM

    buttona = buttons["RPM next"]
    buttonm = buttons["RPM back"]
    buttona2 = buttons["RPM next2"]
    buttonm2 = buttons["RPM back2"]

    plusDown = buttonPressed(buttona, mousePos, mouseDown)
    plusDown2 = buttonPressed(buttona2, mousePos, mouseDown)
    drawButton(screen, buttona, plusDown)
    drawButton(screen, buttona2, plusDown2)
    drawText(screen, str(selectedRPM), (372, buttona["rect"].y), bigFont)
    drawText(screen, "Strobo RPM", (50, buttona["rect"].y), bigFont)

    minusDown = buttonPressed(buttonm, mousePos, mouseDown)
    minusDown2 = buttonPressed(buttonm2, mousePos, mouseDown)
    drawButton(screen, buttonm, minusDown)
    drawButton(screen, buttonm2, minusDown2)

    stroboChanged = False
    if plusDown:
        selectedRPM = selectedRPM + 1
        stroboChanged = True

    if plusDown2:
        selectedRPM = selectedRPM + 10
        stroboChanged = True

    if minusDown:
        selectedRPM = selectedRPM - 1
        stroboChanged = True

    if minusDown2:
        selectedRPM = selectedRPM - 10
        stroboChanged = True

    if stroboChanged:
        pyros.publish("calibrate/strobo", str(60 / (selectedRPM * 16)))


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
    pyros.agent.keepAgents()

    pyros.gccui.background()
    pyros.gcc.drawConnection()
    #
    # if pyros.isConnected():
    #     text = normalFont.render("Connected to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (128, 255, 128))
    # else:
    #     text = normalFont.render("Connecting to rover: " + pyros.gcc.getSelectedRoverDetailsText(), 1, (255, 128, 128))
    # screen.blit(text, pygame.Rect(0, 620, 0, 0))

    for rect in splitingRects:
        pygame.draw.rect(screen, (100, 100, 100), rect, 3)

    screen.blit(texts["Wheel Calibration"], (4, 74))

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
    drawText(screen, "-240", (328, buttons["speed -240 minus"]["rect"].y), bigFont)
    drawText(screen, "-0", (328, buttons["speed -0 minus"]["rect"].y), bigFont)
    drawText(screen, "0", (328, buttons["speed 0 minus"]["rect"].y), bigFont)
    drawText(screen, "240", (328, buttons["speed 240 minus"]["rect"].y), bigFont)
    drawText(screen, "300", (328, buttons["speed 300 minus"]["rect"].y), bigFont)
    if not selectedWheel == "all":
        doCalStuff()
    doSpeedStettingstuff()
    doRPMStuff()

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

    pyros.gccui.frameEnd()
