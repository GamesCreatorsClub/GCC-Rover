
#
# Copyright 2016-2018 Games Creators Club
#
# MIT License
#

import time
import telemetry
import traceback

import numpy

import cv2
import PIL
import PIL.Image
from PIL import ImageDraw

import pyroslib
import pyroslib.logging

from pyroslib.logging import log, LOG_LEVEL_INFO, LOG_LEVEL_DEBUG
from rover import RoverState
from challenge_utils import AgentClass, Action, WaitSensorData, WarmupAction


pyroslib.logging.LOG_LEVEL = LOG_LEVEL_INFO

remotDebug = True

size = (80, 64)


class CameraData:
    def __init__(self):
        self.found = {'red': None, 'blue': None, 'yellow': None, 'green': None}

    def reset(self):
        self.found['red'] = None
        self.found['blue'] = None
        self.found['yellow'] = None
        self.found['green'] = None

    def hasAll(self):
        return self.found['red'] is not None and self.found['blue'] is not None and self.found['yellow'] is not None and self.found['green'] is not None

    def getFound(self):
        return self.found

    def foundAsString(self):
        return " ".join([("" if v is None else str(v)) + ":" + k for k, v in self.found.items()])

    def setData(self, colour, data):
        if not self.hasAll():
            self.found[colour] = data
            for c in self.found:
                if c != colour and self.found[c] == data:
                    self.found[c] = None

    def missingColours(self):
        return ", ".join([p for p in self.found if self.found[p] is None])


class WaitCameraData(Action):
    def __init__(self, rover, parent, next_action):
        super(WaitCameraData, self).__init__(rover)
        self.parent = parent
        self.foundColours = parent.foundColours
        self.next_action = next_action
        self.started_scanning_time = None

    def start(self):
        self.started_scanning_time = time.time()
        self.foundColours.reset()

        pyroslib.publish("camera/raw/fetch", "")
        pyroslib.publish("camera/wheels/raw/fetch", "")
        pyroslib.publish("camera/camera1/raw/fetch", "")
        pyroslib.publish("camera/camera2/raw/fetch", "")
        log(LOG_LEVEL_INFO, "Started a wait for all camera data to arrive...")

    def next(self):
        if self.foundColours.hasAll():
            log(LOG_LEVEL_INFO, "Scanning lasted " + ("{:7.3f}".format(time.time() - self.started_scanning_time)) + "!")
            log(LOG_LEVEL_INFO, "Received all colours " + ("stopping" if self.next_action is None else "starting action " + str(self.next_action.getActionName())))
            return self.next_action
        return self

    def execute(self):
        log(LOG_LEVEL_INFO, "Waiting for sensor data to arrive...")

    def getActionName(self):
        return "Scan"


