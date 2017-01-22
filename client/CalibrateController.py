import paho.mqtt.client as mqtt
import pygame, sys, os


client = mqtt.Client("CalibrateController")

storageMap = {}

initialisationDone = False

def onConnect(client, data, rc):
    if rc == 0:
        print("Connected")
        client.subscribe("storage/values", 0)
        init()
    else:
        print("Connection returned error result: " + str(rc))
        os._exit(rc)

def onMessage(client, data, msg):
    global exit, initialisationDone

    payload = str(msg.payload, 'utf-8')
    topic = msg.topic

    if topic == "storage/values":
        print("Received storage map as \n" + payload)
        lines = payload.split("\n")
        for line in lines:
            processLine(line)

        initialisationDone = True
    else:
        print("Wrong topic '" + msg.topic + "'")


def processLine(line):
    splitline = line.split("=")
    if not len(splitline) == 2:
        print("Received an invalid value " + line)
    else:
        path = splitline[0].split("/")
        value = splitline[1]
        map = storageMap
        for i in range(0, len(path) - 1):
            if path[i] not in map:
                map[path[i]] = {}
            map = map[path[i]]
        map[path[len(path) - 1]] = value


def init():
    global initialisationDone

    print("Requesting calibration data from rover... ", end="")
    client.publish("storage/read", "READ")
    print("Done.")


client.on_connect = onConnect
client.on_message = onMessage

#client.connect("172.24.1.186", 1883, 60)
client.connect("192.168.1.180", 1886, 60)

print("Waiting for calibration data from rover...")
while not initialisationDone:
    client.loop()

print("Received calibration data from rover.")

print(storageMap)



pygame.init()
bigFont = pygame.font.SysFont("apple casual", 64)
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode((600,600))
mousePos = [0, 0]

mouseDown = False
lastMouseDown = False

selectedWheel = "fl"
selectedDeg = "0"
wheelCal = storageMap["wheels"]["cal"]

texts = {
    "Wheel Calibration" : bigFont.render("Wheel Calibration", True, (0,255,0)),
    "fl" : bigFont.render("fl", True, (0, 255, 0)),
    "fr" : bigFont.render("fr", True, (0, 255, 0)),
    "bl" : bigFont.render("bl", True, (0, 255, 0)),
    "br" : bigFont.render("br", True, (0, 255, 0)),
    "all" : bigFont.render("all", True, (0, 255, 0)),

    "-90" : bigFont.render("-90", True, (0, 255, 0)),
    "-45" : bigFont.render("-45", True, (0, 255, 0)),
    "0" : bigFont.render("0", True, (0, 255, 0)),
    "45" : bigFont.render("45", True, (0, 255, 0)),
    "90" : bigFont.render("90", True, (0, 255, 0)),

    "+" : bigFont.render("+", True, (0, 255, 0)),
    "-" : bigFont.render("-", True, (0, 255, 0)),
}

def getTextWidth(text):
    return texts[text].get_rect().width

def getTextHeight(text):
    return texts[text].get_rect().height

