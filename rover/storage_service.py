#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import os
import time
import traceback
import pyroslib

#
# storage service
#
# This service is just storing 'storage map' to disk and reads it at the start up.
# Also, responds to requests for it to be read out completely or particular keys separately
#

DEBUG = False

STORAGE_MAP_FILE = os.path.expanduser('~') + "/rover-storage.config"

storageMap = {}


def addPaths(p1, p2):
    if "" == p1:
        return p2
    return p1 + "/" + p2


def writeLocalStorage(m):
    def writeLayer(f, mm, path):
        for k in mm:
            p = addPaths(path, k)
            v = mm[k]
            if isinstance(v, dict):
                writeLayer(f, v, p)
            else:
                f.write(p + "=" + str(v) + "\n")

    with open(STORAGE_MAP_FILE, 'wt') as file:
        file.write("; storage written at " + time.ctime(time.time()) + "\n")
        writeLayer(file, m, "")


def loadStorageMap():
    global storageMap

    storageMap = {}

    if os.path.exists(STORAGE_MAP_FILE):
        lines = []
        with open(STORAGE_MAP_FILE, "rt") as file:
            lines = file.readlines()

        for line in lines:
            line = line.strip()
            if not line.startswith(";"):
                i = line.find("=")
                if i > 0:
                    k = line[0:i]
                    v = line[i + 1:]
                    writeStorage(k.split("/"), v)

        print("  Storage map is " + str(storageMap))
    else:
        print("  No storage map found @ " + STORAGE_MAP_FILE)


def _composeRecursively(m, prefix):
    res = ""
    for key in m:
        if type(m[key]) is dict:
            newPrefix = prefix + key + "/"
            res += _composeRecursively(m[key], newPrefix)
        else:
            res += prefix + key + "=" + str(m[key]) + "\n"

    return res


def readoutStorage():
    pyroslib.publish("storage/values", _composeRecursively(storageMap, ""))


def writeStorage(splitPath, value):
    # print("Got storage value " + str(topicSplit))
    change = False

    m = storageMap
    for i in range(0, len(splitPath) - 1):
        key = str(splitPath[i])
        if key not in m:
            if value == "":
                return  # empty string means no data. No data - no change.
            m[key] = {}
            change = True
        m = m[key]
    key = str(splitPath[len(splitPath) - 1])

    if (key not in m and value != "") or (key in m and m[key] != value):
        change = True
        m[key] = value

    if change:
        if DEBUG:
            print("Storing to storage " + str(splitPath) + " = " + value)

        writeLocalStorage(storageMap)


def readStorage(splitPath):
    m = storageMap
    for i in range(0, len(splitPath) - 1):
        key = str(splitPath[i])
        if key not in m or not isinstance(m, dict):
            if DEBUG:
                print("Reading - not found key for " + "/".join(splitPath))
            pyroslib.publish("storage/write/" + "/".join(splitPath), "")
            return
        m = m[key]
    key = str(splitPath[len(splitPath) - 1])

    if key not in m:
        if DEBUG:
            print("Reading - not found key for " + "/".join(splitPath))
        pyroslib.publish("storage/write/" + "/".join(splitPath), "")
    else:
        value = str(m[key])
        if DEBUG:
            print("Reading - found key for " + "/".join(splitPath) + " = " + value)
        pyroslib.publish("storage/write/" + "/".join(splitPath), value)


def storageWriteTopic(topic, payload, groups):
    writeStorage(groups[0].split("/"), payload)


def storageReadAllTopic(topic, payload, groups):
    if DEBUG:
        print("Reading out storage")
    readoutStorage()


def storageReadSpecificTopic(topic, payload, groups):
    readStorage(groups[0].split("/"))


def handleEcho(topic, payload, groups):
    print("Got echo in " + payload)
    if len(groups) > 0:
        pyroslib.publish("echo/out", groups[0] + ":" + payload)
    else:
        pyroslib.publish("echo/out", "default:" + payload)


if __name__ == "__main__":
    try:
        print("Starting storage service...")

        loadStorageMap()

        pyroslib.subscribe("storage/write/#", storageWriteTopic)
        pyroslib.subscribe("storage/read/#", storageReadSpecificTopic)
        pyroslib.subscribe("storage/read", storageReadAllTopic)
        pyroslib.init("storage-service")

        print("Started storage service.")

        pyroslib.forever(0.5)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
