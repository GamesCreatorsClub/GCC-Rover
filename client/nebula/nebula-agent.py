
#
# Copyright 2016-2018 Games Creators Club
#
# MIT License
#

import math
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

from pyroslib.logging import log, LOG_LEVEL_INFO, LOG_LEVEL_DEBUG, LOG_LEVEL_ALWAYS
from rover import RoverState, normaiseAngle, angleDiference
from challenge_utils import AgentClass, Action, WaitSensorData, WarmupAction, PID

MINIMUM_SPEED = 60
MIN_ANGLE = 1

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

        pyroslib.publish("camera/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")
        pyroslib.publish("camera/wheels/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")
        pyroslib.publish("camera/camera1/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")
        pyroslib.publish("camera/camera2/format", "RGB " + str(size[0]) + "," + str(size[1]) + " False")

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


class NebulaAction(Action):
    def __init__(self, rover, speed, next_action):
        super(NebulaAction, self).__init__(rover)
        self.speed = speed
        self.next_action = next_action

        self.direction_pid = PID(0.75, 0.2, 0.01, 1, 0)
        self.heading_pid = PID(0.3, 0, 0.01, 1, 0, diff_method=angleDiference)
        self.distance_pid = PID(0.75, 0.2, 0.01, 1, 0)

        self.distance_error = 0
        self.rover_speed = 0

        self.required_corner_distance = 190
        self.required_side_distance = 150
        self.required_keeping_side_distance = 150

    def obtainRoverSpeed(self):
        self.rover_speed = self.rover.wheel_odos.averageSpeed() / 10
        self.rover_speed = 25

    def keepHeading(self):
        state = self.rover.getRoverState()

        # Keeping heading
        heading = state.heading.heading
        heading_output = -self.heading_pid.process(0, heading)
        if -MIN_ANGLE < heading_output < MIN_ANGLE:
            distance = 32000
        else:
            heading_fix_rad = heading_output * math.pi / 180
            distance = self.rover_speed / heading_fix_rad
            if 0 <= distance < 150:
                distance = 150
            elif -150 < distance < 0:
                distance = -150

        return distance, heading_output

    def keepDirection(self, requested_angle, setpoint_distance, current_distance):
        state = self.rover.getRoverState()

        # Keeping direction
        angle_output = self.direction_pid.process(setpoint_distance, current_distance)
        angle = 0
        if abs(angle_output) < 10:
            angle = 0
        elif angle_output > 0 and angle_output > self.rover_speed:
            angle = math.pi / 4
        elif angle_output < 0 and angle_output < -self.rover_speed:
            angle = -math.pi / 4
        else:
            try:
                angle = math.asin(angle_output / self.rover_speed)
            except BaseException as ex:
                log(LOG_LEVEL_ALWAYS, "Domain error")
        angle = int(requested_angle + angle * 180 / math.pi)

        return angle, angle_output

    def calculateSpeed(self):
        # Defining forward speed
        if self.distance_error <= 0:
            speed = -self.distance_error
            if speed > self.speed:
                speed = self.speed
            elif speed < MINIMUM_SPEED:
                speed = MINIMUM_SPEED
        else:
            speed = -self.distance_error
            if speed > -MINIMUM_SPEED:
                speed = -MINIMUM_SPEED
            elif speed < -self.speed:
                speed = -self.speed

        return speed

    def start(self):
        super(NebulaAction, self).start()
        # self.distance_pid = PID(0.75, 0.0, 0.1, 1, 0)
        # self.direction_pid = PID(0.20, 0.02, 0.005, 1, 0)
        # self.heading_pid = PID(0.25, 0.0, 0.01, 1, 0, diff_method=angleDiference)
        self.distance_pid = PID(0.75, 0.1, 0.1, 1, 0)
        self.direction_pid = PID(0.20, 0.02, 0.005, 1, 0)
        self.heading_pid = PID(0.25, 0.0, 0.01, 1, 0, diff_method=angleDiference)

    def end(self):
        super(NebulaAction, self).end()


