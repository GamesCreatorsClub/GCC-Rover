#
# Copyright 2019 Games Creators Club
#
# MIT License
#

import os
import struct
import uuid
from telemetry.telemetry_stream import streamFromJSON


class StreamCallback:
    def __init__(self, stream_name, topic, unique_id, sub_method):
        self.stream_name = stream_name
        self.stream = None
        self.topic = topic
        self.unique_id = unique_id
        self.sub_method = sub_method
        self.retrieve_callbacks = []
        self.oldest_callbacks = []
        self.defs_callbacks = []

        self.retrieveTopic = topic + "/retrieve_" + unique_id + "_" + stream_name
        self.oldestTimestampTopic = topic + "/oldest_" + unique_id + "_" + stream_name
        self.streamDefTopic = topic + "/streamdef_" + unique_id + "_" + stream_name

        self.sub_method(self.retrieveTopic, self._handleRetrieve)
        self.sub_method(self.oldestTimestampTopic, self._handleOldest)
        self.sub_method(self.streamDefTopic, self._handleStreamDef)

    def stop(self):
        pass

    def _handleRetrieve(self, topic, payload):
        record_length = self.stream.fixed_length

        received_records = len(payload) // record_length
        if received_records * record_length != len(payload):
            pass  # what to do here?

        records = []
        for i in range(0, received_records):
            record = struct.unpack(self.stream.pack_string, payload[i * record_length: (i + 1) * record_length])
            records.append(record)

        callbacks = self.retrieve_callbacks
        self.retrieve_callbacks = []

        while len(callbacks) > 0:
            callbacks[0](records)
            del callbacks[0]

    def _handleOldest(self, topic, payload):
        oldest, size = struct.unpack('<di', payload)
        while len(self.oldest_callbacks) > 0:
            self.oldest_callbacks[0](oldest, size)
            del self.oldest_callbacks[0]

    def _handleStreamDef(self, topic, payload):
        payload = str(payload, 'UTF-8')
        self.stream = streamFromJSON(payload)
        if self.stream is not None:
            self.stream.build(self.stream.stream_id)
        while len(self.defs_callbacks) > 0:
            self.defs_callbacks[0](self.stream)
            del self.defs_callbacks[0]


class TelemetryClient:
    def __init__(self):
        pass

    def getStreams(self, callback):
        pass

    def getStreamDefinition(self, stream_name, callback):
        pass

    def getOldestTimestamp(self, stream, callback):
        pass

    def trim(self, stream, to_timestamp):
        pass

    def retrieve(self, stream, from_timestamp, to_timestmap, callback):
        pass


class PubSubTelemetryClient(TelemetryClient):
    def __init__(self, topic=None, pub_method=None, sub_method=None):
        super(PubSubTelemetryClient, self).__init__()

        self.topic = topic
        self.pub_method = pub_method
        self.sub_method = sub_method
        self.uniqueId = str(uuid.uuid4())
        self.stream_callbacks = {}
        self.streams_callbacks = []
        self.streams_topic = self.topic + "/streams_" + self.uniqueId

        self.sub_method(self.streams_topic, self._handleStreams)

    def _handleStreams(self, topic, payload):
        payload = str(payload, 'UTF-8')
        stream_names = payload.split("\n")
        while len(self.streams_callbacks) > 0:
            self.streams_callbacks[0](stream_names)
            del self.streams_callbacks[0]

    def _addStreamCallback(self, stream_name):
        if stream_name not in self.stream_callbacks:
            streamCallback = StreamCallback(stream_name, self.topic, self.uniqueId, self.sub_method)
            self.stream_callbacks[stream_name] = streamCallback
        else:
            streamCallback = self.stream_callbacks[stream_name]

        return streamCallback

    def stop(self):
        for stream_callback in self.stream_callbacks:
            stream_callback.stop()

    def getStreams(self, callback):
        self.streams_callbacks.append(callback)
        self.pub_method(self.topic + "/streams", self.streams_topic)

    def getStreamDefinition(self, stream_name, callback):
        streamCallback = self._addStreamCallback(stream_name)
        if streamCallback.stream is not None:
            callback(streamCallback.stream)
        else:
            streamCallback.defs_callbacks.append(callback)
            self.pub_method(self.topic + "/streamdef/" + stream_name, streamCallback.streamDefTopic)

    def getOldestTimestamp(self, stream, callback):
        if self.pub_method is None:
            raise NotImplemented("Publish method not defined")

        streamCallback = self._addStreamCallback(stream.name)
        streamCallback.oldest_callbacks.append(callback)
        self.pub_method(self.topic + "/oldest/" + stream.name, streamCallback.oldestTimestampTopic)

    def trim(self, stream, to_timestamp):
        self.pub_method(self.topic + "/trim/" + stream.name, str(to_timestamp))

    def retrieve(self, stream, from_timestamp, to_timestmap, callback):
        if self.pub_method is None:
            raise NotImplemented("Publish method not defined")

        streamCallback = self._addStreamCallback(stream.name)
        streamCallback.retrieve_callbacks.append(callback)
        self.pub_method(self.topic + "/retrieve/" + stream.name, ",".join(str(f) for f in [streamCallback.retrieveTopic, from_timestamp, to_timestmap]))


class SocketTelemetryClient(TelemetryClient):
    def __init__(self):
        super(SocketTelemetryClient, self).__init__()
