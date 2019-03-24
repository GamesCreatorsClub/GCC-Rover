
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
from rover import Rover, normaiseAngle, angleDiference
from challenge_utils import AgentClass, Action, WaitSensorData, WarmupAction, PID


SQRT2 = math.sqrt(2)

WHEEL_CIRCUMFERENCE = 68 * math.pi
WHEEL_NAMES = ['fl', 'fr', 'bl', 'br']

pyroslib.logging.LOG_LEVEL = LOG_LEVEL_INFO

MIN_ANGLE = 0.5
MAX_WHEEL_ANGLE = 45

HEADING_MIN_RADIUS = 150

SPEED = 130
REQUIRED_WALL_DISTANCE = 250

corridor_logger = None


class MazeMothAction(Action):
    heading_pid = ...  # type: PID
    side_distance_pid = ...  # type: PID

    def __init__(self, agent, speed, distance):
        super(MazeMothAction, self).__init__(agent)
        self.speed = speed
        self.wall_distance = distance
        self.heading_pid = None
        self.side_distance_pid = None
        self.rover_speed = 25

    def start(self):
        super(MazeMothAction, self).start()
        pyroslib.publish("sensor/distance/focus", "270 315 0 45 90")
        self.heading_pid = PID(0.6, 0.3, 0, 0.2, 0, diff_method=angleDiference)
        self.side_distance_pid = PID(0.75, 0.0, 0.05, 0.25, 0)

    def next(self):
        return self

    @staticmethod
    def calculateRealDistance(side_distance, side_angle):
        if side_distance < 1:
            return 0

        if side_angle > 180:
            side_angle = 360 - side_angle

        side_angle = side_angle * math.pi / 180

        return math.sin(math.pi / 2 - side_angle) * side_distance

    def execute(self):
        state = self.rover.getRoverState()

        heading = state.heading.heading
        front_left_distance = state.radar.radar[315]
        front_distance = state.radar.radar[0]
        front_right_distance = state.radar.radar[45]

        left_distance = state.radar.radar[270]
        right_distance = state.radar.radar[90]

        if left_distance > front_left_distance:  # / SQRT2:
            left_distance = front_left_distance

        if right_distance > front_right_distance:  # / SQRT2:
            right_distance = front_right_distance

        if left_distance < right_distance:
            current_wall_distance = left_distance
            sign = 1
        else:
            current_wall_distance = right_distance
            sign = -1

        if current_wall_distance > self.wall_distance:
            angle = 0
            angle_rad = 0
            angle_pid_output = 0
        else:
            # Keeping distance
            angle_pid_output = self.side_distance_pid.process(self.wall_distance, current_wall_distance)
            angle = 0
            if abs(angle_pid_output) < 1:
                angle = 0
            elif angle_pid_output > 0 and angle_pid_output > self.rover_speed:
                angle = math.pi / 4
            elif angle_pid_output < 0 and angle_pid_output < -self.rover_speed:
                angle = -math.pi / 4
            else:
                try:
                    angle = math.asin(angle_pid_output / self.rover_speed)
                except BaseException as ex:
                    self.agent.log_always("Domain error")

            if angle > MAX_WHEEL_ANGLE:
                angle = MAX_WHEEL_ANGLE
            elif angle < -MAX_WHEEL_ANGLE:
                angle = -MAX_WHEEL_ANGLE

            angle_rad = sign * angle
            angle = sign * int(angle * 180 / math.pi)

        if front_left_distance > front_right_distance and front_left_distance > front_distance:
            target_heading = -45
        elif front_right_distance > front_left_distance and front_right_distance > front_distance:
            target_heading = 45
        else:
            target_heading = 0

        # Keeping heading
        heading_pid_output = -self.heading_pid.process(-target_heading, 0)
        if -MIN_ANGLE < heading_pid_output < MIN_ANGLE:
            distance = 32000
        else:
            heading_fix_rad = heading_pid_output * math.pi / 180
            distance = self.rover_speed / (heading_fix_rad * math.cos(angle_rad))
            if 0 <= distance < HEADING_MIN_RADIUS:
                distance = HEADING_MIN_RADIUS
            elif -HEADING_MIN_RADIUS < distance < 0:
                distance = -HEADING_MIN_RADIUS

        speed = self.speed

        self.agent.log_info(
            "rover_speed={: 4d} front_dist={: 4d} front_left_dist={: 4d} front_right_dist={: 4d} heading_pid_out={: 7.2f} left_dist={: 4d} right_dist={: 4d} angle_pid_out={: 7.2f} speed={: 3d} angle={: 3d} distance={: 3d}".format(
                int(self.rover_speed),
                int(front_distance), int(front_left_distance), int(front_right_distance), heading_pid_output,
                int(left_distance), int(right_distance), angle_pid_output,
                int(speed), int(angle), int(distance)))

        self.rover.command(pyroslib.publish, speed, angle, distance)


class CanyonsOfMarsAgent(AgentClass):
    def __init__(self):
        super(CanyonsOfMarsAgent, self).__init__("canyons")
        self.running = False
        self.rover = Rover()
        self.last_execution_time = 0

    # def stop(self):
    #     self.running = False
    #     self.rover.reset()
    #     self.nextAction(self.stop_action)
    #     pyroslib.publish("position/heading/stop", '')
    #     pyroslib.publish("position/pause", "")
    #     pyroslib.publish("sensor/distance/pause", "")

    def start(self, data):
        if not self.running:

            if data[0] == 'corridor':
                super(CanyonsOfMarsAgent, self).start(data)

                distance = REQUIRED_WALL_DISTANCE
                speed = SPEED

                corridor_action = MazeMothAction(self, speed, distance)
                wait_for_heading_action = WaitSensorData(self, corridor_action)

                self.nextAction(wait_for_heading_action)
            elif data[0] == 'turnCorner':
                super(CanyonsOfMarsAgent, self).start(data)

                # speed = int(data[1])
                # distance = int(data[2])
                #
                # self.nextAction(WaitSensorData(self, MazeTurnAroundCornerAction(self, MazeAction.LEFT, distance, speed)))


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
