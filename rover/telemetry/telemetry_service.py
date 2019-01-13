#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import traceback
import pyroslib

from telemetry_stream import *
from telemetry_storage import *
from telemetry_pyros_logger import *
from telemetry_logger import *
from telemetry_server import *

#
# echo service
#
# This service is just sending echo back to different topic.
#

DEBUG = False


class MQTTLocalPipeTelemetryServer(PubSubLocalPipeTelemetryServer):
    def __init__(self):
        super(MQTTLocalPipeTelemetryServer, self).__init__('telemetry', pyroslib.publish, pyroslib.subscribeBinary)

    def waitAndProcess(self, waitTime=0.02):  # 50 times a second by default
        self.mqtt.loop(waitTime)

    def runForever(self, waitTime=0.02, outer=None):  # 50 times a second by default
        self.mqtt.forever(waitTime, outer)


def handleEcho(topic, payload, groups):
    print("Got echo in " + payload)
    if len(groups) > 0:
        pyroslib.publish("echo/out", groups[0] + ":" + payload)
    else:
        pyroslib.publish("echo/out", "default:" + payload)


if __name__ == "__main__":
    try:
        print("Starting telemetry service...")

        pyroslib.init("telemetry-service")

        server = MQTTLocalPipeTelemetryServer()

        print("Started telemetry service.")

        pyroslib.forever(0.5)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