class GoToCornerKeepingHeadingAction(NebulaAction):
    def __init__(self, rover, speed, angle, next_action=None):
        super(GoToCornerKeepingHeadingAction, self).__init__(rover, speed, next_action)
        self.angle = angle

        self.prev_angle = angle - 45
        self.next_angle = angle + 45
        if self.prev_angle < 0:
            self.prev_angle += 360
        if self.next_angle >= 360:
            self.next_angle -= 360

    def start(self):
        super(GoToCornerKeepingHeadingAction, self).start()
        log(LOG_LEVEL_INFO, "Starting Corner with prev_angle={: 3d} angle={: 3d} next_angle={: 3d}".format(self.prev_angle, self.angle, self.next_angle))

    def next(self):
        state = self.rover.getRoverState()
        self.obtainRoverSpeed()

        corner_distance = state.radar.radar[self.angle]
        self.distance_error = self.distance_pid.process(self.required_corner_distance, corner_distance)

        if corner_distance < self.required_corner_distance:
            return self.next_action

        left_side = state.radar.radar[self.prev_angle]
        right_side = state.radar.radar[self.next_angle]
        average_side = int((left_side + right_side) / 2)

        if average_side < self.required_side_distance:
            return self.next_action

        return self

    def execute(self):
        state = self.rover.getRoverState()

        distance, heading_output = self.keepHeading()

        left_side = state.radar.radar[self.prev_angle]
        right_side = state.radar.radar[self.next_angle]
        angle, angle_output = self.keepDirection(self.angle, right_side, left_side)

        if self.distance_error > 400:
            angle = self.angle

        speed = self.calculateSpeed()

        corner_distance = state.radar.radar[self.angle]

        log(LOG_LEVEL_INFO, "{:16.3f}: rover_speed={: 4d} corner_dist={: 4d} dist_error={: 7.2f} left_dist={: 4d} right_dist={: 4d} angle_fix={: 7.2f} heading={: 3d} heading_fix={: 7.2f} speed={: 3d} angle={: 3d} distance={: 3d}".format(
                            float(time.time()),
                            int(self.rover_speed),
                            int(corner_distance), self.distance_error,
                            int(left_side), int(right_side), angle_output,
                            int(state.heading.heading), heading_output,
                            int(speed), int(angle), int(distance)))

        # distance = 32000

        self.rover.command(pyroslib.publish, speed, angle, distance)

    def getActionName(self):
        return "Corner[{:3d}]".format(self.angle)


class FollowWallKeepingHeadingAction(NebulaAction):
    def __init__(self, rover, speed, wall_angle, direction_angle, next_action=None):
        super(FollowWallKeepingHeadingAction, self).__init__(rover, speed, next_action)
        self.wall_angle = wall_angle
        self.direction_angle = direction_angle

    def next(self):
        state = self.rover.getRoverState()
        self.obtainRoverSpeed()

        wall_distance = state.radar.radar[self.wall_angle]
        front_distance = state.radar.radar[self.direction_angle]

        self.distance_error = self.distance_pid.process(self.required_side_distance, front_distance)

        if front_distance < self.required_side_distance:
            return self.next_action

        return self

    def execute(self):
        state = self.rover.getRoverState()

        distance, heading_output = self.keepHeading()

        wall_distance = state.radar.radar[self.wall_angle]
        if angleDiference(self.wall_angle, self.direction_angle) > 0:
            angle, angle_output = self.keepDirection(self.direction_angle, wall_distance, self.required_keeping_side_distance)
        else:
            angle, angle_output = self.keepDirection(self.direction_angle, self.required_keeping_side_distance, wall_distance)
            # angle, angle_output = self.keepDirection(self.direction_angle, wall_distance, self.required_keeping_side_distance)

        speed = self.calculateSpeed()

        front_distance = state.radar.radar[self.direction_angle]

        log(LOG_LEVEL_INFO, "{:16.3f}: rover_speed={: 4d} front_dist={: 4d} dist_error={: 7.2f} wall_dist={: 4d} angle_fix={: 7.2f} heading={: 3d} heading_fix={: 7.2f} speed={: 3d} angle={: 3d} distance={: 3d}".format(
                            float(time.time()),
                            int(self.rover_speed),
                            int(front_distance), self.distance_error,
                            int(wall_distance), angle_output,
                            int(state.heading.heading), heading_output,
                            int(speed), int(angle), int(distance)))

        self.rover.command(pyroslib.publish, speed, angle, distance)

    def getActionName(self):
        return "Wall[{0} on {1}]".format(self.direction_angle, self.wall_angle)


