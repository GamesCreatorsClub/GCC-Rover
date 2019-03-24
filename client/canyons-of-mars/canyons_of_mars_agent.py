
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

EXIT_HEADING = 270
EXIT_HEADING_CONE = 15

HEADING_MIN_RADIUS = 200

SPEED = 150
FOLLOW_WALL_SPEED = 170

REQUIRED_WALL_DISTANCE = 250

STEERING_FRONT_WALL_DISTANCE = 800

MAX_ANGLE = 45

corridor_logger = None


class MazeMothAction(Action):
    heading_pid = ...  # type: PID
    side_distance_pid = ...  # type: PID

    def __init__(self, agent, speed, distance, next_state):
        super(MazeMothAction, self).__init__(agent)
        self.next_state = next_state
        self.speed = speed
        self.wall_distance = distance
        self.heading_pid = None
        self.side_distance_pid = None
        self.rover_speed = 25

    def start(self):
        super(MazeMothAction, self).start()
        pyroslib.publish("sensor/distance/focus", "270 315 0 45 90")
        # self.heading_pid = PID(0.6, 0.3, 0, 0.2, 0, diff_method=angleDiference)
        self.heading_pid = PID(0.6, 00, 0, 0.2, 0, diff_method=angleDiference)
        self.side_distance_pid = PID(0.75, 0.0, 0.05, 0.25, 0)

    @staticmethod
    def calculateRealDistance(side_distance, side_angle):
        if side_distance < 1:
            return 0

        if side_angle > 180:
            side_angle = 360 - side_angle

        side_angle = side_angle * math.pi / 180

        return math.sin(math.pi / 2 - side_angle) * side_distance

    def next(self):
        state = self.rover.getRoverState()
        if state.heading.heading > EXIT_HEADING - EXIT_HEADING_CONE and state.heading.heading < EXIT_HEADING + EXIT_HEADING_CONE:  # and state.heading.last_heading < EXIT_HEADING:
            self.agent.log_info("prev_heading={: 7.2f} this_heading={: 7.2f}".format(state.heading.last_heading, state.heading.last_heading))
            return self.next_state
        return self

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

        turning_requirement = 25
        if front_distance < STEERING_FRONT_WALL_DISTANCE:
            propotion = 1 - front_distance / STEERING_FRONT_WALL_DISTANCE
            turning_requirement = 25 + propotion * 45
            if turning_requirement > 90:
                turning_requirement = 90

        if front_left_distance > front_right_distance and front_left_distance > front_distance:
            ratio = front_left_distance / front_distance
            if ratio > 2:
                ratio = 2
            ratio -= 1

            target_heading = -turning_requirement - 20 * ratio
        elif front_right_distance > front_left_distance and front_right_distance > front_distance:
            ratio = front_right_distance / front_distance
            if ratio > 2:
                ratio = 2
            ratio -= 1

            target_heading = turning_requirement + 20 * ratio
        elif front_left_distance > front_right_distance:
            ratio = front_distance / front_left_distance
            if ratio > 2:
                ratio = 2
            ratio -= 1

            ratio = 1 - ratio

            target_heading = -20 * ratio
        else:
            ratio = front_distance / front_right_distance
            if ratio > 2:
                ratio = 2
            ratio -= 1

            ratio = 1 - ratio

            target_heading = 20 * ratio


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
            "rover_speed={: 4d} front_dist={: 4d} front_left_dist={: 4d} front_right_dist={: 4d} heading={: 7.2f} heading_pid_out={: 7.2f} left_dist={: 4d} right_dist={: 4d} angle_pid_out={: 7.2f} speed={: 3d} angle={: 3d} distance={: 3d}".format(
                int(self.rover_speed),
                int(front_distance), int(front_left_distance), int(front_right_distance),
                heading, heading_pid_output,
                int(left_distance), int(right_distance), angle_pid_output,
                int(speed), int(angle), int(distance)))

        self.rover.command(pyroslib.publish, speed, angle, distance)


