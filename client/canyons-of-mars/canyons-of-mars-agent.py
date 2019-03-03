
#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import math
import struct
import telemetry
import time
import traceback

import pyroslib
import pyroslib.logging
from pyroslib.logging import log, LOG_LEVEL_ALWAYS, LOG_LEVEL_INFO, LOG_LEVEL_DEBUG

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


class Heading:
    def __init__(self):
        self.current_heading = 0
        self.start_heading = 0
        self.got_heading = False

    def heading(self):
        return self.current_heading

    def reset(self):
        self.start_heading = -1
        self.got_heading = False

    def process(self, heading):
        self.got_heading = True
        if heading < 0:
            heading += 360
        if self.start_heading == -1:
            self.start_heading = heading
        else:
            heading -= self.start_heading
        if heading < 0:
            heading += 360

        self.current_heading = heading


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


class Radar:
    def __init__(self):
        self.radar = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0, 'timestamp': 0.0}
        self.last_radar = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0, 'timestamp': 0.0}

    def process(self, values):
        for d in self.radar:
            self.last_radar[d] = self.radar[d]

        for (k, v) in values:
            if k == 'timestamp':
                self.radar['timestamp'] = float(v)
            else:
                self.radar[int(k)] = int(v)

    def __getitem__(self, item):
        return self.radar[item]


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
    def __init__(self, odo, radar, stop_action):
        super(MoveForwardOnOdo, self).__init__()
        self.odo = odo
        self.radar = radar
        self.stop_action = stop_action
        self.required_odo = {'fl': 0, 'fr': 0, 'bl': 0, 'br': 0}

    def setRequiredOdo(self, distance):
        for wheel_name in WHEEL_NAMES:
            self.required_odo[wheel_name] = distance

    def start(self):
        super(MoveForwardOnOdo, self).start()
        for wheel in self.odo:
            self.odo.wheelOdos()[wheel] = 0
        log(LOG_LEVEL_DEBUG, "Reset odo to " + str(self.odo) + ", required odo  " + str(self.required_odo) + "; starting...")

        pyroslib.publish("move/steer", "300 120")

    def end(self):
        super(MoveForwardOnOdo, self).end()

    def execute(self):
        do_stop = False
        log(LOG_LEVEL_DEBUG, "Driving " + str(self.odo) + " to  " + str(self.required_odo))
        for wheel_name in WHEEL_NAMES:
            if self.odo[wheel_name] >= self.required_odo[wheel_name]:
                do_stop = True

        if self.radar[0] < 1.0 or self.radar[315] < 1.0 or self.radar[45] < 1.0:
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

    def __init__(self, odo, radar, heading):
        super(MazeAction, self).__init__()
        self.odo = odo
        self.radar = radar
        self.heading = heading
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


