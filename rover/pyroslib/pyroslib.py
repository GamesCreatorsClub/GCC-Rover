
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


def doNothing():
    pass

_onConnected = doNothing
_connected = False

_subscribers = []
_regexTextToLambda = {}
_regexBinaryToLambda = {}


def isConnected():
    return _connected


def publish(topic, message):
    if _connected:
        client.publish(topic, message)


def subscribe(topic, method):
    _subscribers.append(topic)
    regexString = "^" + topic.replace("+", "([^/]+)").replace("#", "(.*)") + "$"
    regex = re.compile(regexString)
    _regexTextToLambda[regex] = method

    if _connected:
        client.subscribe(topic, 0)


def subscribeBinary(topic, method):
    _subscribers.append(topic)
    regexString = "^" + topic.replace("+", "([^/]+)").replace("#", "(.*)") + "$"
    regex = re.compile(regexString)
    _regexBinaryToLambda[regex] = method

    if _connected:
        client.subscribe(topic, 0)


def _onDisconnect(mqttClient, data, rc):
    _connect()


def _onConnect(mqttClient, data, rc):
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
    topic = msg.topic

    try:
        for regex in _regexTextToLambda:
            matching = regex.match(topic)
            if matching:
                method = _regexTextToLambda[regex]

                payload = str(msg.payload, 'utf-8')
                method(topic, payload, matching.groups())
                return

        for regex in _regexBinaryToLambda:
            matching = regex.match(topic)
            if matching:
                method = _regexBinaryToLambda[regex]

                method(topic, msg.payload, matching.groups())
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


def init(name, unique=False, host="localhost", port=1883, onConnected=None, waitToConnect=True):
    global client, _connected, _onConnected, _name

    _onConnected = onConnected

    if unique:
        name += "-" + str(random.randint(10000, 99999))

    _name = name
    client = mqtt.Client(name)

    client.on_disconnect = _onDisconnect
    client.on_connect = _onConnect
    client.on_message = _onMessage

    connect(host, port, waitToConnect)


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
    for it in range(0, int(deltaTime / 0.002)):
        time.sleep(0.0015)
        if client is None:
            time.sleep(0.0005)
        else:
            client.loop(0.0005)

        if inner is not None:
            inner()


def forever(deltaTime, outer=None, inner=None):
    while True:
        try:
            loop(deltaTime, inner=inner)
            if outer is not None:
                outer()
        except Exception as ex:
            print("ERROR: Got exception in main loop; " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
