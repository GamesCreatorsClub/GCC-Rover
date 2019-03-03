
#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import gccui
import math
import pygame
import pyros
import pyros.gcc
import pyros.gccui
import pyros.agent
import pyros.pygamehelper
import struct
import sys
import time

from functools import partial
from pygame import Rect

sqrt2 = math.sqrt(2)

screen_size = (800, 700)
screen = pyros.gccui.initAll(screen_size, True)


def connected():
    print("Starting agent... ", end="")
    pyros.agent.init(pyros.client, "canyons-of-mars-agent.py")
    print("Done.")


class CanyonsOfMars:
    def __init__(self):
        self.running = False
        self.radar = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0}
        self.last_radar = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0}
        self.heading = 0
        self.start_heading = -1
        self.front_distance = 4000
        self.back_distance = 4000
        self.left_angle = 0
        self.right_angle = 0
        self.left_front_distance = 0
        self.right_front_distance = 0

        self.onOffButton = None
        self.maze_component = None
        self.left_angle_label = None
        self.right_angle_label = None
        self.left_front_distance_label = None
        self.right_front_distance_label = None
        self.front_distance_label = None
        self.back_distance_label = None
        self.heading_component = None

    def connected(self):
        pass
        # pyros.subscribe("canyons/odo", handleData)

    def start(self):
        self.running = True
        pyros.publish("canyons/command", "start corridor " + str(100) + " " + str(220))  # Speed/Distance
        self.onOffButton.on()

    def turnCorner(self):
        self.running = True
        pyros.publish("canyons/command", "start turnCorner " + str(100) + " " + str(300))  # Speed/Distance
        self.onOffButton.on()

    def turn180(self):
        self.running = True
        pyros.publish("canyons/command", "start turn180 " + str(100) + " " + str(166))  # Speed/Distance
        self.onOffButton.on()

    def _stop(self):
        self.running = False
        self.onOffButton.off()
        self.heading = 0
        self.start_heading = -1

    def stop(self):
        self._stop()
        pyros.publish("canyons/command", "stop")

    def handleRunning(self, topic, message, groups):
        if message == 'False':
            self._stop()

    def handleAction(self, topic, message, groups):
        self.onOffButton.label.setText(message)

    def handleOrientaion(self, topic, message, groups):
        data = message.split(" ")

        # print("LA:{:.2f} RA:{:.2f} LFD:{:.2f} RFD:{:.2f}".format(float(data[0]), float(data[1]), float(data[2]), float(data[3])))

        self.front_distance = float(data[0])
        self.back_distance = float(data[1])
        self.left_angle = float(data[2])
        self.right_angle = float(data[3])
        self.left_front_distance = float(data[4])
        self.right_front_distance = float(data[5])

        self.maze_component.front_distance = self.front_distance
        self.maze_component.back_distance = self.back_distance
        self.maze_component.left_angle = self.left_angle
        self.maze_component.right_angle = self.right_angle
        self.maze_component.left_front_distance = self.left_front_distance
        self.maze_component.right_front_distance = self.right_front_distance

        self.left_angle_label.setText("{:.2f}".format(self.left_angle))
        self.right_angle_label.setText("{:.2f}".format(self.right_angle))
        self.left_front_distance_label.setText("{:.2f}".format(self.left_front_distance))
        self.right_front_distance_label.setText("{:.2f}".format(self.right_front_distance))
        self.front_distance_label.setText("{:.2f}".format(self.front_distance))
        self.back_distance_label.setText("{:.2f}".format(self.back_distance))

    def handleDistances(self, topic, message, groups):
        for d in self.radar:
            self.last_radar[d] = self.radar[d]

        values = [v.split(":") for v in message.split(" ")]
        for (k,v) in values:
            if k != 'timestamp':
                self.radar[int(k)] = int(v)

    def handleHeading(self, topic, message, groups):
        heading_data = struct.unpack('>ffff', message)
        orientation = heading_data[2]
        if orientation < 0:
            orientation += 360

        self.heading_component.setHeading(orientation)


canyonsOfMars = CanyonsOfMars()


