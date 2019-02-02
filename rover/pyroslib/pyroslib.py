
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import os
import sys
import re
import time
import random
import traceback
import threading
import paho.mqtt.client as mqtt

client = None

_name = "undefined"
_host = None
_port = 1883
_clusterId = None

DEBUG_SUBSCRIBE = False


def doNothing():
    pass


_processId = "unknown"
_onConnected = doNothing
_connected = False

_subscribers = []
_regexTextToLambda = {}
_regexBinaryToLambda = {}

_collectStats = False

_stats = [[0, 0, 0]]
_received = False


def _setClusterId(cId):
    global _clusterId

    _clusterId = cId


def getClusterId():
    if _clusterId is not None:
        return _clusterId
    else:
        return "master"


def _addSendMessage():
    currentStats = _stats[len(_stats) - 1]
    currentStats[1] = currentStats[1] + 1


def _addReceivedMessage():
    currentStats = _stats[len(_stats) - 1]
    currentStats[2] = currentStats[2] + 1


def isConnected():
    return _connected


def publish(topic, message):
    if _connected:
        client.publish(topic, message)
        if _collectStats:
            _addSendMessage()


def subscribe(topic, method):
    _subscribers.append(topic)
    regexString = "^" + topic.replace("+", "([^/]+)").replace("#", "(.*)") + "$"
    regex = re.compile(regexString)

    has_self = hasattr(method, '__self__')
    all_args_count = (3 + (1 if has_self else 0))

    has_groups = method.__code__.co_argcount == all_args_count
    _regexTextToLambda[regex] = (has_groups, method)

    if DEBUG_SUBSCRIBE:
        print("*** stored method " + str(method) + " with has group " + str(has_groups) + " and it self is " + str(has_self) + ", expected arg no " + str(all_args_count))

    if _connected:
        client.subscribe(topic, 0)


def subscribeBinary(topic, method):
    _subscribers.append(topic)
    regexString = "^" + topic.replace("+", "([^/]+)").replace("#", "(.*)") + "$"
    regex = re.compile(regexString)

    has_self = hasattr(method, '__self__')
    all_args_count = (3 + (1 if has_self else 0))

    has_groups = method.__code__.co_argcount == all_args_count

    _regexBinaryToLambda[regex] = (has_groups, method)

    if DEBUG_SUBSCRIBE:
        print("*** stored method " + str(method) + " with has group " + str(has_groups) + " and it self is " + str(has_self) + ", expected arg no " + str(all_args_count))

    if _connected:
        client.subscribe(topic, 0)


def _sendStats():
    msg = ""
    for stat in _stats:
        msg = msg + str(stat[0]) + "," + str(stat[1]) + "," + str(stat[2]) + "\n"

    publish("exec/" + _processId + "/stats/out", msg)


def _handleStats(topic, payload, groups):
    global _collectStats

    if "start" == payload:
        _collectStats = True
    elif "stop" == payload:
        _collectStats = False
    elif "read" == payload:
        _sendStats()


def _onDisconnect(mqttClient, data, rc):
    _connect()


def _onConnect(mqttClient, data, flags, rc):
    global _connected
    if rc == 0:
        _connected = True
        for subscriber in _subscribers:
            mqttClient.subscribe(subscriber, 0)
        if _onConnected is not None:
            _onConnected()

    else:
        print("ERROR: Connection returned error result: " + str(rc))
        sys.exit(rc)


def _onMessage(mqttClient, data, msg):
    global _received

    _received = True

    topic = msg.topic

    if _collectStats:
        _addReceivedMessage()

    try:
        for regex in _regexTextToLambda:
            matching = regex.match(topic)
            if matching:
                payload = str(msg.payload, 'utf-8')

                (has_groups, method) = _regexTextToLambda[regex]

                if has_groups:
                    method(topic, payload, matching.groups())
                else:
                    method(topic, payload)

                return

        for regex in _regexBinaryToLambda:
            matching = regex.match(topic)
            if matching:
                (has_groups, method) = _regexBinaryToLambda[regex]

                if has_groups:
                    method(topic, msg.payload, matching.groups())
                else:
                    method(topic, msg.payload)
                return

    except Exception as ex:
        print("ERROR: Got exception in on message processing; " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))


