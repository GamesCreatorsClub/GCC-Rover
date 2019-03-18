
#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import math
import pyroslib
import pyroslib.logging
import time

from pyroslib.logging import log, LOG_LEVEL_ALWAYS, LOG_LEVEL_INFO, LOG_LEVEL_DEBUG
from rover import WheelOdos, WHEEL_NAMES
from rover import normaiseAngle, angleDiference
from challenge_utils import Action


SQRT2 = math.sqrt(2)
PIhalf = math.pi / 2


class PID:
    def __init__(self, _kp, _ki, _kd, gain, dead_band, diff_method=None):
        self.set_point = 0.0
        self.p = 0.0
        self.i = 0.0
        self.d = 0.0
        self.kp = _kp
        self.ki = _ki
        self.kd = _kd
        self.kg = gain
        self.dead_band = dead_band
        self.last_error = 0.0
        self.last_time = 0.0
        self.last_output = 0.0
        self.last_delta = 0.0
        self.first = True
        self.diff_method = diff_method if diff_method is not None else self.subtract

    def process(self, set_point, current):
        now = time.time()

        error = self.diff_method(set_point, current)
        if abs(error) <= self.dead_band:
            error = 0.0

        if self.first:
            self.first = False
            self.set_point = set_point
            self.last_error = error
            self.last_time = now
            return 0
        else:
            delta_time = now - self.last_time

            self.p = error
            if (self.last_error < 0 and error > 0) or (self.last_error > 0 and error < 0):
                self.i = 0.0
            elif abs(error) <= 0.1:
                self.i = 0.0
            else:
                self.i += error * delta_time

            if delta_time > 0:
                self.d = (error - self.last_error) / delta_time

            output = self.p * self.kp + self.i * self.ki + self.d * self.kd

            output *= self.kg

            self.set_point = set_point
            self.last_output = output
            self.last_error = error
            self.last_time = now
            self.last_delta = delta_time

        return output

    @staticmethod
    def subtract(set_point, current):
        return set_point - current

    def to_string(self):
        return "p=" + str(self.p * self.kp) + ", i=" + str(self.i * self.ki) + ", d=" + str(self.d * self.kd) + ", last_delta=" + str(self.last_delta)


