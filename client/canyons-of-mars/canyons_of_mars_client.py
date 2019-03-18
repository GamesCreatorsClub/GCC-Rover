
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
import sys
import time

from pygame import Rect
from client_utils import TelemetryUtil, RunLog
from rover import Rover
from canyon_compponents import MazeCorridorComponent
from agent_components import RunButtons, HeadingComponent, ReflectonValueWithLabel, ReflectonAngleWithLabel, ReflectonLookupWithLabel, WheelsStatus
from roverscreencomponents import Radar

sqrt2 = math.sqrt(2)

screen_size = (1024, 800)
screen = pyros.gccui.initAll(screen_size, True)


def connected():
    print("Starting agent... ", end="")
    pyros.agent.init(pyros.client, "canyons_of_mars_agent.py", optional_files=["../common/rover.py", "maze.py"])
    print("Done.")


class CanyonsOfMars:
    def __init__(self):
        self.telemetry = TelemetryUtil()
        self.rover = Rover()
        self.run_log = RunLog(self.rover)
        self.running = False

        self.runButtons = None
        self.maze_component = None
        self.left_angle_label = None
        self.right_angle_label = None
        self.left_front_distance_label = None
        self.right_front_distance_label = None
        self.front_distance_label = None
        self.back_distance_label = None
        self.last_command = None
        self.heading_component = None

    def connected(self):
        pass
        # pyros.subscribe("canyons/odo", handleData)

    def start(self):
        self.running = True
        self.run_log.reset()
        pyros.publish("canyons/command", "start corridor " + str(100) + " " + str(220))  # Speed/Distance
        self.runButtons.on()

    def turnCorner(self):
        self.running = True
        self.run_log.reset()
        pyros.publish("canyons/command", "start turnCorner " + str(100) + " " + str(300))  # Speed/Distance
        self.runButtons.on()

    def turn180(self):
        self.running = True
        self.run_log.reset()
        pyros.publish("canyons/command", "start turn180 " + str(100) + " " + str(166))  # Speed/Distance
        self.runButtons.on()

    def _stop(self):
        prev_running = self.running
        self.running = False
        self.runButtons.off()
        self.heading = 0
        self.start_heading = -1
        if prev_running:
            self.telemetry.fetchData("rover-state", self.run_log.addNewRecord)

    def stop(self):
        self._stop()
        pyros.publish("canyons/command", "stop")

    def handleRunning(self, topic, message, groups):
        if message == 'False':
            self._stop()

    def handleAction(self, topic, message, groups):
        self.runButtons.label.setText(message)

    def getRadar(self):
        state = self.rover.getRoverState()
        if state.radar is not None:
            radar = state.radar
            return radar.radar, radar.last_radar, radar.status
        return None, None, None

    def _getWheelStatus(self, wheel_name):
        state = self.rover.getRoverState()

        if state.wheel_orientations is not None:
            ori_status = state.wheel_orientations.status[wheel_name]
        else:
            ori_status = 0

        if self.rover.wheel_odos is not None:
            odo_status = state.wheel_odos.status[wheel_name]
        else:
            odo_status = 0

        return odo_status | ori_status

    def getWheelAngleAndStatus(self, wheel_name):
        state = self.rover.getRoverState()
        angle = 0
        status = 0
        if state.wheel_orientations is not None:
            status = self._getWheelStatus(wheel_name)
            angle = state.wheel_orientations.orientations[wheel_name]

        return angle, status

    def getWheelOdoAndStatus(self, wheel_name):
        state = self.rover.getRoverState()
        odo = 0
        status = 0
        if state.wheel_odos is not None:
            status = self._getWheelStatus(wheel_name)
            odo = state.wheel_odos.odos[wheel_name]

        return odo, status

    def getHeading(self):
        if self.rover.heading is not None:
            return self.rover.getRoverState().heading.heading

        return 0


canyonsOfMars = CanyonsOfMars()


