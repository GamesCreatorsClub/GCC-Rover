
#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import math
import traceback

import pyroslib
import pyroslib.logging

from pyroslib.logging import LOG_LEVEL_INFO
from rover import Rover
from maze import MazeAction, MazeCorridorAction, MazeTurnAroundCornerAction
from challenge_utils import AgentClass, WaitSensorData


SQRT2 = math.sqrt(2)

WHEEL_CIRCUMFERENCE = 68 * math.pi
WHEEL_NAMES = ['fl', 'fr', 'bl', 'br']

pyroslib.logging.LOG_LEVEL = LOG_LEVEL_INFO

corridor_logger = None


def angleDiference(a1, a2):
    diff = a1 - a2
    if diff >= 180:
        return diff - 360
    elif diff <= -180:
        return diff + 360
    return diff


def normaiseAngle(a):
    a = a % 360
    if a < 0:
        a += 360
    return a


class Odo:
    def __init__(self):
        self.odo = {'fl': 0, 'fr': 0, 'bl': 0, 'br': 0}
        self.last_odo = {'fl': 0, 'fr': 0, 'bl': 0, 'br': 0}
        self.wheel_speeds = {'fl': 0, 'fr': 0, 'bl': 0, 'br': 0}
        self.last_odo_data = 0
        self.odo_delta_time = 0

        self.wheel_orientation = {'fl': 0, 'fr': 0, 'bl': 0, 'br': 0, 'timestamp': 0.0}
        self.last_wheel_orientation = {'fl': 0, 'fr': 0, 'bl': 0, 'br': 0, 'timestamp': 0.0}
        self.wheel_rot_speeds = {'fl': 0, 'fr': 0, 'bl': 0, 'br': 0}
        self.last_speed_data = 0
        self.speed_delta_time = 0

    @staticmethod
    def deltaOdo(old, new):
        d = new - old
        if d > 32768:
            d -= 32768
        elif d < -32768:
            d += 32768

        return d

    @staticmethod
    def deltaOdoInmm(old, new):
        d = new - old
        if d > 32768:
            d -= 32768
        elif d < -32768:
            d += 32768

        return d * WHEEL_CIRCUMFERENCE / 4096

    def wheelOdos(self):
        return self.odo

    def wheelOdoInmm(self, wheel_name):
        return self.odo[wheel_name] * WHEEL_CIRCUMFERENCE / 4096

    def wheelSpeedInmmPs(self, wheel_name):
        return self.wheel_speeds[wheel_name] * WHEEL_CIRCUMFERENCE / 4096

    def wheelSpeeds(self):
        return self.wheel_speeds

    def wheelSpeedAndDirection(self):
        def addAngles(v1, v2):
            t = (v1[1] + 180 - v2[1]) * math.pi / 180
            m = math.sqrt(v1[0] * v1[0] + v2[0] * v2[0] - 2 * v1[0] * v1[0] * math.cos(t))
            if m < 0.00001:
                return 0, 0

            a = math.asin(v2[0] * math.sin(t) / m)
            return m, a * 180 / math.pi

        if self.odo_delta_time == 0:
            return 0
        total = (0, 0)
        for wheel in WHEEL_NAMES:
            distance = self.odo[wheel] - self.last_odo[wheel]
            total = addAngles(total, (distance, self.wheel_orientation[wheel]))

        return total[0] / (4 * self.odo_delta_time), total[1]

    def wheelOrietations(self):
        return self.wheel_orientation

    def wheelOrientationalSpeed(self):
        return self.wheel_rot_speeds

    def processSpeed(self, data):
        t = float(data[0])

        if t - self.last_odo_data < 1:
            self.odo_delta_time = t - self.last_odo_data
        else:
            self.odo_delta_time = 100000000

        self.last_odo_data = t

        for i in range(4):
            data_index = i * 2
            if data[data_index + 2] == "0":
                new_odo = int(data[data_index + 1])
                delta_odo = self.deltaOdo(self.last_odo[WHEEL_NAMES[i]], new_odo)
                self.last_odo[WHEEL_NAMES[i]] = self.odo[WHEEL_NAMES[i]]
                self.odo[WHEEL_NAMES[i]] = new_odo
                self.wheel_speeds[WHEEL_NAMES[i]] = delta_odo

    def processOrientation(self, data):
        # def deltaDeg(old, new):
        #     d = (int(new) - int(old)) % 360
        #     if d < 0:
        #         d += 360
        #     return d

        self.wheel_orientation['timestamp'] = float(data[0])

        for i in range(4):
            data_index = i * 2
            if data[data_index + 2] == "32":
                new_deg = int(data[data_index + 1])
                self.last_wheel_orientation[WHEEL_NAMES[i]] = self.wheel_orientation[WHEEL_NAMES[i]]
                self.wheel_orientation[WHEEL_NAMES[i]] = new_deg


class CanyonsOfMarsAgent(AgentClass):
    def __init__(self):
        super(CanyonsOfMarsAgent, self).__init__("canyons")
        self.running = False
        self.rover = Rover()
        self.last_execution_time = 0

    def stop(self):
        self.running = False
        self.rover.reset()
        self.nextAction(self.stop_action)
        pyroslib.publish("position/heading/stop", '')
        pyroslib.publish("position/pause", "")
        pyroslib.publish("sensor/distance/pause", "")

    def start(self, data):
        if not self.running:
            pyroslib.publish("canyons/feedback/running", "True")

            if data[0] == 'corridor':
                self.running = True
                speed = int(data[1])
                distance = int(data[2])
                speed = 140

                # drive_forward_action = DriverForwardForTimeActoun(5, speed, self.stop_action)
                # corner_action = MazeTurnAroundCornerAction(self.odo, self.radar, self.heading, MazeAction.LEFT, distance, speed,next_action=drive_forward_action)
                corridor_action = MazeCorridorAction(self.rover, MazeAction.RIGHT, distance, speed)
                wait_for_heading_action = WaitSensorData(self.rover, corridor_action)

                self.nextAction(wait_for_heading_action)
            elif data[0] == 'turnCorner':
                self.running = True
                speed = int(data[1])
                distance = int(data[2])

                self.nextAction(WaitSensorData(self.rover, MazeTurnAroundCornerAction(self.rover, MazeAction.LEFT, distance, speed)))


if __name__ == "__main__":
    try:
        print("Starting canyons-of-mars agent...")

        canyonsOfMarsAgent = CanyonsOfMarsAgent()

        pyroslib.init("canyons-of-mars-agent", unique=True, onConnected=canyonsOfMarsAgent.connected)

        canyonsOfMarsAgent.register_logger()

        print("Started canyons-of-mars agent.")

        pyroslib.forever(0.1, canyonsOfMarsAgent.mainLoop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