class MazeAttitude:

    UNKNOWN = 0
    LEFT_WALL = 1
    RIGHT_WALL = 2
    FRONT_WALL = 4
    BACK_WALL = 8

    NO_GAP = 0
    FORWARD_GAP = 1
    SIDE_GAP = 2

    POINTS = [0, 45, 90, 135, 180, 225, 270, 315]
    WALLS = [90, 270, 0, 180]

    L0_45 = 0
    L45_90 = 45
    L90_135 = 90
    L135_180 = 135
    L180_225 = 180
    L225_270 = 225
    L270_315 = 270
    L315_0 = 315

    LINES = [L0_45, L45_90, L90_135, L135_180, L180_225, L225_270, L270_315, L315_0]

    ANGLE_TOLLERANCE = 1.075

    @staticmethod
    def normAngle(a):
        if a > PIhalf:
            a = a - math.pi
        elif a <= -PIhalf:
            a = a + math.pi
        return a

    class Line:
        def __init__(self, line_index, long_point_index, short_point_index, factor, adjust):
            self.line_index = line_index
            self.short_point_index = short_point_index
            self.long_point_index = long_point_index
            self.factor = factor
            self.adjust = adjust
            self.angle = None

        def calcAngle(self, distances):
            long_distance = distances[self.long_point_index]
            short_distance = distances[self.short_point_index]

            if long_distance is not None and short_distance is not None:
                lsqrt2 = long_distance / SQRT2
                self.angle = MazeAttitude.normAngle(math.atan2(lsqrt2, lsqrt2 - short_distance) * self.factor + self.adjust)
            else:
                self.angle = None

    class Wall:
        def __init__(self, distance_sensor_angle, distance_sensor_index, wall_point_kind, left_mid_point_index, left_point_index, mid_point_index, right_point_index):

            self.ds_angle = distance_sensor_angle
            self.ds_index = distance_sensor_index
            self.wall_point_kind = wall_point_kind

            self.left_mid_point_index = left_mid_point_index
            self.left_point_index = left_point_index
            self.mid_point_index = mid_point_index
            self.right_point_index = right_point_index

            self.is_front_or_back = self.ds_angle == 0 or self.ds_angle == 180

            self.selected_line = None
            self.angle = None
            self.distance = None

        def setAngle(self, angle, distances):
            self.angle = angle

            distance = distances[self.mid_point_index]
            if distance < 1:
                self.distance = 0
            else:
                if self.is_front_or_back:
                    self.distance = abs(int(math.sin(angle) * distance))
                else:
                    self.distance = abs(int(math.cos(angle) * distance))

        def setAngleAndDistance(self, angle, distance):
            self.angle = angle
            self.distance = distance

        def tryFindingWall(self, distances, lines, points):
            lmline = lines[self.left_mid_point_index]
            lline = lines[self.left_point_index]
            mline = lines[self.mid_point_index]
            rline = lines[self.right_point_index]

            dlong1 = distances[lline.long_point_index]
            dmid = distances[mline.short_point_index]
            dlong2 = distances[mline.long_point_index]

            plong1 = points[self.left_point_index]
            pmid = points[self.mid_point_index]
            plong2 = points[self.right_point_index]

            if dlong1 < dlong2 and plong1 != MazeAttitude.UNKNOWN and lmline.angle * MazeAttitude.ANGLE_TOLLERANCE >= lline.angle >= lmline.angle / MazeAttitude.ANGLE_TOLLERANCE:
                points[self.mid_point_index] = points[lline.long_point_index]
                angle = MazeAttitude.normAngle(mline.angle - PIhalf)
                distance = distances[self.right_point_index] * abs(math.sin(mline.angle) / SQRT2)
                self.setAngleAndDistance(angle, distance)
            elif dlong1 >= dlong2 and plong2 != MazeAttitude.UNKNOWN and mline.angle * MazeAttitude.ANGLE_TOLLERANCE >= rline.angle >= mline.angle / MazeAttitude.ANGLE_TOLLERANCE:
                points[self.mid_point_index] = points[rline.long_point_index]
                angle = MazeAttitude.normAngle(mline.angle + PIhalf)
                distance = distances[self.left_point_index] * abs(math.sin(mline.angle) / SQRT2)
                self.setAngleAndDistance(angle, distance)

            elif lline.angle is not None and mline.angle is not None:
                if lline.angle * MazeAttitude.ANGLE_TOLLERANCE >= mline.angle >= lline.angle / MazeAttitude.ANGLE_TOLLERANCE:
                    if plong1 == MazeAttitude.UNKNOWN:
                        points[self.left_point_index] = self.wall_point_kind
                    if pmid == MazeAttitude.UNKNOWN:
                        points[self.mid_point_index] = self.wall_point_kind
                    if plong2 == MazeAttitude.UNKNOWN:
                        points[self.right_point_index] = self.wall_point_kind
                    self.setAngle(mline.angle, distances)
                else:
                    if dlong1 < dlong2 and plong1 == MazeAttitude.UNKNOWN and pmid == MazeAttitude.UNKNOWN:
                        points[self.left_point_index] = self.wall_point_kind
                        points[self.mid_point_index] = self.wall_point_kind
                        self.setAngle(lline.angle, distances)
                    elif dlong1 >= dlong2 and plong2 == MazeAttitude.UNKNOWN and pmid == MazeAttitude.UNKNOWN:
                        points[self.mid_point_index] = self.wall_point_kind
                        points[self.right_point_index] = self.wall_point_kind
                        self.setAngle(mline.angle, distances)
                    elif plong1 == MazeAttitude.UNKNOWN and pmid == MazeAttitude.UNKNOWN and plong2 != MazeAttitude.UNKNOWN:
                        points[self.left_point_index] = self.wall_point_kind
                        points[self.mid_point_index] = self.wall_point_kind
                        self.setAngle(lline.angle, distances)
                    elif plong1 != MazeAttitude.UNKNOWN and pmid == MazeAttitude.UNKNOWN and plong2 == MazeAttitude.UNKNOWN:
                        points[self.mid_point_index] = self.wall_point_kind
                        points[self.right_point_index] = self.wall_point_kind
                        self.setAngle(mline.angle, distances)

            elif lline.angle is not None and plong1 == MazeAttitude.UNKNOWN and pmid == MazeAttitude.UNKNOWN:
                points[self.left_point_index] = self.wall_point_kind
                points[self.mid_point_index] = self.wall_point_kind
                self.setAngle(lline.angle, distances)

            elif mline.angle is not None and pmid == MazeAttitude.UNKNOWN and plong2 == MazeAttitude.UNKNOWN:
                points[self.mid_point_index] = self.wall_point_kind
                points[self.right_point_index] = self.wall_point_kind
                self.setAngle(mline.angle, distances)

    def __init__(self):
        self.lines = {self.L315_0: self.Line(self.L315_0, 315, 0, -1, math.pi), self.L0_45: self.Line(self.L0_45, 45, 0, 1, -math.pi),
                      self.L45_90: self.Line(self.L45_90, 45, 90, -1, PIhalf), self.L90_135: self.Line(self.L90_135, 135, 90, 1, -PIhalf),
                      self.L135_180: self.Line(self.L135_180, 135, 180, -1, math.pi), self.L180_225: self.Line(self.L180_225, 225, 180, 1, -math.pi),
                      self.L225_270: self.Line(self.L225_270, 225, 270, -1, PIhalf), self.L270_315: self.Line(self.L270_315, 315, 270, 1, -PIhalf)}
        self.right_wall = self.Wall(90, 2, self.RIGHT_WALL, 0, 45, 90, 135)
        self.left_wall = self.Wall(270, 6, self.LEFT_WALL, 180, 225, 270, 315)
        self.front_wall = self.Wall(0, 0, self.FRONT_WALL, 270, 315, 0, 45)
        self.back_wall = self.Wall(180, 4, self.BACK_WALL, 90, 135, 180, 225)
        self.left_gap = self.NO_GAP
        self.right_gap = self.NO_GAP
        self.walls = {self.right_wall.ds_angle: self.right_wall, self.left_wall.ds_angle: self.left_wall, self.front_wall.ds_angle: self.front_wall, self.back_wall.ds_angle: self.back_wall}
        self.points = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0}
        self.distances = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0}

    def calculate(self, state):
        def getPointDistance(state, angle):
            distance = state.radar.radar[angle]
            status = state.radar.status[angle]
            if status == 0:
                return distance

            last_distance = state.radar.last_radar[angle]

            if abs(distance - last_distance) < 100:
                return distance

            return None

        def updateUndefinedWall(wall, preferable_wall, wall_adjust, second_wall):
            if wall.angle is None and self.distances[wall.ds_angle] is not None:
                if preferable_wall.angle is not None:
                    wall.setAngleAndDistance(self.normAngle(preferable_wall.angle + wall_adjust), self.distances[wall.mid_point_index])
                else:
                    wall.setAngleAndDistance(self.normAngle(second_wall.angle - wall_adjust), self.distances[wall.mid_point_index])
                self.points[wall.ds_angle] = wall.wall_point_kind

        self.distances = {p: getPointDistance(state, p) for p in self.POINTS}

        for line in self.lines:
            self.lines[line].calcAngle(self.distances)

        wls = [self.walls[w_ds_angle] for w_ds_angle in self.WALLS if self.distances[w_ds_angle] is not None]
        wall_processing_order = sorted(wls,
                                       key=lambda wall: self.distances[wall.ds_angle])

        for wall in wall_processing_order:
            wall.tryFindingWall(self.distances, self.lines, self.points)

        updateUndefinedWall(self.front_wall, self.right_wall, -PIhalf, self.left_wall)
        updateUndefinedWall(self.back_wall, self.right_wall, PIhalf, self.left_wall)
        updateUndefinedWall(self.right_wall, self.front_wall, PIhalf, self.back_wall)
        updateUndefinedWall(self.left_wall, self.front_wall, -PIhalf, self.back_wall)

        # TODO calc gaps