class MazeCorridorAction(MazeAction):
    def __init__(self, odo, radar, heading, left_or_right, distance, speed, next_action=None):
        super(MazeCorridorAction, self).__init__(odo, radar, heading)
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

        self.left_corner_action = MazeTurnAroundCornerAction(self.odo, self.radar, self.heading, self.LEFT, self.distance, self.speed, self)
        self.right_corner_action = MazeTurnAroundCornerAction(self.odo, self.radar, self.heading, self.RIGHT, self.distance, self.speed, DriverForwardForTimeActoun(10, self.speed, None))

    def start(self):
        super(MazeCorridorAction, self).start()

    def end(self):
        super(MazeCorridorAction, self).end()

    def _execute(self):

        def calculateAngleAndFrontDistance(df, dm, db):
            dfsqrt2 = df / SQRT2
            dbsqrt2 = db / SQRT2

            if df < db:
                # angle = math.atan2(dfsqrt2, dfsqrt2 - dm) * 180 / math.pi - 90
                angle = math.atan2(dfsqrt2, dfsqrt2 - dm) - math.pi / 2
            else:
                # angle = 90 - math.atan2(dbsqrt2, dbsqrt2 - dm) * 180 / math.pi
                angle = math.pi / 2 - math.atan2(dbsqrt2, dbsqrt2 - dm)

            xf, yf = dfsqrt2, dfsqrt2
            xm, ym = dm, 0
            xb, yb = dbsqrt2, -dbsqrt2

            d = ((ym - yb) * xf + (xb - xm) * yf + (xm * yb - xb * ym)) / math.sqrt((xb - xm) * (xb - xm) + (yb - ym) * (yb - ym))

            return angle, d

        def calculateRealDistance(side_distance, side_angle):
            if side_distance < 1:
                return 0
            return math.sin(math.pi / 2 - side_angle) * side_distance

        left_angle, left_front_distance = calculateAngleAndFrontDistance(self.radar[315], self.radar[270], self.radar[225])
        right_angle, right_front_distance = calculateAngleAndFrontDistance(self.radar[45], self.radar[90], self.radar[135])

        front_distance = self.radar[0]

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
            wall_angle = right_angle
            if -min_angle < right_angle < min_angle:
                distance = 1000000000
            else:
                distance = steer_speed / right_angle
                if 0 <= distance < 150:
                    distance = 150
                elif -150 < distance < 0:
                    distance = -150

            distance = -distance

            distance_from_wall = calculateRealDistance(self.radar[90], right_angle)

            distance_error = distance_from_wall - self.distance

            angle = 0
            if abs(distance_error) < 10:
                angle = 0
            elif distance_error > 0 and distance_error * SQRT2 > distance_speed:
                angle = math.pi / 4
            elif distance_error < 0 and distance_error * SQRT2 < -distance_speed:
                angle = -math.pi / 4
            else:
                try:
                    angle = math.asin(distance_error / distance_speed)
                except BaseException as ex:
                    log(LOG_LEVEL_ALWAYS, "Domain error " + "wa=" + str(wall_angle) + " dw=" + str(distance_from_wall) + " de=" + str(distance_error) + " d=" + str(distance))

        else:
            wall_angle = left_angle
            if -min_angle < left_angle < min_angle:
                distance = 1000000000
            else:
                distance = speed / left_angle
                if 0 <= distance < 150:
                    distance = 150
                elif -150 < distance < 0:
                    distance = -150

            distance_from_wall = calculateRealDistance(self.radar[270], left_angle)

            distance_error = distance_from_wall - self.distance

            angle = 0
            if abs(distance_error) < 10:
                angle = 0
            elif distance_error > 0 and distance_error > speed * SQRT2:
                angle = -math.pi / 4
            elif distance_error < 0 and distance_error < -speed * SQRT2:
                angle = math.pi / 4
            else:
                angle = -math.asin(distance_error / speed)

        distance = int(distance)
        angle = int(angle * 180 / math.pi)

        pyroslib.publish("move/steer", str(distance) + " " + str(self.speed) + " " + str(angle))

        pyroslib.publish("canyons/feedback/corridor",
                         str(int(self.radar[0])) +
                         " " + str(int(self.radar[180])) +
                         " " + str(int(left_angle * 180 / math.pi)) +
                         " " + str(int(right_angle * 180 / math.pi)) +
                         " " + str(int(left_front_distance)) +
                         " " + str(int(right_front_distance))
                         )

        wheel_orientations = self.odo.wheelOrietations()
        corridor_logger.log(time.time(), int(wall_angle * 180 / math.pi), int(distance_from_wall), int(distance_error),
                            int(left_angle * 180 / math.pi), int(left_front_distance), int(right_angle * 180 / math.pi), int(right_front_distance),
                            int(steer_speed), int(distance_speed),
                            int(distance), int(angle), int(self.heading.heading()),
                            float(wheel_orientations['timestamp']),
                            int(wheel_orientations['fl']), int(wheel_orientations['fr']), int(wheel_orientations['bl']), int(wheel_orientations['br']),
                            self.radar['timestamp'])

        log(LOG_LEVEL_INFO, "{:16.3f}: dist_f={: 4d} wa={: 3d} dist_w={: 4d} dist_err={: 3d} la={: 3d} ld={: 3d} ra={: 3d} rd={: 3d} s_spd={: 3d} dist_spd={: 3d} dist={: 4d} angle={: 3d} heading={: 3d} odo={:7.2f}".format(
                            float(time.time()),
                            int(front_distance),
                            int(wall_angle * 180 / math.pi), int(distance_from_wall), int(distance_error),
                            int(left_angle * 180 / math.pi), int(left_front_distance), int(right_angle * 180 / math.pi), int(right_front_distance),
                            int(steer_speed), int(distance_speed),
                            int(distance), int(angle), int(self.heading.heading()),
                            float(self.odo.wheelOdoInmm('fl'))
        ))

        if left_front_distance > 100 and front_distance < 900:
            log(LOG_LEVEL_INFO, "Found corner - turning")
            return self.left_corner_action

        if right_front_distance > 100 and front_distance < 900:
            log(LOG_LEVEL_INFO, "Found final corner - turning to finish")
            return self.right_corner_action

        return self

    def getActionName(self):
        return "Corridor"


