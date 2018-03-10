
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#


BCM = None
IN = None
OUT = None
PUD_UP = None
FALLING = None
RISING = None
BOTH = None

def setwarnings(b):
    raise NotImplemented()


def setmode(mode):
    raise NotImplemented()


def input(pin):
    raise NotImplemented()


def output(pin, state):
    raise NotImplemented()


def setup(pin, type, pull_up_down=None):
    raise NotImplemented()


def cleanup():
    raise NotImplemented()


def add_event_detect(pin, edge, callback=None):
    raise NotImplemented()
