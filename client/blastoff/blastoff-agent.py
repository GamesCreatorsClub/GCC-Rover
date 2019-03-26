
#
# Copyright 2016-2018 Games Creators Club
#
# MIT License
#

import math
import time
import telemetry
import traceback
import sys


import pyroslib
import pyroslib.logging

from pyroslib.logging import log, LOG_LEVEL_INFO, LOG_LEVEL_DEBUG, LOG_LEVEL_ALWAYS
from rover import RoverState, normaiseAngle, angleDiference
from challenge_utils import AgentClass, Action, WaitSensorData, WarmupAction, PID

MINIMUM_SPEED = 60
MIN_ANGLE = 0.5
MAX_ANGLE = 45

HEADING_MIN_DISTANCE = 150

SPEED = 150
REQUIRED_WALL_DISTANCE = 250

STEERING_FRONT_WALL_DISTANCE = 800
HEADING_MIN_RADIUS = 200

STEERING_CONSTANT_ANGLE = 15
STEERING_RATIO_ANGLE = 20

pyroslib.logging.LOG_LEVEL = LOG_LEVEL_INFO

SQRT2 = math.sqrt(2)


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
        self.heading_pid = PID(0.6, 00, 0, 0.2, 0, diff_method=angleDiference)
        self.side_distance_pid = PID(0.75, 0.0, 0.05, 0.4, 0)

    @staticmethod
    def calculateRealDistance(side_distance, side_angle):
        if side_distance < 1:
            return 0

        if side_angle > 180:
            side_angle = 360 - side_angle

        side_angle = side_angle * math.pi / 180

        return math.sin(math.pi / 2 - side_angle) * side_distance

    def next(self):
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

            if angle > MAX_ANGLE:
                angle = MAX_ANGLE
            elif angle < -MAX_ANGLE:
                angle = -MAX_ANGLE

            angle_rad = sign * angle
            angle = sign * int(angle * 180 / math.pi)

        turning_requirement = STEERING_CONSTANT_ANGLE
        # if front_distance < STEERING_FRONT_WALL_DISTANCE:
        #     propotion = 1 - front_distance / STEERING_FRONT_WALL_DISTANCE
        #     turning_requirement = 25 + propotion * 45
        #     if turning_requirement > 90:
        #         turning_requirement = 90

        if front_left_distance > front_right_distance and front_left_distance > front_distance:
            ratio = front_left_distance / front_distance
            if ratio > 2:
                ratio = 2
            ratio -= 1

            target_heading = -turning_requirement - STEERING_RATIO_ANGLE * ratio
        elif front_right_distance > front_left_distance and front_right_distance > front_distance:
            ratio = front_right_distance / front_distance
            if ratio > 2:
                ratio = 2
            ratio -= 1

            target_heading = turning_requirement + STEERING_RATIO_ANGLE * ratio
        elif front_left_distance > front_right_distance:
            ratio = front_distance / front_left_distance
            if ratio > 2:
                ratio = 2
            ratio -= 1

            ratio = 1 - ratio

            target_heading = -STEERING_RATIO_ANGLE * ratio
        else:
            ratio = front_distance / front_right_distance
            if ratio > 2:
                ratio = 2
            ratio -= 1

            ratio = 1 - ratio

            target_heading = STEERING_RATIO_ANGLE * ratio

        # Keeping heading
        heading_pid_output = -self.heading_pid.process(-target_heading, 0)
        if -MIN_ANGLE < heading_pid_output < MIN_ANGLE:
            distance = 32000
        else:
            heading_fix_rad = heading_pid_output * math.pi / 180
            angle_factor = math.cos(angle_rad) * math.cos(angle_rad) * math.cos(angle_rad)
            distance = self.rover_speed / (heading_fix_rad * angle_factor)
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


