#
# Copyright 2019 Games Creators Club
#
# MIT License
#

import pyroslib


from telemetry import TelemetryLogger, LocalPipeTelemetryLoggerDestination, PubSubTelemetryLoggerClient


class MQTTLocalPipeTelemetryLogger(TelemetryLogger):
    def __init__(self, stream_name, host="localhost", port=1883, topic=None):
        if topic is None:
            topic = "telemetry" if pyroslib.getClusterId() == "master" else pyroslib.getClusterId() + ":telemetry"
        super(MQTTLocalPipeTelemetryLogger, self).__init__(stream_name,
                                                           destination=LocalPipeTelemetryLoggerDestination(),
                                                           telemetry_client=PubSubTelemetryLoggerClient(topic, pyroslib.publish, pyroslib.subscribeBinary))

    def init(self):
        print("    set up topic " + self.telemetry_client.topic)

        print("    waiting for pyros to connect...")
        while not pyroslib.isConnected():
            pyroslib.loop(0.02)
        print("    pyros to connected.")

        print("    regitering stream " + str(self.name) + "...")
        super(MQTTLocalPipeTelemetryLogger, self).init()
        print("    stream " + str(self.name) + " registration sent.")

        print("    waiting for regitration to finish...")
        while not self.stream_ready and self.registration_error == 0:
            pyroslib.loop(0.02)
        print("    stream " + str(self.name) + " registered.")