class MoveForwardOnOdo(Action):
    def __init__(self, rover, stop_action=None):
        super(MoveForwardOnOdo, self).__init__(rover)
        self.stop_action = stop_action
        self.required_odo = {'fl': 0, 'fr': 0, 'bl': 0, 'br': 0}

    def setRequiredOdo(self, distance):
        for wheel_name in WHEEL_NAMES:
            self.required_odo[wheel_name] = distance

    def start(self):
        super(MoveForwardOnOdo, self).start()
        state = self.rover.getRoverState()
        for wheel in self.required_odo:
            self.required_odo[wheel] = WheelOdos.normaliseOdo(state.wheel_odos[wheel] + self.required_odo[wheel])

        log(LOG_LEVEL_DEBUG, "Reset odo to " + str(self.required_odo) + "; starting...")

        self.rover.command(pyroslib.publish, 300, 120)
        # pyroslib.publish("move/steer", "300 120")

    def end(self):
        super(MoveForwardOnOdo, self).end()

    def next(self):
        state = self.rover.getRoverState()
        do_stop = False
        log(LOG_LEVEL_DEBUG, "Driving to " + str(self.required_odo))
        for wheel_name in WHEEL_NAMES:
            if state.wheel_odos[wheel_name] >= self.required_odo[wheel_name]:
                do_stop = True

        if state.radar.radar[0] < 1.0 or state.radar.radar[315] < 1.0 or state.radar.radar[45] < 1.0:
            do_stop = True

        if do_stop:
            return self.stop_action
        else:
            return self

    def execute(self):
        pass

    def getActionName(self):
        return "Forward ODO"