class CalculateRouteAction(Action):
    def __init__(self, rover, speed, foundColours, next_action):
        super(CalculateRouteAction, self).__init__(rover)
        self.speed = speed
        self.foundColours = foundColours
        self.next_action = next_action
        self.colour_order = ['red', 'blue', 'yellow', 'green']
        log(LOG_LEVEL_INFO, "Colour order " + str(self.colour_order))
        self.wait = 0
        self.prepared_action = None

    def calcualteAction(self, from_angle, to_colour):
        to_angle = self.foundColours.found[to_colour]
        colour_index = self.colour_order.index(to_colour)

        if colour_index < 3:
            following_action = self.calcualteAction(to_angle, self.colour_order[colour_index + 1])
        else:
            following_action = self.next_action

        if normaiseAngle(from_angle + 90) == to_angle:
            wall_angle = normaiseAngle(from_angle + 45)
            direction_angle = normaiseAngle(wall_angle + 90)
            # return FollowWallKeepingHeadingAction(self.rover, self.speed, wall_angle, direction_angle, following_action)
            return FollowWallKeepingHeadingAction(self.rover, 160, wall_angle, direction_angle, following_action)
        elif normaiseAngle(from_angle - 90) == to_angle:
            wall_angle = normaiseAngle(from_angle - 45)
            direction_angle = normaiseAngle(wall_angle - 90)
            # return FollowWallKeepingHeadingAction(self.rover, self.speed, wall_angle, direction_angle, following_action)
            return FollowWallKeepingHeadingAction(self.rover, 160, wall_angle, direction_angle, following_action)
        else:
            # return GoToCornerKeepingHeadingAction(self.rover, self.speed, to_angle, following_action)
            return GoToCornerKeepingHeadingAction(self.rover, 220, to_angle, following_action)

    def next(self):
        if self.wait == 0:
            log(LOG_LEVEL_INFO, "Calculating route (1) -> Corner " + str(self.foundColours.found['red']))

            initial_angle = self.foundColours.found['red']
            following_action = self.calcualteAction(initial_angle, 'blue')

            i = 1
            a = following_action
            while a != self.next_action:
                i += 1
                if isinstance(a, GoToCornerKeepingHeadingAction):
                    log(LOG_LEVEL_INFO, "Calculating route (" + str(i) + ") -> Corner " + str(a.angle))
                    a = a.next_action
                else:
                    log(LOG_LEVEL_INFO, "Calculating route (" + str(i) + ") -> Follow wall " + str(a.wall_angle) + " to  " + str(a.direction_angle))
                    a = a.next_action

            self.prepared_action = GoToCornerKeepingHeadingAction(self.rover, self.speed, initial_angle, following_action)
            self.wait = 5
            self.rover.command(pyroslib.publish, 0, initial_angle, 32000)
            log(LOG_LEVEL_INFO, "Wheels orientation {0} wait:{1:2d}".format(str(self.rover.current_state.wheel_orientations.orientations), self.wait))
        else:
            log(LOG_LEVEL_INFO, "Wheels orientation {0} wait:{1:2d}".format(str(self.rover.current_state.wheel_orientations.orientations), self.wait))
            self.wait -= 1
            if self.wait == 0:
                return self.prepared_action

        return self

    def getActionName(self):
        return "Calculate"


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
                # speed = int(data[1])

                speed = 160
                speed = 200

                calculate_route_action = CalculateRouteAction(self.rover, speed, self.foundColours, self.stop_action)
                wait_camera_data_action = WaitCameraData(self.rover, self, calculate_route_action)
                wait_sensor_data_action = WaitSensorData(self.rover, wait_camera_data_action)
                self.nextAction(wait_sensor_data_action)

            elif data[0] == 'warmup':
                self.running = True
                self.nextAction(WaitSensorData(self.rover, WarmupAction(self.rover)))

            elif data[0] == 'scan':
                self.running = True
                self.nextAction(WaitCameraData(self.rover, self, self.stop_action))

            elif data[0] == 'corner':
                self.running = True

                follow_wall_action = FollowWallKeepingHeadingAction(self.rover, 80, 270, 0, self.stop_action)
                go_to_corner_action = GoToCornerKeepingHeadingAction(self.rover, 80, 225, follow_wall_action)
                # wait_camera_data_action = WaitCameraData(self.rover, self, go_to_corner_action)
                wait_sensor_data_action = WaitSensorData(self.rover, go_to_corner_action)
                self.nextAction(wait_sensor_data_action)

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
