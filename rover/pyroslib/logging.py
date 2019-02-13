
#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import time

DEBUG_LEVEL_OFF = 0  # To be used when setting up level
DEBUG_LEVEL_ALWAYS = 1  # To be used when logging or setting up level
DEBUG_LEVEL_ERROR = 1  # To be used when logging or setting up level
DEBUG_LEVEL_INFO = 2  # To be used when logging or setting up level
DEBUG_LEVEL_DEBUG = 3  # To be used when logging or setting up level
DEBUG_LEVEL_TRACE = 4  # To be used when logging or setting up level
DEBUG_LEVEL_ALL = 10  # To be used when setting up level

DEBUG_LEVEL = DEBUG_LEVEL_ALL


def formatArgL(label, value, fieldSize):
    if len(label) > 0:
        return label + ":" + str(value).ljust(fieldSize)
    else:
        return str(value).ljust(fieldSize)


def formatArgR(label, value, fieldSize):
    if len(label) > 0:
        return label + ":" + str(value).rjust(fieldSize)
    else:
        return str(value).rjust(fieldSize)


def log(level, what):
    if level <= DEBUG_LEVEL:
        print(what)


def logArgs(*msg):
    tnow = time.time()

    logMsg = formatArgR("", int(tnow * 1000) % 100000, 7) + " " + " ".join(msg)
    log(DEBUG_LEVEL_DEBUG, logMsg)