class MazeAction(Action):
    LEFT = -1
    RIGHT = 1

    def __init__(self, rover):
        super(MazeAction, self).__init__(rover)

    def check_next_action_conditions(self):
        return self


class ChicaneAction(MazeAction):
    def __init__(self, rover, left_or_right, distance, speed, next_action=None):
        super(ChicaneAction, self).__init__(rover)
        self.left_or_right = left_or_right
        self.distance = distance
        self.speed = speed
        self.next_action = next_action
        if self.left_or_right == MazeAction.RIGHT:
            self.a1 = 45
            self.a2 = 90
            self.a3 = 135
        else:
            self.a1 = 315
            self.a2 = 270
            self.a3 = 225

        self.left_corner_action = MazeTurnAroundCornerAction(self.rover, self.LEFT, self.distance, self.speed, self)
        self.right_corner_action = MazeTurnAroundCornerAction(self.rover, self.RIGHT, self.distance, self.speed, DriverForwardForTimeAction(self.rover, 10, self.speed, None))

    def start(self):
        super(ChicaneAction, self).start()

    def end(self):
        super(ChicaneAction, self).end()

    def next(self):
        if self.left_or_right == self.LEFT:
            diagonal_distance = state.radar.radar[45]
        else:
            diagonal_distance = state.radar.radar[315]

        if self.left_or_right == self.LEFT and diagonal_distance > 800:
            log(LOG_LEVEL_INFO, "Found second part of chicane, rfd={: 4d}".format(int(diagonal_distance)))
            self.left_or_right = self.RIGHT
        elif self.left_or_right == self.RIGHT and diagonal_distance > 800:
            log(LOG_LEVEL_INFO, "Found end ofchicane - leaging, rfd={: 4d}".format(int(diagonal_distance)))
            return self.next_action

        return self

    def execute(self):
        state = self.rover.getRoverState()
        front_distance = state.radar.radar[0]

        gain = 60
        offset = 150

        # Values that worked speed=150, steer=5-7, dist=4
        # self.speed = 150  # 150
        speed = 50  # mm/second - TODO use odo to update to correct value!
        speed_steer_fudge_factor = 5  # 5-7
        speed_distance_fudge_factor = 4   # 4

        min_angle = 1 * math.pi / 180

        steer_speed = speed * speed_steer_fudge_factor
        distance_speed = speed * speed_distance_fudge_factor

        if self.left_or_right == self.RIGHT:
            distance = -1000000000

            distance_from_wall = state.radar.radar[90]

            distance_error = distance_from_wall - self.distance

            angle = 0
            if abs(distance_error) < 10:
                angle = 0
            elif distance_error > 0 and distance_error > distance_speed:
                angle = math.pi / 4
                if front_distance < 450:
                    angle += math.pi * (450 - front_distance) / 1800  # divide with 10 and by 180 -> 450/10 - 45deg
            elif distance_error < 0 and distance_error < -distance_speed:
                angle = -math.pi / 4
                if front_distance < 450:
                    angle -= math.pi * (450 - front_distance) / 1800  # divide with 10 and by 180 -> 450/10 - 45deg
            else:
                try:
                    angle = math.asin(distance_error / distance_speed)
                except BaseException as ex:
                    log(LOG_LEVEL_ALWAYS, "Domain error wa={: 3d} dw={: 4d} de={: 4d} d={: 4d} s={: 3d}".format(int(0), int(distance_from_wall), int(distance_error), int(distance), int(speed)))

        else:
            distance = 1000000000

            distance_from_wall = state.radar.radar[270]

            distance_error = distance_from_wall - self.distance

            angle = 0
            if abs(distance_error) < 10:
                angle = 0
            elif distance_error > 0 and distance_error > distance_speed:
                angle = -math.pi / 4
                if front_distance < 450:
                    angle -= math.pi * (450 - front_distance) / 1800  # divide with 10 and by 180 -> 450/10 - 45deg
            elif distance_error < 0 and distance_error < -distance_speed:
                angle = math.pi / 4
                if front_distance < 450:
                    angle += math.pi * (450 - front_distance) / 1800  # divide with 10 and by 180 -> 450/10 - 45deg
            else:
                try:
                    angle = -math.asin(distance_error / distance_speed)
                except BaseException as ex:
                    log(LOG_LEVEL_ALWAYS, "Domain error wa={: 3d} dw={: 4d} de={: 4d} d={: 4d} s={: 3d}".format(int(0), int(distance_from_wall), int(distance_error), int(distance), int(speed)))

        distance = int(distance)
        angle = int(angle * 180 / math.pi)

        self.rover.command(pyroslib.publish, self.speed, angle, distance)
        # pyroslib.publish("move/steer", str(distance) + " " + str(self.speed) + " " + str(angle))

        wheel_orientations = state.wheel_odos.odos

        log(LOG_LEVEL_INFO, "{:16.3f}: dist_f={: 4d} wa={: 3d} dist_w={: 4d} dist_err={: 3d} la={: 3d} ld={: 3d} ra={: 3d} rd={: 3d} s_spd={: 3d} dist_spd={: 3d} dist={: 4d} angle={: 3d} heading={: 3d} odo={:7.2f}".format(
                            float(time.time()),
                            int(front_distance),
                            int(0 * 180 / math.pi), int(distance_from_wall), int(distance_error),
                            int(0 * 180 / math.pi), int(0), int(0 * 180 / math.pi), int(0),
                            int(steer_speed), int(distance_speed),
                            int(distance), int(angle), int(state.heading.heading),
                            float(state.wheel_orientations.orientations['fl'])
        ))

    def getActionName(self):
        return "Chicane " + ("L" if self.left_or_right == self.LEFT else "R")


