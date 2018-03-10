
#
# Copyright 2016-2018 Games Creators Club
#
# MIT License
#

import time
import threading
import traceback
import pyroslib
from RPi import GPIO

DEBUG = True
STROBO_LIGHT_GPIO = 4

stroboTime = -1
nextTime = time.time()
state = False


def strobo():
    global nextTime, state

    while True:
        if stroboTime > 0:
            # print("    strobing; " + str(nextTime) + " > " + str(time.time()))
            while nextTime > time.time():
                # print("    next time is bigger than now - waiting; " + str(nextTime) + " > " + str(time.time()))
                pass

            # print("    sending out " + str(state))
            GPIO.output(STROBO_LIGHT_GPIO, state)
            state = not state
            nextTime = nextTime + stroboTime

            sleep = nextTime - time.time() - 0.005
            if sleep >= 0.005:
                time.sleep(sleep)
                # print("    sleeping for " + str(sleep))
        else:
            # print("    no data - sleeping")
            time.sleep(0.1)


def handleStrobo(topic, message, groups):
    global stroboTime, nextTime

    if "stop" == message:
        stroboTime = -1
        if DEBUG:
            print("Got stop message")
    else:
        lastStroboTime = stroboTime
        stroboTime = float(message)
        if DEBUG:
            print("Got time " + str(stroboTime) + ", last was " + str(lastStroboTime))
        if lastStroboTime <= 0:
            nextTime = time.time() + stroboTime * 2


if __name__ == "__main__":
    try:
        print("Starting calibrate agent...")

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(STROBO_LIGHT_GPIO, GPIO.OUT)

        thread = threading.Thread(target=strobo, args=())
        thread.daemon = True
        thread.start()

        pyroslib.subscribe("calibrate/strobo", handleStrobo)

        pyroslib.init("calibrate-agent", unique=True)

        print("Started calibrate agent.")

        pyroslib.forever(0.02)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