class MazeTurnOnSpotWithDistanceAction(MazeAction):
    MODE_SLANT_WHEELS = 1
    MODE_ROTATE = 2

    def __init__(self, odo, radar, heading, distance, speed):
        super(MazeTurnOnSpotWithDistanceAction, self).__init__(odo, radar, heading)
        self.distance = distance
        self.speed = speed
        self.fl_last_odo = 0
        self.travelled = 0
        self.pid = None
        self.mode = self.MODE_SLANT_WHEELS
        self.fl_orientation = 1

    def start(self):
        super(MazeTurnOnSpotWithDistanceAction, self).start()
        self.fl_last_odo = self.odo.wheelOdos()['fl']
        self.travelled = 0
        self.pid = PID(.8, 0.1, 0.2, 1, 5)
        self.pid.process(self.distance, self.travelled)
        pyroslib.publish("move/rotate", "0")
        self.mode = self.MODE_SLANT_WHEELS
        self.pause(10)  # 1 second is enough to finish slanting wheels

    def end(self):
        super(MazeTurnOnSpotWithDistanceAction, self).end()

    def _execute(self):
        if self.mode == self.MODE_SLANT_WHEELS:
            fl_orientation_deg = self.odo.wheelOrietations()['fl']

            pyroslib.publish("move/rotate", str(int(self.speed)))
            if fl_orientation_deg < 180:
                self.fl_orientation = 1
            else:
                self.fl_orientation = -1
            self.mode = self.MODE_ROTATE

            log(LOG_LEVEL_INFO, "FL wheel orientation " + str(fl_orientation_deg) + " modifier " + str(self.fl_orientation))
            return self
        else:
            fl_odo = self.odo.wheelOdos()['fl']
            fl_last_odo = self.fl_last_odo
            self.travelled += self.odo.deltaOdoInmm(self.fl_last_odo, fl_odo) * self.fl_orientation
            self.fl_last_odo = fl_odo

            speed = self.pid.process(self.distance, self.travelled)

            log(LOG_LEVEL_INFO, "Turning speed=" + str(speed) + " odo=" + str(fl_odo) + " last_odo=" + str(fl_last_odo) + " travelled=" + str(self.travelled) + " distance=" + str(self.distance))
            if abs(self.distance - self.travelled) > 5:
                if speed > self.speed:
                    speed = self.speed
                pyroslib.publish("move/rotate", str(int(speed)))
            else:
                log(LOG_LEVEL_INFO, "Turning stop!")
                pyroslib.publish("move/stop", "")
                return None

            return self

    def getActionName(self):
        return "Turn-On-Spot-Distance"