class MazeCorridorAction(MazeAction):
    def __init__(self, rover, left_or_right, distance, speed, next_action=None):
        super(MazeCorridorAction, self).__init__(rover)
        self.left_or_right = left_or_right
        self.distance = distance
        self.speed = speed
        self.next_action = next_action
        if self.left_or_right == MazeAction.RIGHT:
            self.a1 = 45
            self.a2 = 90
            self.a3 = 135
        else:
            self.a1 = 315
            self.a2 = 270
            self.a3 = 225

        self.left_corner_action = MazeTurnAroundCornerAction(self.rover, self.LEFT, int(self.distance * 1), self.speed, self)
        self.right_corner_action = MazeTurnAroundCornerAction(self.rover, self.RIGHT, int(self.distance * 1), self.speed, self)
        # self.right_corner_action = MazeTurnAroundCornerAction(self.odo, self.radar, self.heading, self.RIGHT, self.distance, self.speed, DriverForwardForTimeActoun(10, self.speed, None))

        self.been_in_chicane = False

    def start(self):
        super(MazeCorridorAction, self).start()
        self.been_in_chicane = False

    def end(self):
        super(MazeCorridorAction, self).end()

    def next(self):
        left_diagonal_distance = state.radar.radar[315]
        front_distance = state.radar.radar[0]

        if state.radar.status[0] != 0 and abs(state.radar.radar_deltas[0]) > 100:
            log(LOG_LEVEL_INFO, "Front distance not correct: d={:4d} s={:2d} delta={:4d}".format(front_distance, state.radar.status[0], state.radar.radar_deltas[0]))
        else:
            if state.left_front_distance_of_wall > 100 and front_distance < 550:
                expected_diagonal_distance = 0
                if state.left_wall_angle < 0:
                    expected_diagonal_distance = front_distance * 2 * math.cos(math.pi / 4 + state.left_wall_angle)
                else:
                    expected_diagonal_distance = front_distance * math.cos(state.left_wall_angle) * SQRT2

                if False and not self.been_in_chicane and front_distance > 300 and left_diagonal_distance > expected_diagonal_distance * 1.2:
                    log(LOG_LEVEL_INFO, "Found chicane... lfd={: 4d} fd={: 4d} dd={: 4d} ed={: 4d}".format(int(state.left_front_distance_of_wall), int(front_distance), int(left_diagonal_distance), int(expected_diagonal_distance)))
                    self.been_in_chicane = True
                    return ChicaneAction(self.rover, self.LEFT, self.distance, self.speed, next_action=self)
                else:
                    log(LOG_LEVEL_INFO, "Found corner - turning, lfd={: 4d} fd={: 4d} dd={: 4d}  ed={: 4d}".format(int(state.left_front_distance_of_wall), int(front_distance), int(left_diagonal_distance), int(expected_diagonal_distance)))
                    return self.left_corner_action

            if front_distance < 550 and state.radar.radar_deltas[0] < 0:
                left_distances = state.radar.radar[270] + state.radar.radar[315]
                right_distances = state.radar.radar[90] + state.radar.radar[45]
                if left_distances > right_distances:
                    log(LOG_LEVEL_INFO, "Found corner 2 - turning left, fd={: 4d} ld={: 4d} rd={: 4d}".format(int(front_distance), int(left_distances), int(right_distances)))
                    return self.left_corner_action
                else:
                    log(LOG_LEVEL_INFO, "Found corner 2 - turning left, fd={: 4d} ld={: 4d} rd={: 4d}".format(int(front_distance), int(left_distances), int(right_distances)))
                    return self.right_corner_action

            if state.right_front_distance_of_wall > 100 and state.left_front_distance_of_wall > 100 and front_distance < 700:
                log(LOG_LEVEL_INFO, "Found final corner - turning to finish, rfd={: 4d} fd={: 4d} ".format(int(state.right_front_distance_of_wall), int(front_distance)))
                return self.right_corner_action

        return self

    def execute(self):
        state = self.rover.getRoverState()

        left_diagonal_distance = state.radar.radar[315]
        front_distance = state.radar.radar[0]

        gain = 60
        offset = 150

        # Values that worked speed=150, steer=5-7, dist=4
        # self.speed = 150  # 150
        speed = 50  # mm/second - TODO use odo to update to correct value!
        speed_steer_fudge_factor = 5  # 5-7
        speed_distance_fudge_factor = 4   # 4

        min_angle = 1 * math.pi / 180

        steer_speed = speed * speed_steer_fudge_factor
        distance_speed = speed * speed_distance_fudge_factor

        if self.left_or_right == self.RIGHT:
            wall_angle = state.right_wall_angle
            if -min_angle < state.right_wall_angle < min_angle:
                distance = 1000000000
            else:
                distance = steer_speed / state.right_wall_angle
                if 0 <= distance < 150:
                    distance = 150
                elif -150 < distance < 0:
                    distance = -150

            distance = -distance

            distance_from_wall = state.right_wall_distance

            distance_error = distance_from_wall - self.distance

            angle = 0
            if abs(distance_error) < 10:
                angle = 0
            elif distance_error > 0 and distance_error > distance_speed:
                angle = math.pi / 4
            elif distance_error < 0 and distance_error < -distance_speed:
                angle = -math.pi / 4
            else:
                try:
                    angle = math.asin(distance_error / distance_speed)
                except BaseException as ex:
                    log(LOG_LEVEL_ALWAYS, "Domain error wa={: 3d} dw={: 4d} de={: 4d} d={: 4d} s={: 3d}".format(int(wall_angle), int(distance_from_wall), int(distance_error), int(distance), int(speed)))

        else:
            wall_angle = state.left_wall_angle
            if -min_angle < state.left_wall_angle < min_angle:
                distance = 1000000000
            else:
                distance = steer_speed / state.left_wall_angle
                if 0 <= distance < 150:
                    distance = 150
                elif -150 < distance < 0:
                    distance = -150

            distance_from_wall = state.left_wall_distance

            distance_error = distance_from_wall - self.distance

            angle = 0
            if abs(distance_error) < 10:
                angle = 0
            elif distance_error > 0 and distance_error > distance_speed:
                angle = -math.pi / 4
            elif distance_error < 0 and distance_error < -distance_speed:
                angle = math.pi / 4
            else:
                try:
                    angle = -math.asin(distance_error / distance_speed)
                except BaseException as ex:
                    log(LOG_LEVEL_ALWAYS, "Domain error wa={: 3d} dw={: 4d} de={: 4d} d={: 4d} s={: 3d}".format(int(wall_angle), int(distance_from_wall), int(distance_error), int(distance), int(speed)))

        distance = int(distance)
        angle = int(angle * 180 / math.pi)

        self.rover.command(pyroslib.publish, self.speed, angle, distance)
        # pyroslib.publish("move/steer", str(distance) + " " + str(self.speed) + " " + str(angle))

        wheel_orientations = state.wheel_odos.odos
        #
        log(LOG_LEVEL_INFO, "{:16.3f}: dist_f={: 4d} wa={: 3d} dist_w={: 4d} dist_err={: 3d} la={: 3d} ld={: 3d} ra={: 3d} rd={: 3d} s_spd={: 3d} dist_spd={: 3d} dist={: 4d} angle={: 3d} heading={: 3d} odo={:7.2f}".format(
                            float(time.time()),
                            int(front_distance),
                            int(wall_angle * 180 / math.pi), int(distance_from_wall), int(distance_error),
                            int(state.left_wall_angle * 180 / math.pi), int(state.left_front_distance_of_wall), int(state.right_wall_angle * 180 / math.pi), int(state.right_front_distance_of_wall),
                            int(steer_speed), int(distance_speed),
                            int(distance), int(angle), int(state.heading.heading),
                            float(state.wheel_orientations.orientations['fl'])
        ))

    def getActionName(self):
        return "Corridor"