def _reconnect():
    try:
        client.reconnect()
    except:
        pass


def _connect():
    global _connected
    _connected = False

    if client is not None:
        try:
            client.disconnect()
        except:
            pass

    # print("DriveController: Connecting to rover " + str(selectedRover + 2) + " @ " + roverAddress[selectedRover] + "...");

    client.connect_async(_host, _port, 60)
    thread = threading.Thread(target=_reconnect)
    thread.daemon = True
    thread.start()


def onDisconnect(mqttClient, data, rc):
    _connect()


def init(name, unique=False, onConnected=None, waitToConnect=True, host='localhost', port=1883):
    global client, _connected, _onConnected, _name, _processId, _host, _port

    _onConnected = onConnected

    if unique:
        name += "-" + str(random.randint(10000, 99999))

    _name = name
    client = mqtt.Client(name)

    client.on_disconnect = _onDisconnect
    client.on_connect = _onConnect
    client.on_message = _onMessage

    if 'PYROS_MQTT' in os.environ:
        hostStr = os.environ['PYROS_MQTT']
        hostSplit = hostStr.split(":")
        if len(hostSplit) == 1:
            host = hostSplit[0]
        elif len(hostSplit) == 2:
            host = hostSplit[0]
            try:
                port = int(hostSplit[1])
            except:
                pass
        else:
            pass

    if 'PYROS_CLUSTER_ID' in os.environ:
        _setClusterId(os.environ['PYROS_CLUSTER_ID'])

    if host is not None:
        connect(host, port, waitToConnect)

    if len(sys.argv) > 1:
        _processId = sys.argv[1]
        cId = getClusterId()
        if cId == "master":
            print("Started " + _processId + " process on master pyros. Setting up pyroslib...")
        else:
            print("Started " + _processId + " process on " + getClusterId() + " clustered pyros. Setting up pyroslib...")
        subscribe("exec/" + _processId + "/stats", _handleStats)
    else:
        print("No processId argument supplied.")

    _host = host
    _port = port


def connect(host, port=1883, waitToConnect=True):
    global _host, _port

    _host = host
    _port = port

    _connect()

    if waitToConnect:
        print("    " + _name + " waiting to connect to broker...")
        while not _connected:
            loop(0.02)
        print("    " + _name + " connected to broker.")


def sleep(deltaTime):
    loop(deltaTime)


def loop(deltaTime, inner=None):
    global _received

    currentTime = time.time()

    _received = False
    client.loop(0.0005)  # wait for 0.5 ms

    until = currentTime + deltaTime
    while currentTime < until:
        if _received:
            _received = False
            client.loop(0.0005)  # wait for 0.1 ms
            currentTime = time.time()
        else:
            time.sleep(0.002)  # wait for 2 ms
            currentTime = time.time()
            if currentTime + 0.0005 < until:
                client.loop(0.0005)  # wait for 0.1 ms
                currentTime = time.time()


def forever(deltaTime, outer=None, inner=None):
    global _received

    currentTime = time.time()
    nextTime = currentTime

    while True:
        if _collectStats:
            _stats.append([nextTime, 0, 0])
            if len(_stats) > 100:
                del _stats[0]

        nextTime = nextTime + deltaTime
        try:
            if outer is not None:
                outer()
        except BaseException as ex:
            print("ERROR: Got exception in main loop; " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))

        currentTime = time.time()

        sleepTime = nextTime - currentTime
        if sleepTime < 0.002:
            nextTime = currentTime

            _received = False
            client.loop(0.0005)  # wait for 0.1 ms
            count = 10 # allow at least 5 messages
            while count > 0 and _received:
                _received = True
                count -= 1
                client.loop(0.0005)  # wait for 0.1 ms

        else:
            loop(sleepTime, inner=inner)
