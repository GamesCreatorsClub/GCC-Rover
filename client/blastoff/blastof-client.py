
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import gccui
import pyros
import pyros.gcc
import pyros.gccui
import pyros.agent
import pyros.pygamehelper
import pygame
import sys
import time

from pygame import Rect
from PIL import Image
from rover import Rover
from client_utils import TelemetryUtil, RunLog
from agent_components import RunButtons, HeadingComponent, Border, BorderImage, ReflectonValueWithLabel, ReflectonAngleWithLabel, ReflectonLookupWithLabel, WheelsStatus
from roverscreencomponents import Radar

screen_size = (1024, 800)

screen = pyros.gccui.initAll(screen_size, True)


resubscribe = time.time()
lastReceivedTime = time.time()
frameTime = ""

receivedFrameTime = ""

size = (80, 64)


class BlastoffClient:
    def __init__(self):
        self.rover = Rover()
        self.run_log = RunLog(self.rover)
        self.telemetry = TelemetryUtil()

        self.speed = 80

        self.running = False
        self.record = False

        self.runButtons = None
        self.radar = None
        self.heading_component = None

    def connected(self):
        print("Starting agent... ", end="")
        pyros.agent.init(pyros.client, "blastoff-agent.py", optional_files=["../common/rover.py", "../common/challenge_utils.py"])
        print("Done.")

        pyros.subscribe("blastoff/feedback/action", self.handleAction)
        pyros.subscribe("blastoff/feedback/running", self.handleRunning)

        pyros.subscribe("wheel/speed/status", self.rover.handleOdo)
        pyros.subscribe("wheel/deg/status", self.rover.handleWheelOrientation)
        pyros.subscribe("sensor/distance", self.rover.handleRadar)
        pyros.subscribeBinary("sensor/heading/data", self.rover.handleHeading)

    @staticmethod
    def toPILImage(imageBytes):
        pilImage = Image.frombytes("RGB", size, imageBytes)
        return pilImage

    @staticmethod
    def toPyImage(pilImage):
        pyImage = pygame.image.fromstring(pilImage.tobytes("raw"), size, "RGB")
        return pyImage

    def handleAction(self, topic, message, groups):
        self.runButtons.label.setText(message)

    def handleRunning(self, topic, message, groups):
        if message == 'False':
            self._stop()
            self.runButtons.off()
        elif message == 'True':
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
        pyros.publish("blastoff/command", "stop")

    def start(self):
        self.running = True
        self.run_log.reset()
        pyros.publish("blastoff/command", "start blastoff " + str(self.speed))

    def warmup(self):
        pyros.publish("blastoff/command", "start warmup")

    @staticmethod
    def swap(array):
        v = array[0]
        array[0] = array[1]
        array[1] = v

    def draw(self, surface):
        pyros.gccui.drawSmallText("r-toggle record, f - fetch, LEFT/RIGHT-scroll, SPACE-stop, RETURN-start, d-distances, x- clear, camera: u-up, d-down, /-reset",
                                  (8, surface.get_height() - pyros.gccui.smallFont.get_height()))

    def getHeading(self):
        if self.rover.heading is not None:
            return self.rover.getRoverState().heading.heading

        return 0

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


blastoff = BlastoffClient()


def onKeyDown(key):
    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif key == pygame.K_f:
        print("  fetching picture...")
        pyros.publish("camera/raw/fetch", "")
    elif key == pygame.K_w:
        blastoff.warmup()
    elif key == pygame.K_r:
        blastoff.record = not blastoff.record
    elif key == pygame.K_RETURN:
        blastoff.start()
    elif key == pygame.K_SPACE:
        blastoff.stop()


def onKeyUp(key):
    pyros.gcc.handleConnectKeyUp(key)
    return


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

    screens.selectCard("status")

    runButtons = RunButtons(Rect(rect.right - 160, rect.y, 160, 320), uiFactory, blastoff.run_log, blastoff.stop, [("Run", blastoff.start), ("WarmUp", blastoff.warmup)])
    statusComponents.addComponent(runButtons)
    blastoff.runButtons = runButtons

    wheelStatus = WheelsStatus(Rect(rect.x, rect.y, 300, 380), uiFactory, blastoff.getWheelOdoAndStatus, blastoff.getWheelAngleAndStatus)
    statusComponents.addComponent(wheelStatus)

    radar = Radar(Rect(rect.x, wheelStatus.rect.bottom + 10, 300, 300), uiFactory, blastoff.getRadar, 1500, display_delta=True)
    # radar = Radar(Rect(rect.x, rect.y, 300, 300), uiFactory, blastoff.getRadar, 1500, display_delta=True)
    blastoff.radar = radar
    statusComponents.addComponent(blastoff.radar)

    blastoff.heading_component = HeadingComponent(Rect(radar.rect.x, radar.rect.y, radar.rect.width, radar.rect.height + 30), uiFactory, blastoff.getHeading, heading_on, heading_off)
    statusComponents.addComponent(blastoff.heading_component)


pyros.init("over-the-rainbow-#", unique=True, onConnected=blastoff.connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)

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

        uiAdapter.processEvent(event)

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)
    pyros.agent.keepAgents()
    pyros.gccui.background(True)

    blastoff.draw(screen)

    if not blastoff.runButtons.playback:
        state = blastoff.rover.nextState()
        state.calculate()

    uiAdapter.draw(screen)

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()

    now = time.time()
