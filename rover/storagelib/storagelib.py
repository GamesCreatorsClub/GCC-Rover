
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import traceback
import pyroslib
import time

_firstValues = {}
storageMap = {}


def hasDataAt(path):
    value = read(path)
    return value is not None and value != ""


def read(path):
    splitPath = path.split("/")

    m = storageMap
    for i in range(0, len(splitPath) - 1):
        key = splitPath[i]
        if key not in m:
            return None
        m = m[key]
    key = splitPath[len(splitPath) - 1]

    if key not in m:
        return None

    return m[key]


def write(path, value):
    splitPath = path.split("/")

    m = storageMap
    for i in range(0, len(splitPath) - 1):
        key = splitPath[i]
        if key not in m:
            if value == "":
                return  # empty string means no data. No data - no change.
            m[key] = {}
            change = True
        m = m[key]
    key = splitPath[len(splitPath) - 1]
    m[key] = value

    pyroslib.publish("storage/write/" + path, value)


def _handleValues(topic, message, groups):
    global _firstValues

    change = False
    value = message
    splitPath = topic.split("/")
    del splitPath[0]
    del splitPath[0]

    topic = "/".join(splitPath)
    if topic in _firstValues:
        del _firstValues[topic]

    m = storageMap
    for i in range(0, len(splitPath) - 1):
        key = splitPath[i]
        if key not in m:
            if value == "":
                return  # empty string means no data. No data - no change.
            m[key] = {}
            change = True
        m = m[key]
    key = splitPath[len(splitPath) - 1]

    if (key not in m and value != "") or (key in m and m[key] != value):
        change = True
        m[key] = value


def subscribeToPath(path):
    topic = "storage/write/" + path
    pyroslib.subscribe(topic, _handleValues)

    _firstValues[path] = None

    topic = "storage/read/" + path
    pyroslib.publish(topic, "")


def subscribeWithPrototype(prefix, protoMap):
    for key in protoMap:
        if prefix is None or prefix is dict:
            path = key
        else:
            path = prefix + "/" + key
        if type(protoMap[key]) is dict:
            subscribeWithPrototype(path, protoMap[key])
        else:
            subscribeToPath(path)


def bulkPopulateIfEmpty(prefix, protoMap):

    def processRecursive(storage, prefixR, protoMapR):
        for key in protoMapR:
            if prefixR is None or prefixR is dict:
                path = key
            else:
                path = prefixR + "/" + key
            if type(protoMapR[key]) is dict:
                if key not in storage:
                    storage[key] = {}

                    processRecursive(storage[key], path, protoMapR[key])
            else:
                subscribeToPath(path)

    m = storageMap
    if prefix != "" and prefix is not None:
        splitPath = prefix.split("/")
        for k in splitPath:
            if k not in m:
                m[k] = {}
            m = m[k]

    processRecursive(m, prefix, protoMap)


def waitForData():
    while len(_firstValues) > 0:
        try:
            for path in _firstValues:
                topic = "storage/read/" + path
                pyroslib.publish(topic, "")
            pyroslib.loop(1)
        except Exception as ex:
            print("ERROR: Got exception in main loop; " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))


if __name__ == "__main__":

    pyroslib.init("storagelib")