class FollowWallKeepingHeadingAction(Action):
    def __init__(self, agent, speed, wall_angle, direction_angle, next_action=None):
        super(FollowWallKeepingHeadingAction, self).__init__(agent)
        self.speed = speed
        self.next_action = next_action
        self.wall_angle = wall_angle
        self.direction_angle = direction_angle
        self.required_side_distance = 150
        self.required_keeping_side_distance = REQUIRED_WALL_DISTANCE

        self.rover_speed = 25
        self.distance_error = 0

        self.direction_pid = None
        self.heading_pid = None

    @staticmethod
    def calculateRealDistance(side_distance, side_angle):
        if side_distance < 1:
            return 0

        if side_angle > 180:
            side_angle = 360 - side_angle

        side_angle = side_angle * math.pi / 180

        return math.sin(math.pi / 2 - side_angle) * side_distance

    # def hasRadar(self, state):
    #     return state.radar.radar[self.wall_angle] > 1 and state.radar.radar[self.direction_angle] > 1

    def obtainRoverSpeed(self):
        self.rover_speed = self.rover.wheel_odos.averageSpeed() / 10
        self.rover_speed = 25

    def keepHeading(self):
        state = self.rover.getRoverState()

        # Keeping heading
        heading = state.heading.heading
        heading_output = -self.heading_pid.process(self.direction_angle, heading)
        if -MIN_ANGLE < heading_output < MIN_ANGLE:
            distance = 32000
        else:
            heading_fix_rad = heading_output * math.pi / 180
            distance = self.rover_speed / heading_fix_rad
            if 0 <= distance < HEADING_MIN_RADIUS:
                distance = HEADING_MIN_RADIUS
            elif -HEADING_MIN_RADIUS < distance < 0:
                distance = -HEADING_MIN_RADIUS

        return distance, heading_output

    def keepDirection(self, setpoint_distance, current_distance):
        state = self.rover.getRoverState()

        # Keeping direction
        angle_output = self.direction_pid.process(setpoint_distance, current_distance)
        angle = 0
        if abs(angle_output) < 1:
            angle = 0
        elif angle_output > 0 and angle_output > self.rover_speed:
            angle = math.pi / 4
        elif angle_output < 0 and angle_output < -self.rover_speed:
            angle = -math.pi / 4
        else:
            try:
                angle = math.asin(angle_output / self.rover_speed)
            except BaseException as ex:
                self.agent.log_always("Domain error")

        if angle > MAX_ANGLE:
            angle = MAX_ANGLE
        elif angle < -MAX_ANGLE:
            angle = -MAX_ANGLE

        angle = int(angle * 180 / math.pi)

        return angle, angle_output

    def start(self):
        super(FollowWallKeepingHeadingAction, self).start()
        # pyroslib.publish("sensor/distance/focus", str(self.wall_angle) + " " + str(self.direction_angle))
        self.direction_pid = PID(0.20, 0, 0.01, 0.5, 0)
        self.heading_pid = PID(0.25, 0.02, 0.0, 1, 0, diff_method=angleDiference)

    def execute(self):
        state = self.rover.getRoverState()

        distance, heading_output = self.keepHeading()

        wall_distance = self.calculateRealDistance(state.radar.radar[self.wall_angle], self.direction_angle  - state.heading.heading)

        angle, angle_output = self.keepDirection(wall_distance, self.required_keeping_side_distance)

        speed = self.speed

        front_distance = state.radar.radar[0]

        if front_distance < 400:
            angle = angle + 35

        self.agent.log_info("rover_speed={: 4d} front_dist={: 5d} dist_error={: 9.2f} wall_dist={: 5d} angle_fix={: 7.2f} heading={: 3d} heading_fix={: 7.2f} speed={: 3d} angle={: 3d} distance={: 3d}".format(
                            int(self.rover_speed),
                            int(front_distance), self.distance_error,
                            int(wall_distance), angle_output,
                            int(state.heading.heading), heading_output,
                            int(speed), int(angle), int(distance)))

        self.rover.command(pyroslib.publish, speed, angle, distance)

    def getActionName(self):
        return "Wall[{0} on {1}]".format(self.direction_angle, self.wall_angle)


class StraightWheelsAction(Action):
    def __init__(self, agent, next_action):
        super(StraightWheelsAction, self).__init__(agent)
        self.next_action = next_action

    def next(self):
        self.rover.command(pyroslib.publish, 0, 0, 3200)
        return self.next_action


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

                follow_wall_action = FollowWallKeepingHeadingAction(self, FOLLOW_WALL_SPEED, 90, 270, None)
                corridor_action = MazeMothAction(self, speed, distance, follow_wall_action)
                wait_for_heading_action = WaitSensorData(self, corridor_action)

                self.nextAction(wait_for_heading_action)

            elif data[0] == 'warmup':
                self.nextAction(StraightWheelsAction(self, WaitSensorData(self, WarmupAction(self))))


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
