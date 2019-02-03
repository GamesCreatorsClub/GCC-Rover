#
# Copyright 2019 Games Creators Club
#
# MIT License
#

from telemetry import *

import functools
import os
import threading
import uuid

DEBUG = False


class TelemetryServer:
    def __init__(self):
        self.streams = {}
        self.stream_ids = {}
        self.next_stream_id = 0

    def registerStream(self, stream_definition):
        stream = streamFromJSON(stream_definition)
        if stream.name in self.streams:

            old_stream = self.streams[stream.name]
            stream.stream_id = old_stream.stream_id
            if stream.toJSON() != old_stream.toJSON():
                print("ERROR: Someone tried to register different streams: " + stream.name)
                print("old_stream=" + old_stream.toJSON())
                print("new_stream=" + stream.toJSON())
                return -1
            else:
                return old_stream.stream_id

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

        # self.pipe_fd = os.open(self.telemetry_fifo, os.O_RDONLY)
        self.pipe = open(self.telemetry_fifo, "rb")

        self.thread = threading.Thread(target=self._service_pipe, daemon=True)
        self.thread.start()

    def _service_pipe(self):
        def read_pipe(size):
            # buf = os.read(self.pipe_fd, size)
            buf = self.pipe.read(size)
            # if buf != b'' and len(buf) == size:
            #     return buf
            # elif buf != b'':
            #     size -= len(buf)
            #
            # while size > 0:
            #     b = os.read(self.pipe_fd, size)
            #     if b != b'':
            #         buf += b
            #         size -= len(b)

            return buf

        while True:
            d = read_pipe(1)[0]
            if DEBUG:
                print("Def char " + str(bin(d)))
            if d & 1 == 0:
                if DEBUG:
                    print("Reading one byte stream id...")
                stream_id = struct.unpack('<b', read_pipe(1))[0]
            else:
                if DEBUG:
                    print("Reading two bytes stream id...")
                stream_id = struct.unpack('<h', read_pipe(2))[0]

            if DEBUG:
                print("Stream id = " + str(stream_id))

            if d & 6 == 0:
                if DEBUG:
                    print("Reading one byte record size...")
                record_size = struct.unpack('<b', read_pipe(1))[0]
            elif d & 6 == 1:
                if DEBUG:
                    print("Reading two bytes record size...")
                record_size = struct.unpack('<h', read_pipe(2))[0]
            else:
                if DEBUG:
                    print("Reading four bytes record size...")
                record_size = struct.unpack('<i', read_pipe(4))[0]

            if DEBUG:
                print("Record size = " + str(record_size) + ", reading record...")

            record = read_pipe(record_size)
            if DEBUG:
                print("Got record of size = " + str(len(record)) + ", storing record...")

            if stream_id in self.stream_ids:
                stream = self.stream_ids[stream_id]
                self.stream_storage.store(stream, stream.extractTimestamp(record), record)
            else:
                print("Got unknown stream id! stream_id=" + str(stream_id) + ",  record_id=" + str(record_size) + ", def=" + str(bin(d)))

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