class BlastoffAction(Action):
    def __init__(self, agent, speed, next_action):
        super(BlastoffAction, self).__init__(agent)
        self.speed = speed
        self.next_action = next_action

        self.direction_pid = None
        self.heading_pid = None

        self.distance_error = 0
        self.rover_speed = 0

        self.required_keeping_side_distance = REQUIRED_WALL_DISTANCE
        self.last_speed = 0
        self.last_speed_time = 0

    def obtainRoverSpeed(self):
        self.rover_speed = self.rover.wheel_odos.averageSpeed() / 10
        self.rover_speed = self.speed

    def keepHeading(self, heading):
        state = self.rover.getRoverState()

        # Keeping heading
        heading_output = -self.heading_pid.process(0, heading)
        if -MIN_ANGLE < heading_output < MIN_ANGLE:
            distance = 32000
        else:
            heading_fix_rad = heading_output * math.pi / 180
            distance = self.rover_speed / heading_fix_rad
            if 0 <= distance < HEADING_MIN_DISTANCE:
                distance = HEADING_MIN_DISTANCE
            elif -HEADING_MIN_DISTANCE < distance < 0:
                distance = -HEADING_MIN_DISTANCE

        return distance, heading_output

    def keepDirection(self, requested_angle, setpoint_distance, current_distance):
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

        angle = int(requested_angle + angle * 180 / math.pi)

        return angle, angle_output

    def calculateSpeed(self, speed_time):
        # Defining forward speed
        if self.last_speed_time == speed_time:
            return self.last_speed

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

        self.last_speed = speed
        self.last_speed_time = speed_time
        return speed

    def start(self):
        super(BlastoffAction, self).start()

    def end(self):
        super(BlastoffAction, self).end()


class FollowWallAction(BlastoffAction):
    FRONT = 1
    BACK = 2

    def __init__(self, agent, speed, next_action=None):
        super(FollowWallAction, self).__init__(agent, speed, next_action)

    @staticmethod
    def calculateRealDistance(side_distance, side_angle):
        if side_distance < 1:
            return 0

        if side_angle > 180:
            side_angle = 360 - side_angle

        side_angle = side_angle * math.pi / 180

        return math.sin(math.pi / 2 - side_angle) * side_distance

    def calculateAngleAndFrontDistance(self, df, dm, db):
        dfsqrt2 = df / SQRT2
        dbsqrt2 = db / SQRT2

        if df < db:
            # angle = math.atan2(dfsqrt2, dfsqrt2 - dm) * 180 / math.pi - 90
            angle = math.atan2(dfsqrt2, dfsqrt2 - dm) - math.pi / 2
            calc_type = self.FRONT

        else:
            # angle = 90 - math.atan2(dbsqrt2, dbsqrt2 - dm) * 180 / math.pi
            angle = math.pi / 2 - math.atan2(dbsqrt2, dbsqrt2 - dm)
            calc_type = self.BACK

        angle = angle * 180 / math.pi

        d = self.calculateRealDistance(dm, angle)

        return angle, int(d), calc_type

    def start(self):
        super(FollowWallAction, self).start()
        pyroslib.publish("sensor/distance/focus", "0, 45, 90, 135")
        self.heading_pid = PID(0.75, 0.2, 0.0, 1.0, 0, diff_method=angleDiference)
        self.direction_pid = PID(0.75, 0, 0.01, 0.7, 0)

    def next(self):
        self.obtainRoverSpeed()

        return self

    def execute(self):
        state = self.rover.getRoverState()

        front_distance = state.radar.radar[0]
        front_right_distance = state.radar.radar[45]
        right_distance = state.radar.radar[90]
        back_right_distance = state.radar.radar[135]

        wall_angle, wall_distance, calc_type = self.calculateAngleAndFrontDistance(front_right_distance, right_distance, back_right_distance)

        orig_wall_angle = wall_angle
        if wall_angle >= -10 and front_distance < 650 and state.radar.radar_deltas[0] < 0:
            pass
            wall_angle += 30

        distance, heading_output = self.keepHeading(-wall_angle)

        angle, angle_output = self.keepDirection(0, wall_distance, self.required_keeping_side_distance)

        speed = self.speed

        self.agent.log_info("rspd={: 4d} f={: 5d} fs={: 5d} s={: 5d} bs={: 5d} wall={: 5d} calc=a{:1d} angle_f={: 7.2f} owall_a={: 3d} wall_a={: 3d} head_fix={: 7.2f} speed={: 3d} angle={: 3d} distance={: 3d}".format(
                            int(self.rover_speed),
                            int(front_distance), int(front_right_distance), int(right_distance), int(back_right_distance),
                            int(wall_distance), calc_type,  angle_output,
                            int(orig_wall_angle), int(wall_angle), heading_output,
                            int(speed), int(angle), int(distance)))

        self.rover.command(pyroslib.publish, speed, angle, distance)

    def getActionName(self):
        return "Wall"


