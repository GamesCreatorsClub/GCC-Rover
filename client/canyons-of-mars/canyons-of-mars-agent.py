
#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import math
import struct
import time
import traceback

import pyroslib
import pyroslib.logging
from pyroslib.logging import log, LOG_LEVEL_ALWAYS, LOG_LEVEL_INFO, LOG_LEVEL_DEBUG

pyroslib.logging.LOG_LEVEL = LOG_LEVEL_INFO

sqrt2 = math.sqrt(2)

wheel_names = ['fl', 'fr', 'bl', 'bl']


class Heading:
    def __init__(self):
        self.current_heading = 0
        self.start_heading = 0

    def heading(self):
        return self.heading

    def reset(self):
        self.start_heading = -1

    def process(self, heading):
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
        self.odo = {'fl':0, 'fr':0, 'bl':0, 'br':0}
        self.last_odo = {'fl':0, 'fr':0, 'bl':0, 'br':0}
        self.wheel_speeds = {'fl':0, 'fr':0, 'bl':0, 'br':0}
        self.last_odo_data = 0
        self.odo_delta_time = 0

        self.wheel_orientation = {'fl':0, 'fr':0, 'bl':0, 'br':0}
        self.last_wheel_orientation = {'fl':0, 'fr':0, 'bl':0, 'br':0}
        self.wheel_rot_speeds = {'fl':0, 'fr':0, 'bl':0, 'br':0}
        self.last_speed_data = 0
        self.speed_delta_time = 0

    def wheelOdos(self):
        return self.odo

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
        for wheel in wheel_names:
            distance = self.odo[wheel] - self.last_odo[wheel]
            total = addAngles(total, (distance, self.wheel_orientation[wheel]))

        return total[0] / (4 * self.odo_delta_time) , total[1]

    def wheelOrietations(self):
        return self.wheel_orientation

    def wheelOrientationalSpeeda(self):
        return self.wheel_rot_speeds

    def processSpeed(self, data):
        def deltaOdo(old, new):
            d = new - old
            if d > 32768:
                d -= 32768
            elif d < -32768:
                d += 32768

            return d

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
                delta_odo = deltaOdo(self.last_odo[wheel_names[i]], new_odo)
                self.last_odo[wheel_names[i]] = new_odo
                self.odo[wheel_names[i]] += delta_odo


    def processOrientation(self, data):
        def deltaDeg(old, new):
            d = (int(new) - int(old)) % 360
            if d < 0:
                d += 360
            return d

        for i in range(4):
            data_index = i * 2
            if data[data_index + 2] == "32":
                new_deg = int(data[data_index + 1])
                delta_deg = deltaDeg(self.last_wheel_orientation[wheel_names[i]], new_deg)
                self.last_wheel_orientation[wheel_names[i]] = new_deg
                self.wheel_orientation[wheel_names[i]] += delta_deg


class Radar:
    def __init__(self):
        self.radar = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0}
        self.last_radar = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0}

    def process(self, values):
        for d in self.radar:
            self.last_radar[d] = self.radar[d]

        for (k,v) in values:
            if k == 'timestamp':
                timestamp = float(v)
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
        self.required_odo = {'fl':0, 'fr':0, 'bl':0, 'br':0}

    def setRequiredOdo(self, distance):
        for i in range(len(self.odo)):
            self.required_odo[i] = distance

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
        for i in range(4):
            if self.odo[i] >= self.required_odo[i]:
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
    def __init__(self, odo, radar, heading):
        super(MazeAction, self).__init__()
        self.odo = odo
        self.radar = radar
        self.heading = heading

    def check_next_action_conditions(self):
        return self