class MazeTurnAroundCornerAction(MazeAction):
    def __init__(self, rover, left_or_right, distance, speed, next_action=None):
        super(MazeTurnAroundCornerAction, self).__init__(rover)
        self.left_or_right = left_or_right
        self.distance = distance * (1 if left_or_right == self.RIGHT else -1)
        self.speed = speed
        self.start_heading = 0
        self.last_heading = 0
        self.requested_heading = 0
        self.pid = None
        self.next_action = next_action
        self.error = 0

    def start(self):
        super(MazeTurnAroundCornerAction, self).start()
        state = self.rover.getRoverState()
        self.start_heading = state.heading.heading
        self.requested_heading = normaiseAngle(self.start_heading + 80 * -(1 if self.left_or_right == self.RIGHT else -1))

        self.pid = PID(1, 0.0, 0.05, 1, 0, diff_method=angleDiference)
        self.pid.process(self.requested_heading, self.start_heading)

        log(LOG_LEVEL_INFO, "Starting to turn around corner at distance {:04d} at speed {:04d}, start heading {:07.3f}, requested heading {:07.3f}".format(self.distance, self.speed, self.start_heading, self.requested_heading))
        self.rover.command(pyroslib.publish, self.speed, 0, self.distance)
        # pyroslib.publish("move/steer", str(self.distance) + " " + str(self.speed))

    def end(self):
        super(MazeTurnAroundCornerAction, self).end()

    def next(self):
        heading = state.heading.heading

        self.error = self.pid.process(self.requested_heading, heading)
        if self.left_or_right == self.LEFT and self.error > 0:
            return self
        elif self.left_or_right == self.RIGHT and self.error < 0:
            return self
        else:
            if self.next_action is not None:
                log(LOG_LEVEL_INFO, "Finished turning around the corner - invoking next action " + self.next_action.getActionName())
            else:
                log(LOG_LEVEL_INFO, "Finishing turning - no next action spectified.")
            return self.next_action

    def execute(self):
        state = self.rover.getRoverState()
        heading = state.heading.heading

        last_heading = self.last_heading
        self.last_heading = heading

        log(LOG_LEVEL_INFO, "Turning speed={:04d} h={:07.3f} lh={:07.3f} dh={:07.3f} rh={:07.3f} e={:07.3f}"
            .format(self.speed, heading, last_heading, angleDiference(heading, last_heading), self.requested_heading, self.error))

    def getActionName(self):
        return "Turn-Around-Corner"


