
#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import os
import pyros
import time

from rover import Rover, RoverState
from telemetry import TelemetryStreamDefinition
from telemetry.telemetry_client import PubSubTelemetryClient


class PyrosTelemetryClient(PubSubTelemetryClient):
    def __init__(self, publish_method, subscribe_method, topic='telemetry'):
        super(PyrosTelemetryClient, self).__init__(topic, publish_method, subscribe_method)


class TelemetryUtil:
    def __init__(self, topic="telemetry"):
        self.client = PyrosTelemetryClient(pyros.publish, pyros.subscribeBinary, topic=topic)
        self.stream = None
        self.step = 10  # 15 seconds a time
        self.finished_downloading = False
        self.timestamp = None
        self.recordCallback = None
        self.error = None

    def processStreamDef(self, stream_def):
        if stream_def is None:
            print("No such stream")
            self.error = "No such stream"
        else:
            self.stream = stream_def
            self.client.getOldestTimestamp(self.stream, self.processOldestTimestamp)

    def processOldestTimestamp(self, oldest_timestamp, records_count):
        self.timestamp = oldest_timestamp
        if oldest_timestamp == 0.0:
            print("Telemetry: The oldest timestamp is " + str(oldest_timestamp) + " (there are no records) and there are " + str(records_count) + " records.")
        else:
            print("Telemetry: The oldest timestamp is " + str(oldest_timestamp) + " (it is " + str(time.time() - oldest_timestamp) + "s ago) and there are " + str(records_count) + " records.")

        if records_count > 0:
            self.client.retrieve(self.stream, self.timestamp, self.timestamp + self.step, self.processData)

    def processData(self, records):
        self.timestamp += self.step

        for record in records:
            if self.recordCallback is not None:
                self.recordCallback(record)

        if self.timestamp > time.time() or len(records) == 0:
            self.client.trim(self.stream, time.time())

            self.finished_downloading = True
            return

        self.client.trim(self.stream, self.timestamp)

        self.client.retrieve(self.stream, self.timestamp, self.timestamp + self.step, self.processData)

    def fetchData(self, stream_name, recordCallback):
        self.stream = None
        self.finished_downloading = False
        self.timestamp = None
        self.error = None
        self.recordCallback = recordCallback
        self.client.getStreamDefinition(stream_name, self.processStreamDef)


class RunLog:
    def __init__(self, rover):
        self.rover = rover
        self.logger_def = RoverState.defineLogger(TelemetryStreamDefinition('rover-state'))
        self.records = []
        self.ptr = 0
        self.filename = 'rover-state'

    def reset(self):
        self.records = []
        self.ptr = 0

    def addNewRecord(self, record):
        bts = record[len(record) - 1]
        if isinstance(bts, bytes):
            record = [r for r in record[:-1]] + [bts.decode('ascii')]
        self.records.append(record)

    def currentRecord(self):
        if self.ptr >= len(self.records):
            if len(self.records) > 0:
                self.ptr = len(self.records) - 1
            else:
                return None

        return self.records[self.ptr]

    def setup(self):
        if len(self.records) > 0:
            state = RoverState(self.rover, None, None, None, None, None)
            state.recreate(self.records[self.ptr])
            state.calculate()
            self.rover.current_state = state

    def previousRecord(self, step):
        if self.ptr == 0:
            return False

        self.ptr -= step
        if self.ptr < 0:
            self.ptr = 0
        self.setup()
        return True

    def nextRecord(self, step):
        if self.ptr >= len(self.records) - 1:
            return False

        self.ptr += step
        if self.ptr >= len(self.records):
            self.ptr = len(self.records) - 1
        self.setup()
        return True

    def size(self):
        return len(self.records)

    def currentRecordTimeOffset(self):
        if len(self.records) == 0:
            return 0
        t0 = self.records[0][0]
        tc = self.records[self.ptr][0]
        return tc - t0

    def _makeFilename(self, i):
        return self.filename + "." + str(i) + ".csv"

    def _findFilenameNumber(self):
        i = 1
        filename = self._makeFilename(i)
        while os.path.exists(filename):
            i += 1
            filename = self._makeFilename(i)

        return i - 1

    def save(self):
        i = self._findFilenameNumber()
        i += 1
        filename = self._makeFilename(i)
        with open(filename, "wt") as file:
            file.write("timestamp,")
            file.write(",".join([f.name for f in self.logger_def.fields]) + "\n")
            for record in self.records:
                file.write(",".join([str(f) for f in record]) + "\n")

    def load(self):
        i = self._findFilenameNumber()
        filename = self._makeFilename(i)
        if os.path.exists(filename):
            with open(filename, "rt") as file:
                self.reset()
                header = file.readline()
                lines = file.readlines()
                for line in lines:
                    if line.endswith("\n"):
                        line = line[0:len(line) - 1]
                    split = line.split(",")
                    timestamp = float(split[0])
                    del split[0]
                    record = [timestamp] + [d[0].fromString(d[1]) for d in zip(self.logger_def.fields, split)]
                    self.records.append(record)
