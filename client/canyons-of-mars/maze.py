
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
from rover import Rover, WheelOdos, WHEEL_NAMES
from rover import normaiseAngle, angleDiference

SQRT2 = math.sqrt(2)


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


class Action:
    def __init__(self):
        pass

    def start(self):
        pass

    def end(self):
        pass

    def execute(self):
        return self

    def getActionName(self):
        return "Stop"


class DoNothing(Action):
    def __init__(self):
        super(DoNothing, self).__init__()

    def getActionName(self):
        return "Ready"


class StopAction(Action):
    def __init__(self, parent):
        super(StopAction, self).__init__()
        self.parent = parent

    def start(self):
        super(StopAction, self).start()
        self.parent.running = False
        pyroslib.publish("move/stop", "")
        pyroslib.publish("canyons/feedback/running", "False")
        log(LOG_LEVEL_ALWAYS, "Stopped driving...")

    def execute(self):
        return self.parent.do_nothing

    def getActionName(self):
        return "Stop"


class MoveForwardOnOdo(Action):
    def __init__(self, rover, stop_action=None):
        super(MoveForwardOnOdo, self).__init__()
        self.rover = rover
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

    def execute(self):
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

    def getActionName(self):
        return "Forward ODO"


class MazeAction(Action):
    LEFT = -1
    RIGHT = 1

    def __init__(self, rover):
        super(MazeAction, self).__init__()
        self.rover = rover
        self.paused = 0

    def check_next_action_conditions(self):
        return self

    def _execute(self):
        pass

    def execute(self):
        if self.paused > 0:
            self.paused -= 1
            return self

        return self._execute()

    def pause(self, ticks):
        self.paused = ticks


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
        self.right_corner_action = MazeTurnAroundCornerAction(self.rover, self.RIGHT, self.distance, self.speed, DriverForwardForTimeActoun(self.rover, 10, self.speed, None))

    def start(self):
        super(ChicaneAction, self).start()

    def end(self):
        super(ChicaneAction, self).end()

    def _execute(self):
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

        self.left_corner_action = MazeTurnAroundCornerAction(self.rover, self.LEFT, self.distance, self.speed, self)
        self.right_corner_action = MazeTurnAroundCornerAction(self.rover, self.RIGHT, self.distance, self.speed, self)
        # self.right_corner_action = MazeTurnAroundCornerAction(self.odo, self.radar, self.heading, self.RIGHT, self.distance, self.speed, DriverForwardForTimeActoun(10, self.speed, None))

    def start(self):
        super(MazeCorridorAction, self).start()

    def end(self):
        super(MazeCorridorAction, self).end()

    def _execute(self):
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

        if state.left_front_distance_of_wall > 100 and front_distance < 700:
            expected_diagonal_distance = 0
            if state.left_wall_angle < 0:
                expected_diagonal_distance = front_distance * 2 * math.cos(math.pi / 4 + state.left_wall_angle)
            else:
                expected_diagonal_distance = front_distance * math.cos(state.left_wall_angle) * SQRT2

            if front_distance > 300 and left_diagonal_distance > expected_diagonal_distance * 1.1:
                log(LOG_LEVEL_INFO, "Found chicane... lfd={: 4d} fd={: 4d} dd={: 4d} ed={: 4d}".format(int(state.left_front_distance_of_wall), int(front_distance), int(left_diagonal_distance), int(expected_diagonal_distance)))
                return ChicaneAction(self.rover, self.LEFT, self.distance, self.speed, next_action=self)
            else:
                log(LOG_LEVEL_INFO, "Found corner - turning, lfd={: 4d} fd={: 4d} dd={: 4d}  ed={: 4d}".format(int(state.left_front_distance_of_wall), int(front_distance), int(left_diagonal_distance), int(expected_diagonal_distance)))
                return self.left_corner_action

        if state.right_front_distance_of_wall > 100 and front_distance < 900:
            log(LOG_LEVEL_INFO, "Found final corner - turning to finish, rfd={: 4d} fd={: 4d} ".format(int(state.right_front_distance_of_wall), int(front_distance)))
            return self.right_corner_action

        return self

    def getActionName(self):
        return "Corridor"


