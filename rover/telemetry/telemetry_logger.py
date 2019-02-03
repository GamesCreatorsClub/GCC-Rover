#
# Copyright 2019 Games Creators Club
#
# MIT License
#

import os
import struct
import uuid

from telemetry import TelemetryStreamDefinition


class TelemetryLoggerDestination:
    def __init__(self):
        pass

    def log(self, stream, time_stamp, *args):
        raise NotImplemented()


class LocalPipeTelemetryLoggerDestination(TelemetryLoggerDestination):
    def __init__(self, telemetry_fifo="~/telemetry-fifo"):
        super(LocalPipeTelemetryLoggerDestination, self).__init__()

        telemetry_fifo = os.path.expanduser(telemetry_fifo)

        self.telemetry_fifo = telemetry_fifo

        if not os.path.exists(telemetry_fifo):
            os.mkfifo(telemetry_fifo)

        self.pipe_fd = os.open(telemetry_fifo, os.O_NONBLOCK | os.O_WRONLY)

        self.pipe = os.fdopen(self.pipe_fd, 'wb', buffering=0)

    def log(self, stream, time_stamp, *args):
        if stream.fixed_length is None:
            raise NotImplemented("Variable record size len is not yet implemented")

        record = struct.pack(stream.pack_string, time_stamp, *args)

        self.pipe.write(stream.header + record)
        # self.pipe.write(record)


class LocalMemoryTelemetryLoggerDestination(TelemetryLoggerDestination):
    def __init__(self):
        super(LocalMemoryTelemetryLoggerDestination, self).__init__()


class SocketTelemetryLoggerDestination(TelemetryLoggerDestination):
    def __init__(self):
        super(SocketTelemetryLoggerDestination, self).__init__()


class TelemetryLoggerClient:
    def __init__(self):
        pass

    def registerStream(self, stream, callback):
        raise NotImplemented()


class SocketTelemetryLoggerClient(TelemetryLoggerClient):
    def __init__(self):
        super(SocketTelemetryLoggerClient, self).__init__()


class PubSubTelemetryLoggerClient(TelemetryLoggerClient):
    def __init__(self, topic, pub_method, sub_method):
        super(PubSubTelemetryLoggerClient, self).__init__()
        self.topic = topic
        self.pub_method = pub_method
        self.sub_method = sub_method
        self.unique_id = str(uuid.uuid4())
        self.registration_callback = None
        self.registration_topic = self.topic + "/register_" + self.unique_id

        self.sub_method(self.registration_topic, self._handleRegistration)

    def _handleRegistration(self, topic, payload):
        stream_id = int(payload)
        self.registration_callback(stream_id)

    def registerStream(self, stream, callback):
        self.registration_callback = callback
        self.pub_method(self.topic + "/register", self.registration_topic + "," + stream.toJSON())


class TelemetryLogger(TelemetryStreamDefinition):
    # Logs to a stream
    def __init__(self, stream_name, destination=None, telemetry_client=None):
        super(TelemetryLogger, self).__init__(stream_name)
        self.stream_ready = False
        self.registration_error = 0
        if destination is None:
            self.destination = LocalPipeTelemetryLoggerDestination()
        else:
            self.destination = destination
        self.telemetry_client = telemetry_client

    def _finishRegistration(self, stream_id):
        if stream_id > 0:
            self.build(stream_id)
            self.stream_ready = True
        else:
            self.registration_error = stream_id
            # TODO - what now?
            pass

    def init(self):
        self.telemetry_client.registerStream(self, self._finishRegistration)

    def log(self, time_stamp, *args):
        if self.stream_ready:
            self.destination.log(self, time_stamp, *args)
        elif self.registration_error == 0:
            raise RuntimeError("Stream has not been registered, yet")
        else:
            raise RuntimeError("Stream registration failed; error code " + str(self.registration_error))