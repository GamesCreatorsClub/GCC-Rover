
#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import pyroslib
import pyroslib.logging
import telemetry

from pyroslib.logging import log, LOG_LEVEL_ALWAYS, LOG_LEVEL_INFO

from rover import Rover, RoverState


class Action:
    def __init__(self, rover):
        self.rover = rover

    def start(self):
        pass

    def end(self):
        pass

    def next(self):
        return self

    def execute(self):
        pass

    def getActionName(self):
        return "Stop"


class DoNothing(Action):
    def __init__(self, rover):
        super(DoNothing, self).__init__(rover)

    def getActionName(self):
        return "Ready"


class StopAction(Action):
    def __init__(self, rover, parent):
        super(StopAction, self).__init__(rover)
        self.parent = parent

    def start(self):
        super(StopAction, self).start()
        self.parent.stop()

    def getActionName(self):
        return "Stop"


class WaitSensorData(Action):
    def __init__(self, rover: Rover, next_action):
        super(WaitSensorData, self).__init__(rover)
        self.next_action = next_action
        self.countdown = 0
        self.initial_countdown = 4

    def start(self):
        self.countdown = self.initial_countdown
        pyroslib.publish("position/resume", "")
        pyroslib.publish("sensor/distance/resume", "")
        pyroslib.publish("position/heading/start", '{"frequency":20}')
        log(LOG_LEVEL_INFO, "Started a wait for all sensor data to arrive...")

    def next(self):
        if self.rover.hasHeading():
            if self.countdown == self.initial_countdown:
                pyroslib.publish("position/calibrate", "")
            self.countdown -= 1

        if self.rover.hasCompleteState() and self.countdown <= 0:
            self.rover.start_heading_value = self.rover.heading.heading + self.rover.start_heading_value
            log(LOG_LEVEL_INFO, "Received all sensor data - starting action " + str(self.next_action.getActionName()))
            return self.next_action

        return self

    def execute(self):
        log(LOG_LEVEL_INFO, "Waiting for sensor data to arrive...")

    def getActionName(self):
        return "Waiting Sensors"


class WarmupAction(Action):
    def __init__(self, rover: Rover):
        super(WarmupAction, self).__init__(rover)

    def start(self):
        pyroslib.publish("position/resume", "")
        pyroslib.publish("sensor/distance/resume", "")
        pyroslib.publish("position/heading/start", '{"frequency":20}')

    def getActionName(self):
        return "Warmup"


class AgentClass:
    def __init__(self, prefix):
        self.prefix = prefix
        log(LOG_LEVEL_INFO, "  Creating logger...")
        self.state_logger = RoverState.defineLogger(telemetry.MQTTLocalPipeTelemetryLogger('rover-state'))
        self.running = False
        self.rover = Rover()
        self.last_execution_time = 0

        self.do_nothing = DoNothing(self.rover)
        self.stop_action = StopAction(self.rover, self)
        self.current_action = self.do_nothing

    def connected(self):
        pyroslib.subscribe(self.prefix + "/command", self.handleAgentCommands)
        pyroslib.subscribe("wheel/speed/status", self.rover.handleOdo)
        pyroslib.subscribe("wheel/deg/status", self.rover.handleWheelOrientation)
        pyroslib.subscribe("sensor/distance", self.rover.handleRadar)
        pyroslib.subscribeBinary("sensor/heading/data", self.rover.handleHeading)

        pyroslib.publish(self.prefix + "/feedback/action", self.current_action.getActionName())
        pyroslib.publish(self.prefix + "/feedback/running", self.running)

    def register_logger(self):
        log(LOG_LEVEL_INFO, "  Registering logger...")
        self.state_logger.init()
        log(LOG_LEVEL_INFO, "  Registered logger.")

    def handleAgentCommands(self, topic, message, groups):
        data = message.split(" ")

        log(LOG_LEVEL_INFO, "Got command " + message)
        self.receivedAgentCommand(data)

    def receivedAgentCommand(self, cmd_data):
        cmd = cmd_data[0]
        if cmd == "stop":
            self.stop()
        elif cmd == "start":
            self.start(cmd_data[1:])

    def nextAction(self, action):
        if action != self.current_action:
            self.current_action.end()
            if action is None:
                action = self.stop_action
            log(LOG_LEVEL_INFO, "Swapping action " + str(self.current_action.getActionName()) + " to " + str(action.getActionName()))
            self.current_action = action
            action.start()
            pyroslib.publish(self.prefix + "/feedback/action", action.getActionName())

    def mainLoop(self):
        state = self.rover.nextState()
        state.calculate()
        next_action = self.current_action.next()
        if next_action is None:
            next_action = self.stop_action
        if next_action != self.current_action:
            self.nextAction(next_action)

        if self.running:
            self.current_action.execute()
            state.log(self.state_logger, self.current_action.getActionName()[:12])

    def stop(self):
        self.running = False
        self.rover.reset()
        self.nextAction(self.stop_action)
        pyroslib.publish("move/stop", "")
        pyroslib.publish("canyons/feedback/running", "False")
        pyroslib.publish("position/heading/stop", '')
        pyroslib.publish("position/pause", "")
        pyroslib.publish("sensor/distance/pause", "")
        log(LOG_LEVEL_ALWAYS, "Stopped rover...")

    def start(self, data):
        pass