class MazeTurnOnSpotWithDistanceAction(MazeAction):
    MODE_SLANT_WHEELS = 1
    MODE_ROTATE = 2

    def __init__(self, rover, distance, speed):
        super(MazeTurnOnSpotWithDistanceAction, self).__init__(rover)
        self.distance = distance
        self.speed = speed
        self.fl_last_odo = 0
        self.travelled = 0
        self.pid = None
        self.mode = self.MODE_SLANT_WHEELS
        self.fl_orientation = 1

    def start(self):
        super(MazeTurnOnSpotWithDistanceAction, self).start()
        state = self.rover.getRoverState()
        self.fl_last_odo = state.wheel_odos.odos['fl']
        self.travelled = 0
        self.pid = PID(.8, 0.1, 0.2, 1, 5)
        self.pid.process(self.distance, self.travelled)
        self.rover.command(pyroslib.publish, 0, 0, 0)
        # pyroslib.publish("move/rotate", "0")
        self.mode = self.MODE_SLANT_WHEELS
        self.pause(10)  # 1 second is enough to finish slanting wheels

    def end(self):
        super(MazeTurnOnSpotWithDistanceAction, self).end()

    def _execute(self):
        state = self.rover.getRoverState()
        if self.mode == self.MODE_SLANT_WHEELS:
            fl_orientation_deg = state.wheel_odos.odos['fl']

            self.rover.command(pyroslib.publish, self.speed, 0, 0)
            # pyroslib.publish("move/rotate", str(int(self.speed)))
            if fl_orientation_deg < 180:
                self.fl_orientation = 1
            else:
                self.fl_orientation = -1
            self.mode = self.MODE_ROTATE

            log(LOG_LEVEL_INFO, "FL wheel orientation " + str(fl_orientation_deg) + " modifier " + str(self.fl_orientation))
            return self
        else:
            fl_odo = state.wheel_odos.odos['fl']
            fl_last_odo = self.fl_last_odo
            self.travelled += state.wheel_odos.deltaOdoInmm(self.fl_last_odo, fl_odo) * self.fl_orientation
            self.fl_last_odo = fl_odo

            speed = self.pid.process(self.distance, self.travelled)

            log(LOG_LEVEL_INFO, "Turning speed=" + str(speed) + " odo=" + str(fl_odo) + " last_odo=" + str(fl_last_odo) + " travelled=" + str(self.travelled) + " distance=" + str(self.distance))
            if abs(self.distance - self.travelled) > 5:
                if speed > self.speed:
                    speed = self.speed
                self.rover.command(pyroslib.publish, 0, 0, 0)
                # pyroslib.publish("move/rotate", str(int(speed)))
            else:
                log(LOG_LEVEL_INFO, "Turning stop!")
                self.rover.command(pyroslib.publish, 0, 0)
                # pyroslib.publish("move/stop", "")
                return None

            return self

    def getActionName(self):
        return "Turn-On-Spot-Distance"


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

    def start(self):
        super(MazeTurnAroundCornerAction, self).start()
        state = self.rover.getRoverState()
        self.start_heading = state.heading.heading
        self.requested_heading = normaiseAngle(self.start_heading + 90 * -(1 if self.left_or_right == self.RIGHT else -1))

        self.pid = PID(1, 0.0, 0.3, 1, 0, diff_method=angleDiference)
        self.pid.process(self.requested_heading, self.start_heading)

        log(LOG_LEVEL_INFO, "Starting to turn around corner at distance {:04d} at speed {:04d}, start heading {:07.3f}, requested heading {:07.3f}".format(self.distance, self.speed, self.start_heading, self.requested_heading))
        self.rover.command(pyroslib.publish, self.speed, 0, self.distance)
        # pyroslib.publish("move/steer", str(self.distance) + " " + str(self.speed))

    def end(self):
        super(MazeTurnAroundCornerAction, self).end()

    def _execute(self):
        state = self.rover.getRoverState()
        heading = state.heading.heading

        error = self.pid.process(self.requested_heading, heading)

        last_heading = self.last_heading
        self.last_heading = heading

        log(LOG_LEVEL_INFO, "Turning speed={:04d} h={:07.3f} lh={:07.3f} dh={:07.3f} rh={:07.3f} e={:07.3f}"
            .format(self.speed, heading, last_heading, angleDiference(heading, last_heading), self.requested_heading, error))
        if self.left_or_right == self.LEFT and error > 0:
            return self
        elif self.left_or_right == self.RIGHT and error < 0:
            return self
        else:
            if self.next_action is not None:
                log(LOG_LEVEL_INFO, "Finished turning around the corner - invoking next action " + self.next_action.getActionName())
            else:
                log(LOG_LEVEL_INFO, "Finishing turning - no next action spectified.")
            return self.next_action

    def getActionName(self):
        return "Turn-Around-Corner"


class WaitSensorData(Action):
    def __init__(self, rover: Rover, next_action):
        super(WaitSensorData, self).__init__()
        self.rover = rover
        self.next_action = next_action

    def start(self):
        pyroslib.publish("position/resume", "")
        pyroslib.publish("sensor/distance/resume", "")
        pyroslib.publish("position/heading/start", '{"frequency":20}')
        log(LOG_LEVEL_INFO, "Started a wait for all sensor data to arrive...")

    def execute(self):
        if self.rover.hasCompleteState():
            log(LOG_LEVEL_INFO, "Received all sensor data - starting action " + str(self.next_action.getActionName()))
            return self.next_action

        log(LOG_LEVEL_INFO, "Waiting for sensor data to arrive...")
        return self


class DriverForwardForTimeActoun(Action):
    def __init__(self, rover, time, speed, next_action):
        super(DriverForwardForTimeActoun, self).__init__()
        self.rover = rover
        self.time = time
        self.speed = speed
        self.next_action = next_action

    def start(self):
        self.rover.command(pyroslib.publish, self.speed, 0)
        # pyroslib.publish("move/drive", "0 " + str(self.speed))
        log(LOG_LEVEL_INFO, "Going forward for " + str(self.time) + " ticks.")

    def end(self):
        pass

    def execute(self):
        if self.time > 0:
            self.time -= 1
            log(LOG_LEVEL_INFO, "Going forward for " + str(self.time) + " ticks.")
            return self

        return self.next_action