buttons = {
    "br select" : {
        "texture" : texts["br"],
        "rect" : pygame.Rect(64, 64, getTextWidth("br"), getTextHeight("br")),
    },
    "bl select" : {
        "texture" : texts["bl"],
        "rect" : pygame.Rect(4, 64, getTextWidth("bl"), getTextHeight("bl")),
    },
    "fl select" : {
        "texture" : texts["fl"],
        "rect" : pygame.Rect(124, 64, getTextWidth("fl"), getTextHeight("fl")),
    },
    "fr select" : {
        "texture" : texts["fr"],
        "rect" : pygame.Rect(184, 64, getTextWidth("fr"), getTextHeight("fr")),
    },
    "all select" : {
        "texture" : texts["all"],
        "rect" : pygame.Rect(244, 64, getTextWidth("all"), getTextHeight("all")),
    },

    "-90deg select" : {
        "texture" : texts["-90"],
        "rect" : pygame.Rect(4, 184, getTextWidth("-90"), getTextHeight("-90")),
    },
    "-45deg select" : {
        "texture" : texts["-45"],
        "rect" : pygame.Rect(4, 244, getTextWidth("-45"), getTextHeight("-45")),
    },
    "0deg select" : {
        "texture" : texts["0"],
        "rect" : pygame.Rect(4, 304, getTextWidth("0"), getTextHeight("0")),
    },
    "45deg select" : {
        "texture" : texts["45"],
        "rect" : pygame.Rect(4, 364, getTextWidth("45"), getTextHeight("45")),
    },
    "90deg select" : {
        "texture" : texts["90"],
        "rect" : pygame.Rect(4, 424, getTextWidth("90"), getTextHeight("90")),
    },

    "deg -90 add" : {
        "texture" : texts["+"],
        "rect" : pygame.Rect(240, 184, getTextWidth("+"), getTextHeight("+")),
    },
    "deg -90 minus" : {
        "texture" : texts["-"],
        "rect" : pygame.Rect(128, 184, getTextWidth("-"), getTextHeight("-")),
    },

    "deg 0 add" : {
        "texture" : texts["+"],
        "rect" : pygame.Rect(240, 304, getTextWidth("+"), getTextHeight("+")),
    },
    "deg 0 minus" : {
        "texture" : texts["-"],
        "rect" : pygame.Rect(128, 304, getTextWidth("-"), getTextHeight("-")),
    },

    "deg 90 add" : {
        "texture" : texts["+"],
        "rect" : pygame.Rect(240, 424, getTextWidth("+"), getTextHeight("+")),
    },
    "deg 90 minus" : {
        "texture" : texts["-"],
        "rect" : pygame.Rect(128, 424, getTextWidth("-"), getTextHeight("-")),
    },

    "speed next" : {
        "texture" : texts["+"],
        "rect" : pygame.Rect(440, 188, getTextWidth("+"), getTextHeight("+")),
    },
    "speed back" : {
        "texture" : texts["-"],
        "rect" : pygame.Rect(328, 188, getTextWidth("-"), getTextHeight("-")),
    },



    "speed -300 add" : {
        "texture" : texts["+"],
        "rect" : pygame.Rect(540, 304, getTextWidth("+"), getTextHeight("+")),
    },
    "speed -300 minus" : {
        "texture" : texts["-"],
        "rect" : pygame.Rect(428, 304, getTextWidth("-"), getTextHeight("-")),
    },

    "speed 0 add" : {
        "texture" : texts["+"],
        "rect" : pygame.Rect(540, 424, getTextWidth("+"), getTextHeight("+")),
    },
    "speed 0 minus" : {
        "texture" : texts["-"],
        "rect" : pygame.Rect(428, 424, getTextWidth("-"), getTextHeight("-")),
    },

    "speed 300 add" : {
        "texture" : texts["+"],
        "rect" : pygame.Rect(540, 544, getTextWidth("+"), getTextHeight("+")),
    },
    "speed 300 minus" : {
        "texture" : texts["-"],
        "rect" : pygame.Rect(428, 544, getTextWidth("-"), getTextHeight("-")),
    },

}

splitingRects = [
    pygame.Rect(2, 2, 596, 126),
    pygame.Rect(2, 130, 298, 468),
    pygame.Rect(302, 130, 296, 468),
]

speeds = ["-300","-150","-75","-50","0","50","75","150","300"]
selectedSpeedIndex = 4
selectedSpeed = speeds[selectedSpeedIndex]

def drawButton(surface, button, pressed):
    if pressed:
        pygame.draw.rect(screen, (255,255,255), button["rect"])
    else:
        pygame.draw.rect(screen, (150, 150, 150), button["rect"])
    surface.blit(button["texture"], button["rect"])

def buttonPressed(button, mousePos, mouseDown):
    if mouseDown:
        if button["rect"].collidepoint(mousePos):
            return True
        else:
            return False
    else:
        return False


def drawText(surface, text, position, font):
    surface.blit(font.render(text, True, (0,255,0)), position)

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
        plusDown = buttonPressed(buttona, mousePos, mouseDown and not lastMouseDown)
        drawButton(screen, buttona, plusDown)
        drawText(screen, str(wheelCal[selectedWheel]["deg"][calDeg]), (172, buttona["rect"].y), bigFont)
        minusDown = buttonPressed(buttonm, mousePos, mouseDown and not lastMouseDown)
        drawButton(screen, buttonm, minusDown)
        if plusDown:
            wheelCal[selectedWheel]["deg"][calDeg] = int(wheelCal[selectedWheel]["deg"][calDeg]) + 1
            client.publish("storage/write/wheels/cal/" + selectedWheel + "/deg/" + calDeg, str(wheelCal[selectedWheel]["deg"][calDeg]))
            client.publish("wheel/" + selectedWheel + "/deg", selectedDeg)
        elif minusDown:
            wheelCal[selectedWheel]["deg"][calDeg] = int(wheelCal[selectedWheel]["deg"][calDeg]) - 1
            client.publish("storage/write/wheels/cal/" + selectedWheel + "/deg/" + calDeg, str(wheelCal[selectedWheel]["deg"][calDeg]))
            client.publish("wheel/" + selectedWheel + "/deg", selectedDeg)
    todo = ["-300", "0", "300"]

    for calSpeed in todo:
        buttona = buttons["speed " + calSpeed + " add"]
        buttonm = buttons["speed " + calSpeed + " minus"]
        plusDown = buttonPressed(buttona, mousePos, mouseDown and not lastMouseDown)
        drawButton(screen, buttona, plusDown)
        drawText(screen, str(wheelCal[selectedWheel]["speed"][calSpeed]), (442, buttona["rect"].y), bigFont)
        minusDown = buttonPressed(buttonm, mousePos, mouseDown and not lastMouseDown)
        drawButton(screen, buttonm, minusDown)
        if plusDown:
            wheelCal[selectedWheel]["speed"][calSpeed] = int(wheelCal[selectedWheel]["speed"][calSpeed]) + 1
            client.publish("storage/write/wheels/cal/" + selectedWheel + "/speed/" + calSpeed,
                           str(wheelCal[selectedWheel]["speed"][calSpeed]))
            client.publish("wheel/" + selectedWheel + "/speed", selectedSpeed)
        elif minusDown:
            wheelCal[selectedWheel]["speed"][calSpeed] = int(wheelCal[selectedWheel]["speed"][calSpeed]) - 1
            client.publish("storage/write/wheels/cal/" + selectedWheel + "/speed/" + calSpeed,
                           str(wheelCal[selectedWheel]["speed"][calSpeed]))
            client.publish("wheel/" + selectedWheel + "/speed", selectedSpeed)