class MazeTurnAroundCornerAction(MazeAction):
    def __init__(self, odo, radar, heading, left_or_right, distance, speed, next_action=None):
        super(MazeTurnAroundCornerAction, self).__init__(odo, radar, heading)
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
        self.start_heading = self.heading.heading()
        self.requested_heading = normaiseAngle(self.start_heading + 90 * -(1 if self.left_or_right == self.RIGHT else -1))

        self.pid = PID(1, 0.0, 0.3, 1, 0, diff_method=angleDiference)
        self.pid.process(self.requested_heading, self.start_heading)

        log(LOG_LEVEL_INFO, "Starting to turn around corner at distance {:04d} at speed {:04d}, start heading {:07.3f}, requested heading {:07.3f}".format(self.distance, self.speed, self.start_heading, self.requested_heading))
        pyroslib.publish("move/steer", str(self.distance) + " " + str(self.speed))

    def end(self):
        super(MazeTurnAroundCornerAction, self).end()

    def _execute(self):
        heading = self.heading.heading()

        error = self.pid.process(self.requested_heading, heading)

        last_heading = self.last_heading
        self.last_heading = heading

        log(LOG_LEVEL_INFO, "Turning speed={:04d} h={:07.3f} lh={:07.3f} dh={:07.3f} rh={:07.3f} e={:07.3f}".format(self.speed, heading, last_heading, angleDiference(heading, last_heading),
                                                                                                      self.requested_heading, error))
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


class WaitForHeading(Action):
    def __init__(self, heading, next_action):
        super(WaitForHeading, self).__init__()
        self.heading = heading
        self.next_action = next_action

    def start(self):
        self.heading.reset()
        pyroslib.publish("position/resume", "")
        pyroslib.publish("position/heading/start", '{"frequency":20}')
        self.heading.got_heading = False
        log(LOG_LEVEL_INFO, "Started a wait for heading to arrive...")

    def end(self):
        pass

    def execute(self):
        if self.heading.got_heading:
            log(LOG_LEVEL_INFO, "Received heading - starting action " + str(self.next_action.getActionName()))
            return self.next_action

        log(LOG_LEVEL_INFO, "Waiting for heading to arrive...")
        return self


class DriverForwardForTimeActoun(Action):
    def __init__(self, time, speed, next_action):
        super(DriverForwardForTimeActoun, self).__init__()
        self.time = time
        self.speed = speed
        self.next_action = next_action

    def start(self):
        pyroslib.publish("move/drive", "0 " + str(self.speed))
        log(LOG_LEVEL_INFO, "Going forward for " + str(self.time) + " ticks.")

    def end(self):
        pass

    def execute(self):
        if self.time > 0:
            self.time -= 1
            log(LOG_LEVEL_INFO, "Going forward for " + str(self.time) + " ticks.")
            return self

        return self.next_action