class DriverForwardForTimeAction(Action):
    def __init__(self, rover, time, speed, next_action):
        super(DriverForwardForTimeAction, self).__init__(rover)
        self.time = time
        self.speed = speed
        self.next_action = next_action

    def start(self):
        self.rover.command(pyroslib.publish, self.speed, 0)
        # pyroslib.publish("move/drive", "0 " + str(self.speed))
        log(LOG_LEVEL_INFO, "Going forward for " + str(self.time) + " ticks.")

    def end(self):
        pass

    def next(self):
        if self.time > 0:
            self.time -= 1
            log(LOG_LEVEL_INFO, "Going forward for " + str(self.time) + " ticks.")
            return self

        return self.next_action


if __name__ == "__main__":
    from rover import Radar, RoverState

    radar_values = {0: 10, 45: SQRT2 * 10, 90: 10, 135: SQRT2 * 10, 180: 10, 225: SQRT2 * 10, 270: 10, 315: SQRT2 * 10}
    radar_last_values = {0: 10, 45: SQRT2 * 10, 90: 10, 135: SQRT2 * 10, 180: 10, 225: SQRT2 * 10, 270: 10, 315: SQRT2 * 10}
    radar_status = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0}

    attitude = MazeAttitude()
    radar = Radar(0, radar_values, radar_status, Radar(0, radar_last_values, radar_status))

    state = RoverState(None, None, None, radar, None, None)

    def printWallLines(a):
        if attitude.lines[a].angle is None:
            print("{:3d} -> point too far - not calculated".format(a))
        else:
            angle = int(attitude.lines[a].angle * 180 / math.pi)
            point = attitude.points[a]

            if point is None:
                print("{:3d} -> line at {:3d} angle".format(a, angle))
            else:
                if point == MazeAttitude.LEFT_WALL:
                    wall = "left wall"
                elif point == MazeAttitude.RIGHT_WALL:
                    wall = "right wall"
                elif point == MazeAttitude.FRONT_WALL:
                    wall = "front wall"
                elif point == MazeAttitude.BACK_WALL:
                    wall = "back wall"
                else:
                    wall = "no wall"

                print("{:3d} -> line at {:3d} angle belogs to {:s}".format(a, angle, wall))

    def printWall(w):
        if w.angle is None:
            print("Wall {:3d} -> is too far - not calculated".format(w.ds_angle))
        else:
            if w.distance is None:
                print("Wall {:3d} -> has angle {:3d} but is too far - distance not calculated".format(w.ds_angle, int(w.angle * 180 / math.pi)))
            else:
                print("Wall {:3d} -> has angle {:3d} and is at {:3d}".format(w.ds_angle, int(w.angle * 180 / math.pi), w.distance))

    def printWalls():
        for p in attitude.points:
            printWallLines(p)
        for w in attitude.walls:
            printWall(w)
        print("----------------------------------------------------------")

    # attitude.calculate(state)
    # printWalls()
    #
    # state.radar.radar[0] = 5
    # state.radar.radar[45] = SQRT2 * 5 * 0.9
    # state.radar.radar[315] = SQRT2 * 17
    # state.radar.radar[270] = SQRT2 * 13
    # state.radar.radar[225] = SQRT2 * 12
    # attitude.calculate(state)
    # printWalls()

    state.radar.radar[180] = 50
    state.radar.radar[315] = 30
    attitude.calculate(state)
    printWalls()
