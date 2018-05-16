#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import traceback
import time
import re
import copy
import pyroslib
import storagelib
import smbus
import urllib.request
import math
import random
import espeak

def httpRequest(thing):
    return urllib.request.urlopen(thing).read()

# es = espeak.ESpeak()


a = 0
def loop():
    global a
    a += 1
    if a % 500 == 0:
        print("no")
        pyroslib.publish("servo/11", str(220))
    if a % 500 == 25:
        # es.say("NO")
        print("NO!")
        pyroslib.publish("servo/11", str(260))
    if a % 500 == 50:
        pyroslib.publish("servo/11", str(240))





if __name__ == "__main__":

    try:
        print("Starting tts service...")
        print("    initialising tts...")
        servoBlasterFile = open("/dev/servoblaster", 'w')

        pyroslib.init("tts-service")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