class HeadingAntenae(BlastoffAction):
    FRONT = 1
    BACK = 2

    def __init__(self, agent, speed, next_action=None):
        super(HeadingAntenae, self).__init__(agent, speed, next_action)

    @staticmethod
    def calculateRealDistance(side_distance, side_angle):
        if side_distance < 1:
            return 0

        if side_angle > 180:
            side_angle = 360 - side_angle

        side_angle = side_angle * math.pi / 180

        return math.sin(math.pi / 2 - side_angle) * side_distance

    def calculateAngleAndFrontDistance(self, df, dm, db):
        dfsqrt2 = df / SQRT2
        dbsqrt2 = db / SQRT2

        if df < db:
            # angle = math.atan2(dfsqrt2, dfsqrt2 - dm) * 180 / math.pi - 90
            angle = math.atan2(dfsqrt2, dfsqrt2 - dm) - math.pi / 2
            calc_type = self.FRONT

        else:
            # angle = 90 - math.atan2(dbsqrt2, dbsqrt2 - dm) * 180 / math.pi
            angle = math.pi / 2 - math.atan2(dbsqrt2, dbsqrt2 - dm)
            calc_type = self.BACK

        angle = angle * 180 / math.pi

        d = self.calculateRealDistance(dm, angle)

        return angle, int(d), calc_type

    def start(self):
        super(HeadingAntenae, self).start()
        pyroslib.publish("sensor/distance/focus", "315, 45")
        self.heading_pid = PID(0.75, 0.2, 0.0, 1.2, 0, diff_method=angleDiference)
        self.direction_pid = PID(0.75, 0, 0.02, 0.4, 0)

    def next(self):
        self.obtainRoverSpeed()

        return self

    def execute(self):
        state = self.rover.getRoverState()

        heading = state.heading.heading

        front_left = state.radar.radar[315]
        front_right = state.radar.radar[45]

        angle_output = self.direction_pid.process(front_right, front_left)
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

        angle_rad = angle
        angle = int(angle * 180 / math.pi)

        heading_pid_output = -self.heading_pid.process(0, heading)
        if -MIN_ANGLE < heading_pid_output < MIN_ANGLE:
            distance = 32000
        else:
            heading_fix_rad = heading_pid_output * math.pi / 180
            angle_factor = math.cos(angle_rad) * math.cos(angle_rad) * math.cos(angle_rad)
            distance = self.rover_speed / (heading_fix_rad * angle_factor)
            if 0 <= distance < HEADING_MIN_RADIUS:
                distance = HEADING_MIN_RADIUS
            elif -HEADING_MIN_RADIUS < distance < 0:
                distance = -HEADING_MIN_RADIUS

        speed = self.speed

        self.agent.log_info("rspd={: 4d} fl={: 5d} fr={: 5d} heading={: 3d} heading_pid={: 7.2f}, angle_fix={: 7.2f} speed={: 3d} angle={: 3d} distance={: 3d}".format(
                            int(self.rover_speed),
                            int(front_left), int(front_right),
                            int(heading), heading_pid_output,
                            angle_output,
                            int(speed), int(angle), int(distance)))

        self.rover.command(pyroslib.publish, speed, angle, distance)

    def getActionName(self):
        return "HeadingAntenae"


class StraightWheelsAction(Action):
    def __init__(self, agent, next_action):
        super(StraightWheelsAction, self).__init__(agent)
        self.next_action = next_action

    def next(self):
        self.rover.command(pyroslib.publish, 0, 0, 3200)
        return self.next_action


class BlastoffAgent(AgentClass):
    def __init__(self):
        super(BlastoffAgent, self).__init__("blastoff")

    def connected(self):
        super(BlastoffAgent, self).connected()

    def start(self, data):
        if not self.running:
            if data[0] == 'blastoff':
                super(BlastoffAgent, self).start(data)

                # follow_wall = FollowWallKeepingHeadingAction(self, SPEED)
                # follow_wall = FollowWallAction(self, SPEED)
                # follow_wall = MazeMothAction(self, SPEED, REQUIRED_WALL_DISTANCE)
                follow_wall = HeadingAntenae(self, SPEED)
                wait_sensor_data_action = StraightWheelsAction(self, WaitSensorData(self, follow_wall))
                self.nextAction(wait_sensor_data_action)

            elif data[0] == 'warmup':
                self.nextAction(StraightWheelsAction(self, WaitSensorData(self, WarmupAction(self))))


def stopCallback():
    print("Asked to stop!")
    sys.exit(0)


if __name__ == "__main__":
    try:
        print("Starting Blastoff agent...")

        print("  creating logger...")
        state_logger = RoverState.defineLogger(telemetry.MQTTLocalPipeTelemetryLogger('rover-state'))

        blastoff = BlastoffAgent()

        pyroslib.init("blastoff-agent", unique=True, onConnected=blastoff.connected, onStop=stopCallback)

        print("  initialising logger...")
        state_logger.init()

        blastoff.register_logger()
        print("Started Blastoff agent.")

        pyroslib.forever(0.1, blastoff.mainLoop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
