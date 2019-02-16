
#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import math
import time
import traceback

import pyroslib
import pyroslib.logging
from pyroslib.logging import log, DEBUG_LEVEL_ALWAYS, DEBUG_LEVEL_INFO, DEBUG_LEVEL_DEBUG

pyroslib.logging.DEBUG_LEVEL = DEBUG_LEVEL_INFO

sqrt2 = math.sqrt(2)


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
        log(DEBUG_LEVEL_ALWAYS, "Stopped driving...")

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
        self.required_odo = [0, 0, 0, 0]

    def setRequiredOdo(self, distance):
        for i in range(len(self.odo)):
            self.required_odo[i] = distance

    def start(self):
        super(MoveForwardOnOdo, self).start()
        for i in range(len(self.odo)):
            self.odo[i] = 0
        log(DEBUG_LEVEL_DEBUG, "Reset odo to " + str(self.odo) + ", required odo  " + str(self.required_odo) + "; starting...")

        pyroslib.publish("move/steer", "300 120")

    def end(self):
        super(MoveForwardOnOdo, self).end()

    def execute(self):
        do_stop = False
        log(DEBUG_LEVEL_DEBUG, "Driving " + str(self.odo) + " to  " + str(self.required_odo))
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
    def __init__(self, radar):
        super(MazeAction, self).__init__()
        self.radar = radar

    def check_next_action_conditions(self):
        return self


class MazeCorridorAction(MazeAction):
    LEFT = -1
    RIGHT = 1

    def __init__(self, radar, left_or_right, distance):
        super(MazeCorridorAction, self).__init__(radar)
        self.left_or_right = left_or_right
        self.distance = distance
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
        self.odo = [0, 0, 0, 0]
        self.last_odo = [0, 0, 0, 0]
        self.radar = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0}
        self.last_radar = {0: 0, 45: 0, 90: 0, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0}
        self.time_to_send_compact_data = 0
        self.last_execution_time = 0

        self.do_nothing = DoNothing()
        self.stop_action = StopAction(self)
        self.move_forward_on_odo = MoveForwardOnOdo(self.odo, self.radar, self.stop_action)
        self.current_action = self.do_nothing

    def connected(self):
        pyroslib.subscribe("canyons/command", self.handleAgentCommands)
        pyroslib.subscribe("wheel/speed/status", self.handleOdo)
        pyroslib.subscribe("sensor/distance", self.handleRadar)
        pyroslib.publish("canyons/feedback/action", self.current_action.getActionName())
        pyroslib.publish("canyons/feedback/running", self.running)

    def handleAgentCommands(self, topic, message, groups):
        data = message.split(" ")

        log(DEBUG_LEVEL_INFO, "Got command " + message)

        cmd = data[0]
        if cmd == "stop":
            self.stop()
        elif cmd == "start":
            self.start(data[1:])

    def handleOdo(self, topic, message, groups):
        def deltaOdo(old, new):
            d = new - old
            if d > 32768:
                d -= 32768
            elif d < -32768:
                d += 32768

            return d

        data = message.split(",")

        for i in range(4):
            data_index = i * 2
            if data[data_index + 2] == "0":
                newOdo = int(data[data_index + 1])
                delta_odo = deltaOdo(self.last_odo[i], newOdo)
                self.last_odo[i] = newOdo
                self.odo[i] += delta_odo

    def handleRadar(self, topic, message, groups):
        for d in self.radar:
            self.last_radar[d] = self.radar[d]

        values = [v.split(":") for v in message.split(" ")]
        for (k,v) in values:
            if k == 'timestamp':
                timestamp = float(v)
            else:
                self.radar[int(k)] = int(v)

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
        self.nextAction(self.stop_action)

    def start(self, data):
        if not self.running:
            pyroslib.publish("canyons/feedback/running", "True")

            self.running = True

            distance = int((float(data[0]) / 360) * 4096)

            # self.move_forward_on_odo.setRequiredOdo(distance)
            # self.nextAction(self.move_forward_on_odo)

            self.nextAction(MazeCorridorAction(self.radar, MazeCorridorAction.RIGHT, 250))

            log(DEBUG_LEVEL_ALWAYS, "Started driving... for  " + str(distance) + " (" + str(self.move_forward_on_odo.required_odo) + ")")


if __name__ == "__main__":
    try:
        print("Starting canyons-of-mars agent...")

        canyonsOfMarsAgent = CanyonsOfMarsAgent()

        pyroslib.init("canyons-of-mars-agent", unique=True, onConnected=canyonsOfMarsAgent.connected)

        print("Started canyons-of-mars agent.")

        pyroslib.forever(0.02, canyonsOfMarsAgent.execute)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
