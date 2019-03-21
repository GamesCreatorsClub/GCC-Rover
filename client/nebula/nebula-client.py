
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


class NebulaClient:
    def __init__(self):
        self.rover = Rover()
        self.run_log = RunLog(self.rover)
        self.telemetry = TelemetryUtil()

        self.found = {'45': None, '135': None, '225': None, '315': None}
        self.speed = 80

        self.rawImage = pygame.Surface((80, 64), 24)
        self.rawImageBig = pygame.Surface((320, 256), 24)

        self.completeRawImage = None
        self.lastImage = None

        self.processedImages = []
        self.processedBigImages = []
        self.imgNo = 0
        self.ptr = -1
        self.selected = ""

        self.running = False
        self.record = False
        self.found_colours = False
        self.started_scanning_time = None
        self.scan_time = "-"

        self.runButtons = None
        self.radar = None
        self.heading_component = None
        self.preview_image = None
        self.preview_image_small = None
        self.result_preview = None

    def connected(self):
        print("Starting agent... ", end="")
        pyros.agent.init(pyros.client, "nebula-agent.py", optional_files=["../common/rover.py", "../common/challenge_utils.py"])
        print("Done.")

        pyros.subscribeBinary("nebula/processed", self.handleCameraRaw)
        pyros.subscribe("nebula/imagedetails", self.handleResults)
        pyros.subscribe("nebula/feedback/action", self.handleAction)
        pyros.subscribe("nebula/feedback/running", self.handleRunning)

        pyros.subscribeBinary("camera/raw", self.handleCameraRaw)
        pyros.subscribeBinary("camera/wheels/raw", self.handleCameraWheelsRaw)
        pyros.subscribeBinary("camera/camera1/raw", self.handleCamera1Raw)
        pyros.subscribeBinary("camera/camera2/raw", self.handleCamera2Raw)

        pyros.subscribe("wheel/speed/status", self.rover.handleOdo)
        pyros.subscribe("wheel/deg/status", self.rover.handleWheelOrientation)
        pyros.subscribe("sensor/distance", self.rover.handleRadar)
        pyros.subscribeBinary("sensor/heading/data", self.rover.handleHeading)

        # pyros.subscribe("overtherainbow/distances", handleDistances)
        # pyros.subscribe("overtherainbow/imagedetails", handleImageDetails)
        # pyros.subscribeBinary("overtherainbow/processed", handleCameraProcessed)

    @staticmethod
    def toPILImage(imageBytes):
        pilImage = Image.frombytes("RGB", size, imageBytes)
        return pilImage

    @staticmethod
    def toPyImage(pilImage):
        pyImage = pygame.image.fromstring(pilImage.tobytes("raw"), size, "RGB")
        return pyImage

    def handleCameraRaw(self, topic, message, groups):
        self.handleCameraProcessed(topic, message, groups)
        self.completeRawImage = self.lastImage

    def handleCameraWheelsRaw(self, topic, message, groups):
        self.handleCameraProcessed(topic, message, groups)
        self.completeRawImage = self.lastImage

    def handleCamera1Raw(self, topic, message, groups):
        self.handleCameraProcessed(topic, message, groups)
        self.completeRawImage = self.lastImage

    def handleCamera2Raw(self, topic, message, groups):
        self.handleCameraProcessed(topic, message, groups)
        self.completeRawImage = self.lastImage

    def handleCameraProcessed(self, topic, message, groups):

        pilImage = self.toPILImage(message)

        image = self.toPyImage(pilImage)
        self.lastImage = image

        self.rawImage = pygame.transform.scale(self.lastImage, (80, 64))
        self.rawImageBig = pygame.transform.scale(self.lastImage, (320, 256))

        self.preview_image.setImage(self.rawImageBig)
        self.preview_image_small.setImage(self.rawImage)

        if self.record:
            self.processedImages.append(self.rawImage)
            self.processedBigImages.append(self.rawImageBig)
            self.updateSelected()

    def handleResults(self, topic, message, groups):
        # print("Received " + str(message))
        split = message.split(" ")
        if split[0] == "found:":
            self.found_colours = True
            self.scan_time = "{:7.3f}".format(time.time() - self.started_scanning_time)

        del split[0]
        for s in split:
            kv = s.split(":")
            self.found[kv[0]] = kv[1]

        # print("Found now: " + str(self.found))

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
        pyros.publish("nebula/command", "stop")

    def clear(self):
        self.imgNo = 0
        del self.processedImages[:]
        del self.processedBigImages[:]
        self.updateSelected()
        self.found_colours = False
        for p in self.found:
            self.found[p] = None

    def scan(self):
        self.clear()
        pyros.publish("nebula/command", "start scan")
        self.started_scanning_time = time.time()
        self.scan_time = "-"

    def corner(self):
        self.clear()
        pyros.publish("nebula/command", "start corner")
        self.started_scanning_time = time.time()
        self.scan_time = "-"

    def warmup(self):
        pyros.publish("nebula/command", "start warmup")

    def start(self):
        self.running = True
        self.clear()
        pyros.publish("nebula/command", "start nebula " + str(self.speed))
        self.started_scanning_time = time.time()
        self.scan_time = "-"

    def updateSelected(self):
        self.selected = str(self.ptr) + " of " + str(len(self.processedImages))

    @staticmethod
    def swap(array):
        v = array[0]
        array[0] = array[1]
        array[1] = v

    def draw(self, surface):
        # noinspection PyRedeclaration
        # hpos = 40
        # hpos = pyros.gccui.drawKeyValue("Recording", str(self.record), 8, hpos)
        # hpos = pyros.gccui.drawKeyValue("Selected", str(self.ptr) + " of " + str(len(self.processedImages)), 8, hpos)
        # hpos = pyros.gccui.drawKeyValue("Running", str(self.running), 8, hpos)
        # hpos = pyros.gccui.drawKeyValue("Scan time", "{:7.3f}".format(self.scan_time) if self.scan_time is not None else "-", 8, hpos)

        pyros.gccui.drawSmallText("r-toggle record, f - fetch, s-scan, LEFT/RIGHT-scroll, SPACE-stop, RETURN-start, d-distances, x- clear, camera: u-up, d-down, /-reset",
                                  (8, surface.get_height() - pyros.gccui.smallFont.get_height()))

        # pyros.gccui.drawImage(self.rawImage, (500, 50), 10)
        # pyros.gccui.drawImage(self.rawImageBig, (688, 50), 10)

        if self.ptr >= 0:
            if self.ptr > len(self.processedImages) - 1:
                self.ptr = len(self.processedImages) - 1
            i = self.ptr
        else:
            i = len(self.processedImages) - 1

        imgX = 1024 - 320 - 16
        while i >= 0 and imgX >= 0:
            pyros.gccui.drawImage(self.processedBigImages[i], (imgX, 420))
            imgX -= 336
            i -= 1

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