class MazeCorridorComponent(gccui.components.CardsCollection):
    def __init__(self, rect):
        super(MazeCorridorComponent, self).__init__(rect)

        self.rover_image = pygame.image.load("rover-top-no-cover-48.png")

        self.radar = None
        self.heading = 0
        self.front_distance = 4000
        self.back_distance = 4000
        self.left_angle = 0
        self.right_angle = 0
        self.left_front_distance = 0
        self.right_front_distance = 0

        self.scale = self.rect.width / 2

        self.rover_image_component = uiFactory.image(self.rect.copy(), self.rover_image)
        self.rover_image_component.rect.width = self.rover_image.get_width()
        self.rover_image_component.rect.height = self.rover_image.get_height()
        self.rover_image_component.rect.center = self.rect.center
        self.addComponent(self.rover_image_component)

    def draw(self, surface):
        def drawRadar(deg):
            d = self.radar[deg]

            if deg == 90 or deg == 180 or deg == 270 or deg == 0:
                if d > 1200:
                    d = 1200
            else:
                if d > 1700:
                    d = 1700

            d = int(d * self.scale / 1200)
            deg = deg * math.pi / 180 - math.pi / 2
            x = int(math.cos(deg) * d + self.rect.center[0])
            y = int(math.sin(deg) * d + self.rect.center[1])
            pygame.draw.line(surface, pygame.color.THECOLORS['gray48'], self.rect.center, (x, y))
            pygame.draw.circle(surface, pygame.color.THECOLORS['gray48'], (x, y), 3)

        def drawWall(side_distance, front_distance, angle, mod, corner):
            angle = angle / 2
            side_distance = int(side_distance * self.scale / 1200)
            front_distance = int(front_distance * self.scale / 1200)

            x0 = int(mod * side_distance)
            y0 = 0

            x2 = int(mod * math.sin(angle * math.pi / 180) * self.scale + x0)
            y2 = self.scale

            if corner:
                x1 = mod * side_distance
                y1 = 0
                if (x2 - x1) != 0.0:
                    k = (y2 - y1) / (x2 - x1)
                else:
                    k = 1000000000.0
                y = (y1 - k * x1) / (1 + mod * k)
                x = y
                x1 = int(- mod * x)
                y1 = int(y)
                x1 = x1 + self.rect.center[0]
                y1 = y1 + self.rect.center[1]

                x31 = mod * self.scale
                y31 = -mod * x2

                x31 = x31 + self.rect.center[0]
                y31 = y31 + self.rect.center[1]

                pygame.draw.line(surface, pygame.color.THECOLORS['green2'], (x1, y1), (x31, y31))

            else:
                x1 = int(-mod * math.sin(angle * math.pi / 180) * self.scale + x0)
                y1 = -self.scale

                x1 = x1 + self.rect.center[0]
                y1 = y1 + self.rect.center[1]
            x2 = x2 + self.rect.center[0]
            y2 = y2 + self.rect.center[1]

            pygame.draw.line(surface, pygame.color.THECOLORS['green2'], (x1, y1), (x2, y2))

        def drawFrontWall(front_distance, angle, left_corner, right_corner):
            if front_distance < 1200:
                front_distance = int(front_distance * self.scale / 1200)

                angle = - angle + math.pi / 2

                x0 = 0
                y0 = -front_distance

                x1 = -self.scale
                y1 = int(-math.sin(angle * math.pi / 180) * self.scale + y0)

                x2 = self.scale
                y2 = int(math.sin(angle * math.pi / 180) * self.scale + y0)

                x1 = x1 + self.rect.center[0]
                y1 = y1 + self.rect.center[1]
                x2 = x2 + self.rect.center[0]
                y2 = y2 + self.rect.center[1]

                pygame.draw.line(surface, pygame.color.THECOLORS['green2'], (x1, y1), (x2, y2))

        pygame.draw.rect(surface, pygame.color.THECOLORS['green'], self.rect, 1)
        for d in [0, 45, 90, 135, 180, 225, 270, 315]:
            drawRadar(d)

        drawWall(self.radar[90], self.radar[45], self.right_angle, 1, self.right_front_distance > 50)
        drawWall(self.radar[270], self.radar[315], self.left_angle, -1, self.left_front_distance > 50)
        drawFrontWall(self.radar[0], (self.right_angle - self.left_angle) / 2, self.left_front_distance > 0, self.right_front_distance > 0)

        rotated_rover_image = pygame.transform.rotate(self.rover_image, -self.heading)
        rotated_rover_image.get_rect(center=self.rect.center)
        self.rover_image_component._surface = rotated_rover_image

        super(MazeCorridorComponent, self).draw(surface)


