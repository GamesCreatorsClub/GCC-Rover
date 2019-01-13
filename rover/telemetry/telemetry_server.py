#
# Copyright 2019 Games Creators Club
#
# MIT License
#

from telemetry import *

import functools
import os
import select
import time
import threading
import uuid


class TelemetryServer:
    def __init__(self):
        self.streams = {}
        self.stream_ids = {}
        self.next_stream_id = 0

    def registerStream(self, stream_definition):
        stream = streamFromJSON(stream_definition)
        if stream.name in self.streams:

            old_stream = self.streams[stream.stream.name]

            if stream != old_stream:
                return -1

        else:
            self.streams[stream.name] = stream
            self.next_stream_id += 1
            stream.stream_id = self.next_stream_id
            self.stream_ids[stream.stream_id] = stream
            return self.next_stream_id


class PubSubLocalPipeTelemetryServer(TelemetryServer):
    def __init__(self, topic=None, pub_method=None, sub_method=None, telemetry_fifo="~/telemetry-fifo", stream_storage=MemoryTelemetryStorage()):
        super(PubSubLocalPipeTelemetryServer, self).__init__()

        self.stream_storage = stream_storage
        self.topic = topic
        self.pub_method = pub_method
        self.sub_method = sub_method
        self.uniqueId = str(uuid.uuid4())

        self.sub_method(topic + "/register", self._handleRegister)  # logger
        self.sub_method(topic + "/streams", self._handleGetStreams)  # client
        self.sub_method(topic + "/streamdef/#", self._handleGetStreamDefinition)  # client
        self.sub_method(topic + "/oldest/#", self._handleGetOldestTimestamp)  # client
        self.sub_method(topic + "/trim/#", self._handleTrim)  # client
        self.sub_method(topic + "/retrieve/#", self._handleRetrieve)  # client

        telemetry_fifo = os.path.expanduser(telemetry_fifo)

        self.telemetry_fifo = telemetry_fifo
        if not os.path.exists(self.telemetry_fifo):
            os.mkfifo(self.telemetry_fifo)

        self.pipe_fd = os.open(self.telemetry_fifo, os.O_NONBLOCK | os.O_RDONLY)

        self.pipe = os.fdopen(self.pipe_fd, 'rb', buffering=0)

        self.thread = threading.Thread(target=self._service_pipe)
        self.thread.daemon = True
        self.thread.start()

    def _service_pipe(self):
        def read_pipe(size):
            reads, writes, errors = select.select([self.pipe], [], [self.pipe])
            return self.pipe.read(size)

        while True:
            reads, writes, errors = select.select([self.pipe], [], [self.pipe])
            d = read_pipe(1)
            if d != b'' and d is not None:
                i = ord(d)
                if i & 1 == 0:
                    stream_id = struct.unpack('<b', read_pipe(1))[0]
                else:
                    stream_id = struct.unpack('<h', read_pipe(2))[0]

                if i & 6 == 0:
                    record_size = struct.unpack('<b', read_pipe(1))[0]
                elif i & 6 == 1:
                    record_size = struct.unpack('<h', read_pipe(2))[0]
                else:
                    record_size = struct.unpack('<i', read_pipe(4))[0]

                record = read_pipe(record_size)

                if stream_id in self.stream_ids:
                    stream = self.stream_ids[stream_id]
                    self.stream_storage.store(stream, stream.extractTimestamp(record), record)
            else:
                time.sleep(0.02)

    def _handleRegister(self, topic, payload):
        payload = str(payload, 'UTF-8')
        i = payload.index(',')
        response_topic = payload[0:i]
        stream_definition = payload[i+1:]

        result = self.registerStream(stream_definition)
        self.pub_method(response_topic, str(result))

    def _handleGetStreams(self, topic, payload):
        if len(self.streams) > 0:
            payload = str(payload, 'UTF-8')
            topic = payload
            streams = "\n".join(self.streams)
            self.pub_method(topic, streams)

    def _handleGetStreamDefinition(self, topic, payload):
        payload = str(payload, 'UTF-8')
        response_topic = payload
        stream_name = topic[topic.rindex('/') + 1:]
        if stream_name in self.streams:
            stream = self.streams[stream_name]
            self.pub_method(response_topic, stream.toJSON())

    def _handleGetOldestTimestamp(self, topic, payload):
        payload = str(payload, 'UTF-8')
        response_topic = payload
        stream_name = topic[topic.rindex('/') + 1:]
        if stream_name in self.streams:
            stream = self.streams[stream_name]
            self.stream_storage.getOldestTimestamp(stream, lambda value: self.pub_method(response_topic, struct.pack('<d', value)))

    def _handleTrim(self, topic, payload):
        payload = str(payload, 'UTF-8')
        stream_name = topic[topic.rindex('/') + 1:]
        if stream_name in self.streams:
            stream = self.streams[stream_name]
            self.stream_storage.trim(stream, float(payload))

    def _handleRetrieve(self, topic, payload):
        payload = str(payload, 'UTF-8')
        stream_name = topic[topic.rindex('/') + 1:]
        response_topic, from_timestamp, to_timestamp = payload.split(",")
        if stream_name in self.streams:
            stream = self.streams[stream_name]
            self.stream_storage.retrieve(stream, float(from_timestamp), float(to_timestamp), lambda records: self._sendRecords(response_topic, records))

    def _sendRecords(self, topic, records):
        if len(records) > 0:
            self.pub_method(topic, functools.reduce(lambda x, y: x + y, [r[1] for r in records]))
        else:
            print("*** got zero records")


if __name__ == "__main__":
    pass
