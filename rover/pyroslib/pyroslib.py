
import sys
import re
import time
import random
import traceback
import paho.mqtt.client as mqtt

client = None

_connected = False

_subscribers = []
_regexToLambda = {}


def isConnected():
    return _connected


def publish(topic, message):
    if _connected:
        client.publish(topic, message)


def subscribe(topic, method):
    _subscribers.append(topic)
    regexString = "^" + topic.replace("+", "([^/]+)").replace("#", "(.*)") + "$"
    regex = re.compile(regexString)
    _regexToLambda[regex] = method

    if _connected:
        client.subscribe(topic, 0)


def _onConnect(mqttClient, data, rc):
    global _connected
    if rc == 0:
        _connected = True
        for subscriber in _subscribers:
            mqttClient.subscribe(subscriber, 0)

    else:
        print("ERROR: Connection returned error result: " + str(rc))
        sys.exit(rc)


def _onMessage(mqttClient, data, msg):
    payload = str(msg.payload, 'utf-8')
    topic = msg.topic

    for regex in _regexToLambda:
        matching = regex.match(topic)
        if matching:
            method = _regexToLambda[regex]

            method(topic, payload, matching.groups())
            return


def init(name, unique=False):
    global client, _connected

    if unique:
        name += "-" + str(random.randint(10000, 99999))

    client = mqtt.Client(name)

    client.on_connect = _onConnect
    client.on_message = _onMessage

    client.connect("localhost", 1883, 60)

    print("    " + name + " waiting to connect to broker...")
    while not _connected:
        loop(0.02)
    print("    " + name + " connected to broker.")


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