class NebulaAgent(AgentClass):
    def __init__(self):
        super(NebulaAgent, self).__init__("nebula")
        self.foundColours = CameraData()

    def connected(self):
        super(NebulaAgent, self).connected()

        pyroslib.subscribeBinary("camera/raw", self.handleCameraMain)
        pyroslib.subscribeBinary("camera/wheels/raw", self.handleCameraWheels)
        pyroslib.subscribeBinary("camera/camera1/raw", self.handleCamera1)
        pyroslib.subscribeBinary("camera/camera2/raw", self.handleCamera2)

        pyroslib.publish("camera/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")
        pyroslib.publish("camera/wheels/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")
        pyroslib.publish("camera/camera1/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")
        pyroslib.publish("camera/camera2/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")

    def start(self, data):
        if not self.running:
            pyroslib.publish("canyons/feedback/running", "True")

            if data[0] == 'nebula':
                self.running = True
                speed = int(data[1])
                distance = int(data[2])
                speed = 140
            elif data[0] == 'warmup':
                self.running = True
                self.nextAction(WaitSensorData(self.rover, WarmupAction(self.rover)))

            elif data[0] == 'scan':
                self.running = True
                self.nextAction(WaitCameraData(self.rover, self, self.stop_action))

    def handleCameraData(self, topic, message, source):
        # now = time.time()
        # delta = now - lastProcessed
        # lastProcessed = now

        pilImage = self._toPILImage(message)
        openCVImage = numpy.array(pilImage)

        result, value = self.processImageCV(openCVImage)

        log(LOG_LEVEL_INFO, "For " + str(source) + " got " + ("None" if result is None else str(result)) + " for value " + str(value))

        if result is not None:
            self.foundColours.setData(result, source)

        if not self.foundColours.hasAll():
            log(LOG_LEVEL_INFO, "Found " + self.foundColours.foundAsString() + " but not finished yet as " + self.foundColours.missingColours() + " " + ("are" if len(self.foundColours.missingColours()) > 1 else "is") + " still missing.")
            if self.running:
                pyroslib.publish(topic + "/fetch", "")
            pyroslib.publish("nebula/imagedetails", "working: " + self.foundColours.foundAsString())
        else:
            log(LOG_LEVEL_INFO, "So far " + self.foundColours.foundAsString() + " and finishing...")
            stopped = True
            pyroslib.publish("nebula/imagedetails", "found: " + self.foundColours.foundAsString())

    def handleCameraMain(self, topic, message, groups):
        self.handleCameraData(topic, message, 225)

    def handleCameraWheels(self, topic, message, groups):
        self.handleCameraData(topic, message, 45)

    def handleCamera1(self, topic, message, groups):
        self.handleCameraData(topic, message, 315)

    def handleCamera2(self, topic, message, groups):
        self.handleCameraData(topic, message, 135)

    @staticmethod
    def _toPILImage(imageBytes):
        pilImage = PIL.Image.frombytes("RGB", size, imageBytes)
        return pilImage

    @staticmethod
    def processImageCV(image):
        def findColourNameHSV(hChannel, contour):

            mask = numpy.zeros(hChannel.shape[:2], dtype="uint8")
            cv2.drawContours(mask, [contour], -1, 255, -1)
            mask = cv2.erode(mask, None, iterations=2)

            maskAnd = hChannel.copy()
            cv2.bitwise_and(hChannel, mask, maskAnd)

            pyroslib.publish("nebula/processed", PIL.Image.fromarray(cv2.cvtColor(maskAnd, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
            log(LOG_LEVEL_DEBUG, "Published mask ")

            hist = cv2.calcHist([hChannel], [0], mask, [255], [0, 255], False)

            value = numpy.argmax(hist)

            if value < 19 or value > 145:
                return "red", value
            elif 19 <= value <= 34:
                return "yellow", value
            elif 40 <= value <= 76:
                return "green", value
            elif 90 <= value <= 138:
                return "blue", value
            else:
                return None, value

        blurred = cv2.GaussianBlur(image, (5, 5), 0)

        hsv = cv2.cvtColor(blurred, cv2.COLOR_RGB2HSV)
        hueChannel, satChannel, valChannel = cv2.split(hsv)

        countours = [numpy.array([[25, 20], [55, 20], [55, 44], [25, 44]], dtype=numpy.int32)]
        c = countours[0]
        result, value = findColourNameHSV(hueChannel, c)

        if result is not None:

            def sendResult(colour):
                # pil = PIL.Image.fromarray(cv2.cvtColor(hueChannel, cv2.COLOR_GRAY2RGB))
                pil = PIL.Image.fromarray(image)

                draw = ImageDraw.Draw(pil)
                draw.rectangle(((25, 20), (55, 44)), outline=colour)
                pyroslib.publish("nebula/processed", pil.tobytes("raw"))

            if result == "red":
                sendResult("#f00")
                log(LOG_LEVEL_DEBUG, "Published hue red image")
            elif result == "yellow":
                sendResult("#ff0")
                log(LOG_LEVEL_DEBUG, "Published hue yellow image")
            elif result == "green":
                sendResult("#0f0")
                log(LOG_LEVEL_DEBUG, "Published hue green image")
            elif result == "blue":
                sendResult("#00f")
                log(LOG_LEVEL_DEBUG, "Published hue blue image")
        else:
            cv2.drawContours(hueChannel, countours, -1, (255, 255, 255), 2)

            pyroslib.publish("nebula/processed", PIL.Image.fromarray(cv2.cvtColor(hueChannel, cv2.COLOR_GRAY2RGB)).tobytes("raw"))
            log(LOG_LEVEL_DEBUG, "Published unrecognised hue image")

        return result, value


if __name__ == "__main__":
    try:
        print("Starting Nebula agent...")

        print("  creating logger...")
        state_logger = RoverState.defineLogger(telemetry.MQTTLocalPipeTelemetryLogger('rover-state'))

        nebula = NebulaAgent()

        pyroslib.init("nebula-agent", unique=True, onConnected=nebula.connected)

        print("  initialising logger...")
        state_logger.init()

        nebula.register_logger()
        print("Started Nebula agent.")

        pyroslib.forever(0.1, nebula.mainLoop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