class RunButtons(gccui.components.CardsCollection):
    def __init__(self, rect, off_button_text, off_callback, runners):
        super(RunButtons, self).__init__(rect)
        self.runners_count = len(runners)
        self.off_callback = off_callback

        self.onComponent = gccui.Collection(rect)
        self.label = uiFactory.label(rect, "Connecting...")
        self.addComponent(self.label)
        self.onComponent.addComponent(uiFactory.text_button(rect, off_button_text, self.off_button_clicked, hint=gccui.UI_HINT.WARNING))

        self.offComponent = gccui.Collection(rect)
        for runner in runners:
            self.offComponent.addComponent(uiFactory.text_button(rect, runner[0], partial(self.runners_button_clicked, runner[1])))
        self.offComponent.addComponent(uiFactory.text_button(rect, off_button_text, self.off_button_clicked, hint=gccui.UI_HINT.ERROR))

        self.addCard("on", self.onComponent)
        self.addCard("off", self.offComponent)

        self.selectCard("off")

        self.redefineRect(rect)

    def redefineRect(self, rect):
        margin = int(rect.height * 0.1)
        self.label.redefineRect(Rect(rect.x, rect.y, rect.width, rect.height - margin))
        self.onComponent.components[0].redefineRect(Rect(rect.x, rect.y + (self.runners_count + 1) * rect.height, rect.width, rect.height - margin))

        self.offComponent.components[0].redefineRect(Rect(rect.x, rect.y + rect.height, rect.width, rect.height - margin))
        for i in range(1, self.runners_count):
            self.offComponent.components[i].redefineRect(Rect(rect.x, rect.y + (i + 1) * rect.height, rect.width, rect.height - margin))
        self.offComponent.components[self.runners_count].redefineRect(Rect(rect.x, rect.y + (self.runners_count + 1) * rect.height, rect.width, rect.height - margin))
        self.rect = Rect(rect.x, rect.y, rect.width, rect.height * (self.runners_count + 2))
        self.onComponent.rect = self.rect
        self.offComponent.rect = self.rect

    def on(self):
        self.selectCard("on")

    def off(self):
        self.selectCard("off")

    def runners_button_clicked(self, callback, button, pos):
        self.selectCard('on')
        callback()

    def off_button_clicked(self, button, pos):
        self.selectCard('off')
        self.off_callback()


class HeadingComponent(gccui.components.CardsCollection):
    def __init__(self, rect, on_callback, off_callback):
        super(HeadingComponent, self).__init__(rect)

        self.arrow_image = pygame.image.load("arrow.png")
        self.arrow_image = pygame.transform.scale(self.arrow_image, (100, 100))

        self.on_callback = on_callback
        self.off_callback = off_callback

        self.onComponent = gccui.Collection(rect)
        self.onComponent.addComponent(uiFactory.text_button(Rect(0, 0, 0, 30), "Heading Off", self.off_button_clicked, hint=gccui.UI_HINT.WARNING))

        self.offComponent = gccui.Collection(rect)
        self.offComponent.addComponent(uiFactory.text_button(Rect(0, 0, 0, 30), "Heading On", self.on_button_clicked))

        self.addCard("on", self.onComponent)
        self.addCard("off", self.offComponent)

        self.selectCard("off")

        self.heading_label = uiFactory.label(Rect(370, 0, 70, 20), "", h_alignment=gccui.ALIGNMENT.RIGHT)
        self.addComponent(self.heading_label)

        self.image = uiFactory.image(Rect(0, 0, self.arrow_image.get_width(), self.arrow_image.get_height()), self.arrow_image, h_alignment=gccui.ALIGNMENT.CENTER, v_alignment=gccui.ALIGNMENT.MIDDLE)
        self.addComponent(self.image)

        self.redefineRect(rect)

    def redefineRect(self, rect):
        self.rect = rect
        margin = int(rect.height * 0.1)
        self.heading_label.redefineRect(Rect(rect.x, rect.y, rect.width, self.heading_label.rect.height))

        self.onComponent.redefineRect(Rect(rect.x, self.rect.bottom - 30 - margin, rect.width, 30))
        self.offComponent.redefineRect(Rect(rect.x, self.rect.bottom - 30 - margin, rect.width, 30))
        # self.onComponent.components[0].redefineRect(Rect(rect.x, self.rect.bottom - 30 - margin, rect.width, 30))
        # self.offComponent.components[0].redefineRect(Rect(rect.x, self.hearect.bottom - 30 - margin, rect.width, 30))

        self.image.redefineRect(Rect(rect.x, self.rect.y + self.heading_label.rect.height - margin, rect.width, rect.height - self.heading_label.rect.height - 30 - 2 * margin))

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

    def setHeading(self, heading):
        self.heading_label.setText("{:7.2f}".format(heading))

        rotatedImage = pygame.transform.rotate(self.arrow_image, -heading)
        rotatedImage.get_rect(center=self.rect.center)
        self.image._surface = rotatedImage