class NebulaComponent(gccui.Component):
    def __init__(self, rect, found):
        super(NebulaComponent, self).__init__(rect)
        self.found = found
        self.border = Border(rect)

    def redefineRect(self, rect):
        super(NebulaComponent, self).redefineRect(rect)
        self.border.redefineRect(rect)

    def draw(self, surface):
        pygame.draw.rect(surface, (0, 0, 0), self.rect)

        self.border.draw(surface)

        pygame.draw.rect(surface, (255, 0, 0), Rect(self.rect.x + int(self.rect.width // 2 - 3), self.rect.top - 6, 6, 6))

        pygame.draw.polygon(surface, self.stringToColour(self.found['45']), ((self.rect.right, self.rect.top), (self.rect.right - 20, self.rect.top), (self.rect.right, self.rect.top + 20)))
        pygame.draw.polygon(surface, self.stringToColour(self.found['135']), ((self.rect.right, self.rect.bottom), (self.rect.right - 20, self.rect.bottom), (self.rect.right, self.rect.bottom - 20)))
        pygame.draw.polygon(surface, self.stringToColour(self.found['225']), ((self.rect.left, self.rect.bottom), (self.rect.left + 20, self.rect.bottom), (self.rect.left, self.rect.bottom - 20)))
        pygame.draw.polygon(surface, self.stringToColour(self.found['315']), ((self.rect.left, self.rect.top), (self.rect.left + 20, self.rect.top), (self.rect.left, self.rect.top + 20)))

    @staticmethod
    def stringToColour(s):
        if s is None:
            return 96, 96, 96
        elif s == "red":
            return 255, 0, 0
        elif s == "yellow":
            return 255, 255, 0
        elif s == "green":
            return 0, 255, 0
        elif s == "blue":
            return 0, 0, 255
        else:
            return 255, 0, 255


nebula = NebulaClient()


def onKeyDown(key):
    if pyros.gcc.handleConnectKeyDown(key):
        pass
    elif key == pygame.K_f:
        print("  fetching picture...")
        pyros.publish("camera/raw/fetch", "")
    elif key == pygame.K_s:
        nebula.scan()
    elif key == pygame.K_w:
        nebula.warmup()
    elif key == pygame.K_c:
        nebula.corner()
    elif key == pygame.K_r:
        nebula.record = not nebula.record
    elif key == pygame.K_x:
        nebula.clear()
    elif key == pygame.K_1:
        pyros.publish("camera/wheels/raw/fetch", "")
    elif key == pygame.K_2:
        pyros.publish("camera/camera2/raw/fetch", "")
    elif key == pygame.K_3:
        pyros.publish("camera/raw/fetch", "")
    elif key == pygame.K_4:
        pyros.publish("camera/camera1/raw/fetch", "")
    elif key == pygame.K_RETURN:
        nebula.start()
    elif key == pygame.K_SPACE:
        nebula.stop()
    elif key == pygame.K_LEFT:
        if nebula.ptr == -1:
            nebula.ptr = len(nebula.processedImages) - 2
        else:
            nebula.ptr -= 1
        nebula.updateSelected()
    elif key == pygame.K_RIGHT:
        nebula.ptr += 1
        if nebula.ptr >= len(nebula.processedImages) - 1:
            nebula.ptr = -1
        nebula.updateSelected()


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

    runButtons = RunButtons(Rect(rect.right - 160, rect.y, 160, 280), uiFactory, nebula.run_log, nebula.stop, [("Run", nebula.start), ("WarmUp", nebula.warmup), ("Scan", nebula.scan), ("Corner", nebula.corner)])
    statusComponents.addComponent(runButtons)
    nebula.runButtons = runButtons

    # wheelStatus = WheelsStatus(Rect(rect.x, rect.y, 300, 380), uiFactory, nebula.getWheelOdoAndStatus, nebula.getWheelAngleAndStatus)
    # statusComponents.addComponent(wheelStatus)
    #
    # radar = Radar(Rect(rect.x, wheelStatus.rect.bottom + 10, 300, 300), uiFactory, nebula.getRadar, 1500, display_delta=True)
    radar = Radar(Rect(rect.x, rect.y, 300, 300), uiFactory, nebula.getRadar, 1500, display_delta=True)
    nebula.radar = radar
    statusComponents.addComponent(nebula.radar)

    preview_image = BorderImage(Rect(runButtons.rect.x - 360, runButtons.rect.y + 50, 320, 256), nebula.rawImageBig)
    nebula.preview_image = preview_image
    statusComponents.addComponent(preview_image)

    preview_image_small = BorderImage(Rect(preview_image.rect.x - 110, preview_image.rect.y, 80, 64), nebula.rawImage)
    nebula.preview_image_small = preview_image_small
    statusComponents.addComponent(preview_image_small)

    result_preview = NebulaComponent(Rect(preview_image_small.rect.x, preview_image_small.rect.bottom + 20, 80, 80), nebula.found)
    nebula.result_preview = result_preview
    statusComponents.addComponent(result_preview)

    nebula.heading_component = HeadingComponent(Rect(radar.rect.x, radar.rect.y, radar.rect.width, radar.rect.height + 30), uiFactory, nebula.getHeading, heading_on, heading_off)
    statusComponents.addComponent(nebula.heading_component)

    nebula.recording_label = ReflectonValueWithLabel(Rect(preview_image.rect.x, preview_image.rect.bottom + 5, 80, 16), "Recording: ", "{0}", nebula, "running", font=uiFactory.font)
    nebula.selected_label = ReflectonValueWithLabel(Rect(preview_image.rect.x, preview_image.rect.top - 40, 80, 16), "Selected: ", "{:26s}", nebula, "selected", font=uiFactory.font)
    nebula.scan_time_label = ReflectonValueWithLabel(Rect(result_preview.rect.x, result_preview.rect.bottom + 5, result_preview.rect.width, 16), "", "{0}", nebula, "scan_time", h_alignment=gccui.ALIGNMENT.CENTER, font=uiFactory.font)
    # nebula.scan_time_label = ReflectonValueWithLabel(Rect(450, result_preview.rect.bottom + 5, 100, 16), "", "{:26s}", nebula, "scan_time", h_alignment=gccui.ALIGNMENT.CENTER, font=uiFactory.font)
    statusComponents.addComponent(nebula.recording_label)
    statusComponents.addComponent(nebula.selected_label)
    statusComponents.addComponent(nebula.scan_time_label)

    # statusComponents.addComponent(Border(Rect(result_preview.rect.x, result_preview.rect.bottom + 5, result_preview.rect.width, 16)))


pyros.init("over-the-rainbow-#", unique=True, onConnected=nebula.connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)

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

    nebula.draw(screen)

    if not nebula.runButtons.playback:
        state = nebula.rover.nextState()
        state.calculate()

    uiAdapter.draw(screen)

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()

    now = time.time()
