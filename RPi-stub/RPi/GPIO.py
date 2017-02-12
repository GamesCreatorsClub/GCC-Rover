

BCM = None
IN = None
OUT = None
PUD_UP = None


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