def initGraphics(screens):
    def heading_on():
        pyros.publish("position/resume", "")
        pyros.publish("position/heading/start", '{"frequency":20}')

    def heading_off():
        pyros.publish("position/heading/stop", "")
        pyros.publish("position/pause", "")

    statusComponents = gccui.Collection(screens.rect)
    screens.addCard("status", statusComponents)
    onOffButton = RunButtons(Rect(630, 40, 160, 40), "Stop", canyonsOfMars.stop, [("Run", canyonsOfMars.start), ("Turn Corner", canyonsOfMars.turnCorner), ("Turn 180", canyonsOfMars.turn180)])
    statusComponents.addComponent(onOffButton)
    canyonsOfMars.onOffButton = onOffButton
    canyonsOfMars.left_angle_label = uiFactory.label(Rect(40, 30, 70, 20), "", h_alignment=gccui.ALIGNMENT.RIGHT)
    canyonsOfMars.right_angle_label = uiFactory.label(Rect(150, 30, 70, 20), "", h_alignment=gccui.ALIGNMENT.RIGHT)
    canyonsOfMars.left_front_distance_label = uiFactory.label(Rect(40, 50, 70, 20), "", h_alignment=gccui.ALIGNMENT.RIGHT)
    canyonsOfMars.right_front_distance_label = uiFactory.label(Rect(150, 50, 70, 20), "", h_alignment=gccui.ALIGNMENT.RIGHT)
    canyonsOfMars.front_distance_label = uiFactory.label(Rect(270, 30, 70, 20), "", h_alignment=gccui.ALIGNMENT.RIGHT)
    canyonsOfMars.back_distance_label = uiFactory.label(Rect(270, 50, 70, 20), "", h_alignment=gccui.ALIGNMENT.RIGHT)
    statusComponents.addComponent(uiFactory.label(Rect(10, 30, 30, 20), "LA:"))
    statusComponents.addComponent(canyonsOfMars.left_angle_label)
    statusComponents.addComponent(uiFactory.label(Rect(120, 30, 30, 20), "RA:"))
    statusComponents.addComponent(canyonsOfMars.right_angle_label)
    statusComponents.addComponent(uiFactory.label(Rect(10, 50, 30, 20), "LD:"))
    statusComponents.addComponent(canyonsOfMars.left_front_distance_label)
    statusComponents.addComponent(uiFactory.label(Rect(120, 50, 30, 20), "RD:"))
    statusComponents.addComponent(canyonsOfMars.right_front_distance_label)
    statusComponents.addComponent(uiFactory.label(Rect(230, 30, 30, 20), "FD:"))
    statusComponents.addComponent(canyonsOfMars.front_distance_label)
    statusComponents.addComponent(uiFactory.label(Rect(230, 50, 30, 20), "BD:"))
    statusComponents.addComponent(canyonsOfMars.back_distance_label)

    maze_component = MazeCorridorComponent(Rect(10, 80, 600, 600))
    maze_component.radar = canyonsOfMars.radar
    canyonsOfMars.maze_component = maze_component
    statusComponents.addComponent(maze_component)

    canyonsOfMars.heading_component = HeadingComponent(Rect(630, 250, 160, 240), heading_on, heading_off)
    statusComponents.addComponent(canyonsOfMars.heading_component)

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
pyros.subscribe("canyons/feedback/action", canyonsOfMars.handleAction)
pyros.subscribe("canyons/feedback/running", canyonsOfMars.handleRunning)
pyros.subscribe("canyons/feedback/corridor", canyonsOfMars.handleOrientaion)
pyros.subscribeBinary("sensor/heading/data", canyonsOfMars.handleHeading)
pyros.subscribe("sensor/distance", canyonsOfMars.handleDistances)

uiAdapter = gccui.UIAdapter(screen)
uiFactory = gccui.BoxBlueSFTheme.BoxBlueSFThemeFactory(uiAdapter)
uiFactory.font = pyros.gccui.font

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
            screensComponent.redefineRect(Rect(0, 0, event.size[0], event.size[1]))

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
