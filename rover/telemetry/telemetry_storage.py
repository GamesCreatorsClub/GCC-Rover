#
# Copyright 2019 Games Creators Club
#
# MIT License
#

import os
import struct
import time
import uuid


def _findTimeIndex(values, the_time, starting_from=0):
    for i in range(starting_from, len(values)):
        if values[i][0] >= the_time:
            return i

    return len(values)


class TelemetryStorage:
    def __init__(self):
        pass

    def store(self, stream, time_stamp, record):
        raise NotImplemented("TelemetryStorage.store")

    def trim(self, stream, to_timestamp):
        raise NotImplemented("TelemetryStorage.trim")

    def retrieve(self, stream, from_timestamp, to_timestmap, callback):
        raise NotImplemented("TelemetryStorage.retrieve")

    def getOldestTimestamp(self, stream, callback):
        callback(time.time())


class MemoryTelemetryStorage(TelemetryStorage):
    def __init__(self, max_records=100000):
        super(MemoryTelemetryStorage, self).__init__()
        self.streams = {}
        self.max_records = max_records

    def _values(self, stream):
        if stream.name not in self.streams:
            self.streams[stream.name] = []

        return self.streams[stream.name]

    def store(self, stream, time_stamp, record):
        stream_array = self._values(stream)
        stream_array.append([time_stamp, record])
        if len(stream_array) > self.max_records:
            del stream_array[0:self.max_records//10]

    def trim(self, stream, to_timestamp):
        values = self._values(stream)
        if len(values) > 0:
            i = _findTimeIndex(values, to_timestamp)
            values = values[i:]
            self.streams[stream.name] = values

    def retrieve(self, stream, from_timestamp, to_timestmap, callback):
        values = self._values(stream)
        if len(values) > 0:
            start = _findTimeIndex(values, from_timestamp)
            if start < len(values):
                end = _findTimeIndex(values, to_timestmap, starting_from=start)

                callback(values[start:end])
                return

        callback([])

    def getOldestTimestamp(self, stream, callback):
        if stream.name in self.streams:
            values = self.streams[stream.name]
            if len(values) > 0:
                return callback(values[0][0], len(values))

        return callback(0, 0)


class StreamCallback:
    def __init__(self, stream):
        self.stream = stream
        self.callback = None

    def handleRetrieve(self, topic, payload):
        record_length = self.stream.fixed_length

        received_records = len(payload) // record_length
        if received_records * record_length != len(payload):
            pass  # what to do here?

        records = []
        for i in range(0, received_records):
            record = struct.unpack(self.stream.pack_string, payload[i * record_length: (i + 1) * record_length])
            records.append(record)
        self.callback(records)

    def handleOldest(self, topic, payload):
        self.callback(struct.unpack('<d', payload))


class ClientPubSubTelemetryStorage(TelemetryStorage):

    def __init__(self, topic=None, pub_method=None, sub_method=None):
        super(ClientPubSubTelemetryStorage, self).__init__()
        self.topic = topic
        self.put_method = pub_method
        self.sub_method = sub_method
        self.uniqueId = str(uuid.uuid4())
        self.stream_callbacks = {}

    def setPubSubCallbacks(self, topic, pub_method, sub_method):
        self.topic = topic
        self.put_method = pub_method
        self.sub_method = sub_method

    def store(self, stream, time_stamp, record):
        if self.put_method is None:
            raise NotImplemented("Publish method not defined")

        self.put_method(self.pub_topic + "/store/" + stream.name, record)

    def trim(self, stream, to_timestamp):
        self.put_method(self.pub_topic + "/trim/" + stream.name, struct.pack("<d", to_timestamp))

    def _addStreamCallback(self, stream, callback):
        if stream.name not in self.stream_callbacks:
            streamCallback = StreamCallback(stream)
            self.stream_callbacks[stream.name] = streamCallback

            self.sub_method(self.topic + "/retrieve/" + self.uniqueId + stream.name, streamCallback.handleRetrieve)
            self.sub_method(self.topic + "/oldest/" + self.uniqueId + stream.name, streamCallback.handleOldest)

        self.stream_callbacks[stream.name].callback = callback

    def retrieve(self, stream, from_timestamp, to_timestmap, callback):
        if self.put_method is None:
            raise NotImplemented("Publish method not defined")

        self._addStreamCallback(stream, callback)
        self.put_method(self.topic + "/retrieve/request", struct.pack("<dd36s", from_timestamp, to_timestmap, self.uniqueId))

    def getOldestTimestamp(self, stream, callback):
        if self.put_method is None:
            raise NotImplemented("Publish method not defined")

        self._addStreamCallback(stream, callback)
        self.put_method(self.topic + "/retrieve/request", struct.pack("<36s", self.uniqueId))


class LocalPipePubSubTelemetryStorage(ClientPubSubTelemetryStorage):
    def __init__(self, telemetry_fifo="~/telemetry-fifo"):
        super(LocalPipePubSubTelemetryStorage, self).__init__()

        telemetry_fifo = os.path.expanduser(telemetry_fifo)

        self.telemetry_fifo = telemetry_fifo

        if not os.path.exists(telemetry_fifo):
            os.mkfifo(telemetry_fifo)

        self.pipe_fd = os.open(telemetry_fifo, os.O_NONBLOCK | os.O_WRONLY)

        self.pipe = os.fdopen(self.pipe_fd, 'wb', buffering=0)

    def store(self, stream, time_stamp, record):
        self.pipe.write(stream.header)
        self.pipe.write(record)

    def trim(self, stream, to_timestamp):
        # use ClientPubSubTelemetryStorage for rest of the communication
        super(LocalPipePubSubTelemetryStorage, self).trim(stream, to_timestamp)

    def retrieve(self, stream, from_timestamp, to_timestmap, callback):
        # use ClientPubSubTelemetryStorage for rest of the communication
        super(LocalPipePubSubTelemetryStorage, self).retrieve(stream, from_timestamp, to_timestmap, callback)

    def getOldestTimestamp(self, stream, callback):
        # use ClientPubSubTelemetryStorage for rest of the communication
        super(LocalPipePubSubTelemetryStorage, self).getOldestTimestamp(stream, callback)