class CanyonsOfMarsAgent:
    def __init__(self):
        self.running = False
        self.odo = Odo()
        self.radar = Radar()
        self.heading = Heading()
        self.time_to_send_compact_data = 0
        self.last_execution_time = 0

        self.do_nothing = DoNothing()
        self.stop_action = StopAction(self)
        self.move_forward_on_odo = MoveForwardOnOdo(self.odo, self.radar, self.stop_action)
        self.current_action = self.do_nothing

    def connected(self):
        pyroslib.subscribe("canyons/command", self.handleAgentCommands)
        pyroslib.subscribe("wheel/speed/status", self.handleOdoSpeed)
        pyroslib.subscribe("wheel/deg/status", self.handleOdoOrientation)
        pyroslib.subscribe("sensor/distance", self.handleRadar)
        pyroslib.subscribeBinary("sensor/heading/data", self.handleHeading)
        pyroslib.publish("canyons/feedback/action", self.current_action.getActionName())
        pyroslib.publish("canyons/feedback/running", self.running)

    def handleAgentCommands(self, topic, message, groups):
        data = message.split(" ")

        log(LOG_LEVEL_INFO, "Got command " + message)

        cmd = data[0]
        if cmd == "stop":
            self.stop()
        elif cmd == "start":
            self.start(data[1:])

    def handleOdoSpeed(self, topic, message, groups):
        self.odo.processSpeed(message.split(","))

    def handleOdoOrientation(self, topic, message, groups):
        self.odo.processOrientation(message.split(","))

    def handleRadar(self, topic, message, groups):
        self.radar.process([v.split(":") for v in message.split(" ")])

    def handleHeading(self, topic, message, groups):
        heading_data = struct.unpack('>ffff', message)
        # log(LOG_LEVEL_INFO, "heading: " + str(heading_data))
        self.heading.process(heading_data[2])

    def sendCompactData(self):
        pass

    def nextAction(self, action):
        if action != self.current_action:
            self.current_action.end()
            self.current_action = action
            action.start()
            pyroslib.publish("canyons/feedback/action", action.getActionName())

    def execute(self):
        next_action = self.current_action.execute()
        if next_action is None:
            next_action = self.stop_action
        self.nextAction(next_action)

        now = time.time()
        if now >= self.time_to_send_compact_data:
            self.time_to_send_compact_data = now + 0.1
            self.sendCompactData()

    def stop(self):
        self.running = False
        self.heading.reset()
        self.nextAction(self.stop_action)
        pyroslib.publish("position/heading/stop", '')
        pyroslib.publish("position/pause", "")

    def start(self, data):
        if not self.running:
            pyroslib.publish("canyons/feedback/running", "True")

            if data[0] == 'corridor':
                self.running = True
                speed = int(data[1])
                distance = int(data[2])

                # drive_forward_action = DriverForwardForTimeActoun(5, speed, self.stop_action)
                # corner_action = MazeTurnAroundCornerAction(self.odo, self.radar, self.heading, MazeAction.LEFT, distance, speed,next_action=drive_forward_action)
                corridor_action = MazeCorridorAction(self.odo, self.radar, self.heading, MazeAction.RIGHT, distance, speed)
                wait_for_heading_action = WaitForHeading(self.heading, corridor_action)

                self.nextAction(wait_for_heading_action)
            elif data[0] == 'turnCorner':
                self.running = True
                speed = int(data[1])
                distance = int(data[2])

                self.nextAction(WaitForHeading(self.heading, MazeTurnAroundCornerAction(self.odo, self.radar, self.heading, MazeAction.LEFT, distance, speed)))
            elif data[0] == 'turn180':
                self.running = True
                speed = int(data[1])
                distance = int(data[2])

                self.nextAction(WaitForHeading(self.heading, MazeTurnOnSpotWithDistanceAction(self.odo, self.radar, self.heading, distance, speed)))


if __name__ == "__main__":
    try:
        print("Starting canyons-of-mars agent...")

        print("  creating logger...")
        corridor_logger = telemetry.MQTTLocalPipeTelemetryLogger('canyons-corridor')
        corridor_logger.addInt('wall_angle', 2)
        corridor_logger.addInt('distance_wall', 2)
        corridor_logger.addInt('distance_error')
        corridor_logger.addInt('left_angle')
        corridor_logger.addInt('right_angle')
        corridor_logger.addInt('left_distance')
        corridor_logger.addInt('right_distance')
        corridor_logger.addInt('speed_angle')
        corridor_logger.addInt('speed_distance')
        corridor_logger.addInt('distance')
        corridor_logger.addInt('angle')
        corridor_logger.addInt('heading')
        corridor_logger.addDouble('wheel_time')
        corridor_logger.addInt('fld')
        corridor_logger.addInt('frd')
        corridor_logger.addInt('bld')
        corridor_logger.addInt('brd')
        corridor_logger.addDouble('radar_time')

        print("  creating agemt object...")
        canyonsOfMarsAgent = CanyonsOfMarsAgent()

        pyroslib.init("canyons-of-mars-agent", unique=True, onConnected=canyonsOfMarsAgent.connected)

        print("  initialising logger...")
        corridor_logger.init()

        print("Started canyons-of-mars agent.")

        pyroslib.forever(0.1, canyonsOfMarsAgent.execute)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