def initGraphics(screens, rect):
    def heading_on():
        pyros.publish("sensor/distance/resume", "")
        pyros.publish("position/resume", "")
        pyros.publish("position/heading/start", '{"frequency":20}')

    def heading_off():
        pyros.publish("position/heading/stop", "")
        pyros.publish("position/pause", "")
        pyros.publish("sensor/distance/pause", "")

    statusComponents = gccui.Collection(screens.rect)
    screens.addCard("status", statusComponents)

    runButtons = RunButtons(Rect(rect.right - 160, rect.y, 160, 280), uiFactory, canyonsOfMars.run_log, canyonsOfMars.stop, [("Run", canyonsOfMars.start), ("Turn Corner", canyonsOfMars.turnCorner), ("Turn 180", canyonsOfMars.turn180)])
    statusComponents.addComponent(runButtons)
    canyonsOfMars.runButtons = runButtons

    wheelStatus = WheelsStatus(Rect(rect.x, rect.y, 300, 380), uiFactory, canyonsOfMars.getWheelOdoAndStatus, canyonsOfMars.getWheelAngleAndStatus)
    statusComponents.addComponent(wheelStatus)

    radar = Radar(Rect(rect.x, wheelStatus.rect.bottom + 10, 300, 300), uiFactory, canyonsOfMars.getRadar, 1500, display_delta=True)
    canyonsOfMars.radar = radar
    statusComponents.addComponent(canyonsOfMars.radar)

    maze_component = MazeCorridorComponent(Rect(wheelStatus.rect.right + 20, rect.y, 400, 400), uiFactory, canyonsOfMars.rover)
    canyonsOfMars.maze_component = maze_component
    statusComponents.addComponent(maze_component)

    canyonsOfMars.left_angle_label = ReflectonAngleWithLabel(Rect(maze_component.rect.x, maze_component.rect.bottom + 5, 70, 16), "LA: ", "{:>5d}", canyonsOfMars.rover, "current_state.left_wall_angle", font=uiFactory.font)
    canyonsOfMars.left_front_distance_label = ReflectonValueWithLabel(Rect(canyonsOfMars.left_angle_label.rect.right + 10, canyonsOfMars.left_angle_label.rect.y, 80, 16), "LFD: ", "{:>5d}", canyonsOfMars.rover, "current_state.left_front_distance_of_wall", font=uiFactory.font)
    canyonsOfMars.left_front_gap_type = ReflectonLookupWithLabel(Rect(canyonsOfMars.left_front_distance_label.rect.right + 10, canyonsOfMars.left_angle_label.rect.y, 100, 16), "LT: ", "{:>7s}", canyonsOfMars.rover, "current_state.left_front_gap_type", ["None", "Corner", "Chicane"], font=uiFactory.font)

    canyonsOfMars.right_angle_label = ReflectonAngleWithLabel(Rect(maze_component.rect.x, canyonsOfMars.left_angle_label.rect.bottom + 5, 70, 16), "RA: ", "{:>5d}", canyonsOfMars.rover, "current_state.right_wall_angle", font=uiFactory.font)
    canyonsOfMars.right_front_distance_label = ReflectonValueWithLabel(Rect(canyonsOfMars.right_angle_label.rect.right + 10, canyonsOfMars.right_angle_label.rect.y, 80, 16), "RFD: ", "{:>5d}", canyonsOfMars.rover, "current_state.right_front_distance_of_wall", font=uiFactory.font)
    canyonsOfMars.right_front_gap_type = ReflectonLookupWithLabel(Rect(canyonsOfMars.right_front_distance_label.rect.right + 10, canyonsOfMars.right_angle_label.rect.y, 100, 16), "RT: ", "{:>7s}", canyonsOfMars.rover, "current_state.right_front_gap_type", ["None", "Corner", "Chicane"], font=uiFactory.font)

    canyonsOfMars.front_distance_label = ReflectonValueWithLabel(Rect(canyonsOfMars.left_front_gap_type.rect.right + 10, canyonsOfMars.left_front_gap_type.rect.y, 80, 16), "FD: ", "{:>5d}", canyonsOfMars.rover, "current_state.front_wall_distance", font=uiFactory.font)
    canyonsOfMars.back_distance_label = ReflectonValueWithLabel(Rect(canyonsOfMars.right_front_gap_type.rect.right + 10, canyonsOfMars.right_front_gap_type.rect.y, 80, 16), "BD: ", "{:>5d}", canyonsOfMars.rover, "current_state.back_wall_distance", font=uiFactory.font)

    canyonsOfMars.last_command = ReflectonValueWithLabel(Rect(canyonsOfMars.right_angle_label.rect.x, canyonsOfMars.right_angle_label.rect.bottom + 5, 80, 16), "LC: ", "{:26s}", canyonsOfMars.rover, "current_state.last_command.display", font=uiFactory.font)
    canyonsOfMars.selection_str = ReflectonValueWithLabel(Rect(canyonsOfMars.last_command.rect.x, canyonsOfMars.last_command.rect.bottom + 5, 80, 16), "S: ", "{:26s}", canyonsOfMars.rover, "current_state.selection", font=uiFactory.font)

    statusComponents.addComponent(canyonsOfMars.left_angle_label)
    statusComponents.addComponent(canyonsOfMars.left_front_distance_label)
    statusComponents.addComponent(canyonsOfMars.left_front_gap_type)

    statusComponents.addComponent(canyonsOfMars.right_angle_label)
    statusComponents.addComponent(canyonsOfMars.right_front_distance_label)
    statusComponents.addComponent(canyonsOfMars.right_front_gap_type)

    statusComponents.addComponent(canyonsOfMars.front_distance_label)
    statusComponents.addComponent(canyonsOfMars.back_distance_label)
    statusComponents.addComponent(canyonsOfMars.last_command)
    statusComponents.addComponent(canyonsOfMars.selection_str)

    canyonsOfMars.heading_component = HeadingComponent(Rect(radar.rect.x, radar.rect.y, radar.rect.width, radar.rect.height + 30), uiFactory, canyonsOfMars.getHeading, heading_on, heading_off)
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

pyros.subscribe("wheel/speed/status", canyonsOfMars.rover.handleOdo)
pyros.subscribe("wheel/deg/status", canyonsOfMars.rover.handleWheelOrientation)
pyros.subscribe("sensor/distance", canyonsOfMars.rover.handleRadar)
pyros.subscribeBinary("sensor/heading/data", canyonsOfMars.rover.handleHeading)

pyros.subscribe("canyons/feedback/action", canyonsOfMars.handleAction)
pyros.subscribe("canyons/feedback/running", canyonsOfMars.handleRunning)

font = pygame.font.Font("../common/garuda.ttf", 18)
smallFont = pygame.font.Font("../common/garuda.ttf", 12)

uiAdapter = gccui.UIAdapter(screen)
uiFactory = gccui.BoxBlueSFTheme.BoxBlueSFThemeFactory(uiAdapter)
uiFactory.font = font

screensComponent = gccui.CardsCollection(screen.get_rect())
uiAdapter.setTopComponent(screensComponent)
initGraphics(screensComponent, screen.get_rect().inflate(-10, -40).move(0, 20))

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

    if not canyonsOfMars.runButtons.playback:
        state = canyonsOfMars.rover.nextState()
        state.calculate()

    uiAdapter.draw(screen)

    pyros.gccui.drawSmallText("Put help here", (8, screen.get_height() - pyros.gccui.smallFont.get_height()))

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()

    now = time.time()
