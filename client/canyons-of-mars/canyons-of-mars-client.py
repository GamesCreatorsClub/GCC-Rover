
#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import sys
import time
import pygame
import gccui
import pyros
import pyros.gcc
import pyros.gccui
import pyros.agent
import pyros.pygamehelper


screen_size = (800, 640)
screen = pyros.gccui.initAll(screen_size, True)


def connected():
    print("Starting agent... ", end="")
    pyros.agent.init(pyros.client, "canyons-of-mars-agent.py")
    print("Done.")


class CanyonsOfMars:
    def __init__(self):
        self.running = False
        self.onOffButton = None

    def connected(self):
        pass
        # pyros.subscribe("canyons/odo", handleData)

    def start(self):
        self.running = True
        pyros.publish("canyons/command", "start " + str(360 * 2.2))
        self.onOffButton.on()

    def stop(self):
        self.running = False
        pyros.publish("canyons/command", "stop")
        self.onOffButton.off()

    def handleRunning(self, topic, message, groups):
        if message == 'False':
            self.running = False
            self.onOffButton.off()


canyonsOfMars = CanyonsOfMars()


class OnOffButton(gccui.components.CardsCollection):
    def __init__(self, rect, on_label_text, off_label_text, on_button_text, off_button_text, on_callback, off_callback):
        super(OnOffButton, self).__init__(rect)
        self.on_callback = on_callback
        self.off_callback = off_callback
        self.onComponent = gccui.Collection(rect)
        self.onComponent.addComponent(uiFactory.label(rect, on_label_text))
        self.onComponent.addComponent(uiFactory.text_button(rect, off_button_text, self.off_button_clicked, hint=gccui.UI_HINT.WARNING))
        self.offComponent = gccui.Collection(rect)
        self.offComponent.addComponent(uiFactory.label(rect, off_label_text))
        self.offComponent.addComponent(uiFactory.text_button(rect, on_button_text, self.on_button_clicked))
        self.offComponent.addComponent(uiFactory.text_button(rect, off_button_text, self.off_button_clicked, hint=gccui.UI_HINT.ERROR))
        self.addCard("on", self.onComponent)
        self.addCard("off", self.offComponent)
        self.selectCard("off")
        self.redefineRect(rect)

    def redefineRect(self, rect):
        width = int(rect.width * 0.3)
        margin = int(rect.width * 0.05)

        self.onComponent.components[0].redefineRect(pygame.Rect(rect.x, rect.y, width, rect.height))
        self.onComponent.components[1].redefineRect(pygame.Rect(rect.right - width, rect.y, width, rect.height))

        self.offComponent.components[0].redefineRect(pygame.Rect(rect.x, rect.y, width, rect.height))
        self.offComponent.components[1].redefineRect(pygame.Rect(rect.x + width + margin, rect.y, width, rect.height))
        self.offComponent.components[2].redefineRect(pygame.Rect(rect.right - width, rect.y, width, rect.height))

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


def initGraphics(screens):
    # arrow_image = pygame.image.load("arrow.png")
    # arrow_image = pygame.transform.scale(arrow_image, (50, 50))

    statusComponents = gccui.Collection(screens.rect)
    screens.addCard("status", statusComponents)
    onOffButton = OnOffButton(pygame.Rect(10, 40, 300, 30), "Running", "Stopped", "Run", "Stop", canyonsOfMars.start, canyonsOfMars.stop)
    statusComponents.addComponent(onOffButton)
    canyonsOfMars.onOffButton = onOffButton

    screens.selectCard("status")


def onKeyDown(key):
    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif key == pygame.K_SPACE:
        canyonsOfMars.stop()
    elif key == pygame.K_RETURN:
        canyonsOfMars.start()


def onKeyUp(key):
    pyros.gcc.handleConnectKeyUp(key)
    return


pyros.init("canyons-of-mars-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)
pyros.subscribe("canyons/feedback/running", canyonsOfMars.handleRunning)

uiFactory = gccui.BoxBlueSFTheme.BoxBlueSFThemeFactory()
uiFactory.font = pyros.gccui.font
uiAdapter = gccui.UIAdapter(screen)

screensComponent = gccui.CardsCollection(screen.get_rect())
uiAdapter.setTopComponent(screensComponent)
initGraphics(screensComponent)

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.VIDEORESIZE:
            pyros.gccui.screenResized(event.size)
            screensComponent.redefineRect(pygame.Rect(0, 0, event.size[0], event.size[1]))

        uiAdapter.processEvent(event)

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)
    pyros.agent.keepAgents()
    pyros.gccui.background(True)

    uiAdapter.draw(screen)

    pyros.gccui.drawSmallText("Put help here", (8, screen.get_height() - pyros.gccui.smallFont.get_height()))

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()

    now = time.time()
