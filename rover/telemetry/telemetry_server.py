#
# Copyright 2019 Games Creators Club
#
# MIT License
#

from telemetry import *

import functools
import os
import threading
import traceback
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

        print("  setting up published/subscriber, unix pipe server...")
        self.stream_storage = stream_storage
        self.topic = topic
        self.pub_method = pub_method
        self.sub_method = sub_method
        self.uniqueId = str(uuid.uuid4())

        print("  subscribing to server topics...")
        self.sub_method(topic + "/register", self._handleRegister)  # logger
        self.sub_method(topic + "/streams", self._handleGetStreams)  # client
        self.sub_method(topic + "/streamdef/#", self._handleGetStreamDefinition)  # client
        self.sub_method(topic + "/oldest/#", self._handleGetOldestTimestamp)  # client
        self.sub_method(topic + "/trim/#", self._handleTrim)  # client
        self.sub_method(topic + "/retrieve/#", self._handleRetrieve)  # client

        print("  subscribed to server topics.")

        telemetry_fifo = os.path.expanduser(telemetry_fifo)

        self.telemetry_fifo = telemetry_fifo
        if not os.path.exists(self.telemetry_fifo):
            print("   fifo file " + str(telemetry_fifo) + " does not exist, creating new...")
            os.mkfifo(self.telemetry_fifo)
        else:
            print("   fifo file " + str(telemetry_fifo) + " already exists.")

        # self.pipe_fd = os.open(self.telemetry_fifo, os.O_RDONLY)

        print("  starting service thread...")
        self.thread = threading.Thread(target=self._service_pipe, daemon=True)
        self.thread.start()
        print("  service thread started.")

    #     print("  starting telemetry fifo thread...")
    #     self.thread = threading.Thread(target=self._initiate_fifo_file, daemon=True)
    #     self.thread.start()
    #     print("  started telemetry fifo thread.")
    #
    # def _initiate_fifo_file(self):
    #     time.sleep(1)
    #     print("   moving on telemetry fifo...")
    #     open(self.telemetry_fifo, "wb")
    #     print("   opened and closed fifo.")

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

            if len(buf) == size:
                return buf

            if DEBUG:
                print("Failed to load all in once: " + str(len(buf)) + " while needed " + str(size))
            while len(buf) < size:
                bb = self.pipe.read(size - len(buf))
                buf = buf + bb

            return buf

        while True:
            try:
                print("    opening " + str(self.telemetry_fifo) + " fifo file...")
                self.pipe = open(self.telemetry_fifo, "rb")
                print("    opened " + str(self.telemetry_fifo) + " fifo file...")

                while True:
                    d = read_pipe(1)[0]
                    if DEBUG:
                        print("Def char " + str(bin(d)))
                    if d & 1 == 0:
                        if DEBUG:
                            print("Reading one byte stream id...")
                        stream_id = struct.unpack('<B', read_pipe(1))[0]
                    else:
                        if DEBUG:
                            print("Reading two bytes stream id...")
                        stream_id = struct.unpack('<H', read_pipe(2))[0]

                    if DEBUG:
                        print("Stream id = " + str(stream_id))

                    if d & 6 == 0:
                        if DEBUG:
                            print("Reading one byte record size...")
                        record_size = struct.unpack('<B', read_pipe(1))[0]
                    elif d & 6 == 1:
                        if DEBUG:
                            print("Reading two bytes record size...")
                        record_size = struct.unpack('<H', read_pipe(2))[0]
                    else:
                        if DEBUG:
                            print("Reading four bytes record size...")
                        record_size = struct.unpack('<I', read_pipe(4))[0]

                    if DEBUG:
                        print("Record size = " + str(record_size) + ", reading record...")

                    record = read_pipe(record_size)
                    if DEBUG:
                        print("Got record of size = " + str(len(record)) + ", storing record...")

                    if stream_id in self.stream_ids:
                        stream = self.stream_ids[stream_id]
                        self.stream_storage.store(stream, stream.extractTimestamp(record), record)
                        if DEBUG:
                            print("Stored record for stream id " + str(stream_id))
                    else:
                        print("Got unknown stream id! stream_id=" + str(stream_id) + ",  record_id=" + str(record_size) + ", def=" + str(bin(d)))

            except Exception as ex:
                print("Exception while handing pipe stream; " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))

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
        if DEBUG:
            print("Asked for stream definition " + str(stream_name))
        if stream_name in self.streams:
            stream = self.streams[stream_name]
            self.pub_method(response_topic, stream.toJSON())
        else:
            self.pub_method(response_topic, "{}")
            if DEBUG:
                print("Asked for strema definition but stream does not exist " + stream_name)

    def _handleGetOldestTimestamp(self, topic, payload):
        payload = str(payload, 'UTF-8')
        response_topic = payload
        stream_name = topic[topic.rindex('/') + 1:]
        if stream_name in self.streams:
            stream = self.streams[stream_name]
            self.stream_storage.getOldestTimestamp(stream, lambda oldest,size: self.pub_method(response_topic, struct.pack('<di', oldest,size)))
        else:
            if DEBUG:
                print("Asked for oldest but stream does not exist " + stream_name)

    def _handleTrim(self, topic, payload):
        payload = str(payload, 'UTF-8')
        stream_name = topic[topic.rindex('/') + 1:]
        if stream_name in self.streams:
            stream = self.streams[stream_name]
            self.stream_storage.trim(stream, float(payload))
        else:
            if DEBUG:
                print("Asked for trim but stream does not exist " + stream_name)

    def _handleRetrieve(self, topic, payload):
        payload = str(payload, 'UTF-8')
        stream_name = topic[topic.rindex('/') + 1:]
        response_topic, from_timestamp, to_timestamp = payload.split(",")
        if stream_name in self.streams:
            stream = self.streams[stream_name]
            if DEBUG:
                print("Asked to retrieve from stream " + stream_name + ", from " + str(float(from_timestamp)) + " to " + str(float(to_timestamp)))
            self.stream_storage.retrieve(stream, float(from_timestamp), float(to_timestamp), lambda records: self._sendRecords(response_topic, records))
        else:
            if DEBUG:
                print("Asked to retrieve from unknown stream " + stream_name)

    def _sendRecords(self, topic, records):
        if len(records) > 0:
            if DEBUG:
                print("Sending " + str(len(records)) + " records out...")
            self.pub_method(topic, functools.reduce(lambda x, y: x + y, [r[1] for r in records]))
            if DEBUG:
                print("Sent " + str(len(records)) + " records out.")
        else:
            if DEBUG:
                print("Sending empty message")
            self.pub_method(topic, b'')
            print("*** got zero records")


if __name__ == "__main__":
    pass
