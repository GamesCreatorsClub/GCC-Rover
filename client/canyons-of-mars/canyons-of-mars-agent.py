
#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import time
import traceback

import pyroslib
import pyroslib.logging
from pyroslib.logging import log, DEBUG_LEVEL_ALWAYS, DEBUG_LEVEL_INFO, DEBUG_LEVEL_DEBUG

pyroslib.logging.DEBUG_LEVEL = DEBUG_LEVEL_INFO


class Action:
    def __init__(self):
        pass

    def start(self):
        pass

    def end(self):
        pass

    def execute(self):
        return self

    def __repr__(self):
        return "not defined"


class DoNothing(Action):
    def __init__(self):
        super(DoNothing, self).__init__()

    def __repr__(self):
        return "Do-Nothing"


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

    def __repr__(self):
        return "Stop-Action"


class MoveForwardOnOdo(Action):
    def __init__(self, odo, stop_action):
        super(MoveForwardOnOdo, self).__init__()
        self.odo = odo
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

        if do_stop:
            return self.stop_action
        else:
            return self

    def __repr__(self):
        return "Move-Forward-Action"


class CanyonsOfMarsAgent:
    def __init__(self):
        self.running = False
        self.odo = [0, 0, 0, 0]
        self.last_odo = [0, 0, 0, 0]
        self.time_to_send_compact_data = 0
        self.last_execution_time = 0

        self.do_nothing = DoNothing()
        self.stop_action = StopAction(self)
        self.move_forward_on_odo = MoveForwardOnOdo(self.odo, self.stop_action)
        self.current_action = self.do_nothing

    def connected(self):
        pyroslib.subscribe("canyons/command", self.handleAgentCommands)
        pyroslib.subscribe("wheel/speed/status", self.handleOdo)
        # pyroslib.publish("sensor/gyro/continuous", "calibrate,50")
        pass

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

    def handleAgentCommands(self, topic, message, groups):
        data = message.split(" ")

        log(DEBUG_LEVEL_INFO, "Got command " + message)

        cmd = data[0]
        if cmd == "stop":
            self.stop()
        elif cmd == "start":
            self.start(data[1:])

    def sendCompactData(self):
        pass

    def nextAction(self, action):
        if action != self.current_action:
            self.current_action.end()
            self.current_action = action
            action.start()

    def execute(self):
        next_action = self.current_action.execute()
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

            self.move_forward_on_odo.setRequiredOdo(distance)
            self.nextAction(self.move_forward_on_odo)

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