def doSpeedStettingstuff():
    global buttons
    global selectedDeg
    global selectedWheel
    global selectedSpeedIndex
    global speeds

    buttona = buttons["speed next"]
    buttonm = buttons["speed back"]
    plusDown = buttonPressed(buttona, mousePos, mouseDown and not lastMouseDown)
    drawButton(screen, buttona, plusDown)
    drawText(screen, speeds[selectedSpeedIndex], (372, buttona["rect"].y), bigFont)
    minusDown = buttonPressed(buttonm, mousePos, mouseDown and not lastMouseDown)
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



wheelsList = ["fr","fl","br","bl"]
while True:
    lastMouseDown = mouseDown
    selectedSpeed = speeds[selectedSpeedIndex]
    if (selectedWheel == "all"):

        for wheel in wheelsList:
            client.publish("wheel/" + wheel + "/speed", selectedSpeed)
    else:
        client.publish("wheel/" + selectedWheel + "/speed", selectedSpeed)

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

    screen.fill((0,0,0))
    for rect in splitingRects:
        pygame.draw.rect(screen, (100,100,100), rect)

    screen.blit(texts["Wheel Calibration"], (4,4))

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

    drawText(screen,"-300", (328, buttons["speed -300 minus"]["rect"].y), bigFont)
    drawText(screen, "0", (328, buttons["speed 0 minus"]["rect"].y), bigFont)
    drawText(screen, "300", (328, buttons["speed 300 minus"]["rect"].y), bigFont)
    if not selectedWheel == "all" :
        doCalStuff()
    doSpeedStettingstuff()


    if mouseDown and not lastMouseDown:
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
            wheelstodo = ["bl","br","fr","fl"]

        for wheel in wheelstodo:
            if buttonPressed(buttons["-90deg select"], mousePos, True):
                selectedDeg = "-90"
                client.publish("wheel/" + wheel + "/deg", "-90")
            if buttonPressed(buttons["-45deg select"], mousePos, True):
                selectedDeg = "-45"
                client.publish("wheel/" + wheel + "/deg", "-45")
            if buttonPressed(buttons["0deg select"], mousePos, True):
                client.publish("wheel/" + wheel + "/deg", "0")
                selectedDeg = "0"
            if buttonPressed(buttons["45deg select"], mousePos, True):
                selectedDeg = "45"
                client.publish("wheel/" + wheel + "/deg", "45")
            if buttonPressed(buttons["90deg select"], mousePos, True):
                selectedDeg = "90"
                client.publish("wheel/" + wheel + "/deg", "90")

    drawText(screen, "Degrees:           Speed:", (4, 128), bigFont)
    # drawText(screen, " 90: [-] " + str(wheelsMap[selectedWheel]["deg"]["90"]) + " [+] ",  (4, 172), bigFont)
    # drawText(screen, "  0: [-] " + str(wheelsMap[selectedWheel]["deg"]["0"]) + " [+] ",   (4, 212), bigFont)
    # drawText(screen, "-90: [-] " + str(wheelsMap[selectedWheel]["deg"]["-90"]) + " [+] ", (4, 242), bigFont)

    client.loop(1/40)

    pygame.display.flip()
    frameclock.tick(30)

    # print(str(mouseDown and not lastMouseDown))
    keys = pygame.key.get_pressed()