class MazeCorridorAction(MazeAction):
    LEFT = -1
    RIGHT = 1

    def __init__(self, odo, radar, heading, left_or_right, distance, speed):
        super(MazeCorridorAction, self).__init__(odo, radar, heading)
        self.left_or_right = left_or_right
        self.distance = distance
        self.speed = speed
        if self.left_or_right == MazeCorridorAction.RIGHT:
            self.a1 = 45
            self.a2 = 90
            self.a3 = 135
        else:
            self.a1 = 315
            self.a2 = 270
            self.a3 = 225

    def start(self):
        super(MazeCorridorAction, self).start()

    def end(self):
        super(MazeCorridorAction, self).end()

    def execute(self):

        def calculateAngleAndFrontDistance(df, dm, db):
            dfsqrt2 = df / sqrt2
            dbsqrt2 = db / sqrt2

            if df < db:
                angle = math.atan2(dfsqrt2, dfsqrt2 - dm) * 180 / math.pi - 90
            else:
                angle = 90 - math.atan2(dbsqrt2, dbsqrt2 - dm) * 180 / math.pi

            xf, yf = dfsqrt2, dfsqrt2
            xm, ym = dm, 0
            xb, yb = dbsqrt2, -dbsqrt2

            d = ((ym - yb) * xf + (xb - xm) * yf + (xm * yb - xb * ym)) / math.sqrt((xb - xm) * (xb - xm) + (yb - ym) * (yb - ym))

            return angle, d

        left_angle, left_front_distance = calculateAngleAndFrontDistance(self.radar[315], self.radar[270], self.radar[225])
        right_angle, right_front_distance = calculateAngleAndFrontDistance(self.radar[45], self.radar[90], self.radar[135])

        gain = 60
        offset = 150

        if right_angle > 40:
            distance = -offset
        elif right_angle < -40:
            distance = offset
        elif right_angle > 0:
            distance = 40 - right_angle
            distance *= -gain

            distance -= offset
        else:
            distance = 40 + right_angle
            distance *= gain
            distance += offset

        distance = int(distance)

        log(LOG_LEVEL_INFO, "Distance is " + str(distance))

        pyroslib.publish("move/steer", str(distance) + " " + str(self.speed))

        pyroslib.publish("canyons/feedback/corridor",
                         str(int(self.radar[0])) +
                         " " + str(int(self.radar[180])) +
                         " " + str(int(left_angle)) +
                         " " + str(int(right_angle)) +
                         " " + str(int(left_front_distance)) +
                         " " + str(int(right_front_distance))
                         )
        return self

    def getActionName(self):
        return "Corridor"


class MazeCornerAction(MazeAction):
    LEFT = -1
    RIGHT = 1

    def __init__(self, odo, radar, heading, left_or_right, distance, speed):
        super(MazeCornerAction, self).__init__(odo, radar, heading)
        self.left_or_right = left_or_right
        self.distance = distance
        self.speed = speed
        if self.left_or_right == MazeCorridorAction.RIGHT:
            self.a1 = 45
            self.a2 = 90
            self.a3 = 135
        else:
            self.a1 = 315
            self.a2 = 270
            self.a3 = 225

    def start(self):
        super(MazeCornerAction, self).start()

    def end(self):
        super(MazeCornerAction, self).end()

    def execute(self):

        def calculateAngleAndFrontDistance(df, dm, db):
            dfsqrt2 = df / sqrt2
            dbsqrt2 = db / sqrt2

            if df < db:
                angle = math.atan2(dfsqrt2, dfsqrt2 - dm) * 180 / math.pi - 90
            else:
                angle = 90 - math.atan2(dbsqrt2, dbsqrt2 - dm) * 180 / math.pi

            xf, yf = dfsqrt2, dfsqrt2
            xm, ym = dm, 0
            xb, yb = dbsqrt2, -dbsqrt2

            d = ((ym - yb) * xf + (xb - xm) * yf + (xm * yb - xb * ym)) / math.sqrt((xb - xm) * (xb - xm) + (yb - ym) * (yb - ym))

            return angle, d

        left_angle, left_front_distance = calculateAngleAndFrontDistance(self.radar[315], self.radar[270], self.radar[225])
        right_angle, right_front_distance = calculateAngleAndFrontDistance(self.radar[45], self.radar[90], self.radar[135])

        gain = 60
        offset = 150

        if right_angle > 40:
            distance = -offset
        elif right_angle < -40:
            distance = offset
        elif right_angle > 0:
            distance = 40 - right_angle
            distance *= -gain

            distance -= offset
        else:
            distance = 40 + right_angle
            distance *= gain
            distance += offset

        distance = int(distance)

        log(LOG_LEVEL_INFO, "Distance is " + str(distance))

        pyroslib.publish("move/steer", str(distance) + " " + str(self.speed))

        pyroslib.publish("canyons/feedback/corridor",
                         str(int(self.radar[0])) +
                         " " + str(int(self.radar[180])) +
                         " " + str(int(left_angle)) +
                         " " + str(int(right_angle)) +
                         " " + str(int(left_front_distance)) +
                         " " + str(int(right_front_distance))
                         )
        return self

    def getActionName(self):
        return "Corridor"


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
        pyroslib.subscribe("wheel/def/status", self.handleOdoOrientation)
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

    def start(self, data):
        if not self.running:
            pyroslib.publish("position/heading/start", '{"frequency":20}')
            pyroslib.publish("canyons/feedback/running", "True")

            self.running = True

            speed = int(data[0])

            self.nextAction(MazeCorridorAction(self.odo, self.radar, self.heading, MazeCorridorAction.RIGHT, 300, speed))


if __name__ == "__main__":
    try:
        print("Starting canyons-of-mars agent...")

        canyonsOfMarsAgent = CanyonsOfMarsAgent()

        pyroslib.init("canyons-of-mars-agent", unique=True, onConnected=canyonsOfMarsAgent.connected)

        print("Started canyons-of-mars agent.")

        pyroslib.forever(0.1, canyonsOfMarsAgent.execute)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
