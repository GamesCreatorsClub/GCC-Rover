
#
# Copyright 2016-2018 Games Creators Club
#
# MIT License
#


import gccui
import os
import pyroslib
import pygame
import roverscreen
import subprocess
import spidev
import time
import threading
import traceback
from pyroslib.logging import log, LOG_LEVEL_ALWAYS, LOG_LEVEL_INFO, LOG_LEVEL_DEBUG

import RPi.GPIO as GPIO

working = False

# to change console to special group...
# $ sudo addgroup --system console
# $ sudo chgrp console /dev/console
# $ sudo chmod g+rw /dev/console
# $ sudo usermod -a -G console pi


screen = None
font = None
smallFont = None

wheel_status = None
joystick_status = None
sound_level = 'all'
uptime = None

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


class TouchHandler:
    def __init__(self, _uiAdapter):
        self.uiAdapter = _uiAdapter
        self.touchDown = False
        self.touchX = 0
        self.touchY = 0
        self.spi = spidev.SpiDev()

        self.FADEOUT = 1.5

        self.trail = []

        GPIO.setup(25, GPIO.IN)

    def processEvent(self, event):
        pass

    def process(self):
        if not GPIO.input(25):
            # spi.open(0, 1)
            # spi.max_speed_hz = 200000
            # spi.lsbfirst = False
            # data = spi.xfer([0xD0, 0, 0])
            # spi.close()

            newY = 480 - self.readReg(0x90, 200, 3900, 480)
            newX = self.readReg(0xD0, 200, 3900, 320)

            if newY > 0 and newY < 480 and newX > 0 and newX < 320:
                if not self.touchDown:
                    self.touchDown = True
                    self.touchX = newX
                    self.touchY = newY
                    self.uiAdapter.mouseDown((self.touchX, self.touchY))
                elif newX != self.touchX or newY != self.touchY:
                    self.touchX = newX
                    self.touchY = newY
                    self.uiAdapter.mouseMoved((self.touchX, self.touchY))

                self.trail.append((time.time(), (self.touchX, self.touchY)))
            else:
                if self.touchDown:
                    self.uiAdapter.mouseUp((self.touchX, self.touchY))
                self.touchDown = False
        else:
            if self.touchDown:
                self.uiAdapter.mouseUp((self.touchX, self.touchY))
            self.touchDown = False

    def draw(self, surface):
        now = time.time()
        if len(self.trail) > 0:
            for i in range(len(self.trail) - 1, -1, -1):
                t = now - self.trail[i][0]
                if t > self.FADEOUT:
                    del self.trail[i]

        for tr in self.trail:
            t = self.FADEOUT - (now - tr[0])
            size = int(t * 5)
            colour = int(255.0 / self.FADEOUT * t)
            pygame.draw.circle(screen, (colour, colour, colour / 2, self.FADEOUT * t), tr[1], size, 0)

    def readReg(self, reg, minv, maxv, dest_max):
        self.spi.open(0, 1)
        self.spi.max_speed_hz = 200000
        self.spi.lsbfirst = False
        data = self.spi.xfer([reg, 0, 0])
        self.spi.close()

        return self.fixValue((data[1] << 5) | (data[2] >> 3), minv, maxv, dest_max)

    @staticmethod
    def fixValue(value, minv, maxv, dest_max):
        if value < minv:
            value = minv
        elif value >= maxv:
            value = maxv - 1

        value = value - minv
        value = (maxv - 1 - minv - value)
        value = value * dest_max / (maxv - minv)
        return int(value)


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


def connected():
    # pyroslib.publish("sensor/gyro/continuous", "calibrate,50")
    pass


def startPyGame():
    global working, screen, font, smallFont

    log(LOG_LEVEL_ALWAYS, "Started driving...")

    def disable_text_cursor_blinking():
        command_to_run = ["/usr/bin/sudo", "sh", "-c", "echo 0 > /sys/class/graphics/fbcon/cursor_blink"]
        try:
            output = subprocess.check_output(command_to_run, universal_newlines=True)
        except subprocess.CalledProcessError:
            raise

    def disable_screen_blanking():
        command_to_run = ["/usr/bin/setterm", "--blank", "0"]
        try:
            output = subprocess.check_output(command_to_run, universal_newlines=True)
        except subprocess.CalledProcessError:
            raise

    pygame.init()

    print("Disabling cursor blinking")
    disable_text_cursor_blinking()

    print("Disabling screen blanking")
    disable_screen_blanking()

    print(str(pygame.display.Info()))

    for mode in pygame.display.list_modes():
        print(mode)

    s = pygame.display.get_surface()

    if s is not None:
        print("Current surface size " + str(s.get_size()))
    else:
        print("No surface at this moment")

    try:
        screen = pygame.display.set_mode((320, 480))
    except BaseException as e:
        print("Got exception trying to set display mode " + str(e))
        print("Retrying...")
        try:
            screen = pygame.display.set_mode((320, 480))
        except BaseException as e:
            print("Got exception again while trying to set display mode " + str(e))

    print("New surface size " + str(screen.get_size()))

    pygame.mouse.set_visible(False)

    font = pygame.font.Font("garuda.ttf", 20)
    smallFont = pygame.font.Font("garuda.ttf", 16)

    working = True


def handleSay(topic, message, groups):
    say(message)


def say(message, level=LOG_LEVEL_INFO):
    def doSay(_message):
        print("Saying: " + _message)

        # new_env = os.environ.copy()
        # proc = subprocess.Popen(["/usr/bin/flite", "-v", "-voice", "/home/pi/cmu_us_ljm.flitevox", "--setf duration_stretch=1.3", "--setf int_f0_target_stddev=70", "\"" + message + "\""],
        #                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ.copy(), shell=False)
        # stdout, stderr = proc.communicate()
        # print("Said: " + str(stdout) + ", error: " + str(stderr))

        os.system("/usr/bin/flite -v -voice /home/pi/cmu_us_eey.flitevox --setf duration_stretch=1.2 --setf int_f0_target_stddev=70 \"" + _message.replace("\"", "") + "\"")

    threading.Thread(target=doSay, args=(message,), daemon=True).start()


def handleWheelsStatus(topic, message, group):
    global wheel_status

    status = {s[0]: s[1] for s in [s.split(":") for s in message.split(" ")]}
    if 's' in status:
        ws = status['s']

        # print("Got wheels status \"" + ws + "\", old status \"" + str(wheel_status) + "\"")
        if ws != wheel_status:
            if ws == "running":
                say("Wheels, engaged.")
            elif ws == "stopped":
                say("Wheels, disengaged.")

            wheel_status = ws

    if oldHandleWheelsStatus is not None:
        pyroslib.invokeHandler(topic, message, group, oldHandleWheelsStatus)


def handleJoystickStatus(topic, message, group):
    global joystick_status

    # print("Got joystick status \"" + message + "\", old status \"" + str(joystick_status) + "\"")
    if message != joystick_status:
        if message == "connected":
            say("Controller, attached.")
        elif message == "none" and joystick_status is not None:
            say("Controller, detached.")

        joystick_status = message

    if oldHandleJoystickStatus is not None:
        pyroslib.invokeHandler(topic, message, group, oldHandleJoystickStatus)


def handleUptimeStatus(topic, message, group):
    global uptime

    if message != uptime:
        if message == "00:10":
            say("Time: ten minutes.")
        elif message == "00:20":
            say("Time: twenty minutes.")
        elif message == "00:30":
            say("Time, Warning! Thirty minutes.", level=LOG_LEVEL_ALWAYS)
        elif message == "00:40":
            say("Time, Warning! Fourty minutes.", level=LOG_LEVEL_ALWAYS)

        uptime = message

    if oldHandleUptimeStatus is not None:
        pyroslib.invokeHandler(topic, message, group, oldHandleUptimeStatus)


def mainLoop():
    try:
        if working and screen is not None:
            screen.fill((0, 0, 0))

            touchHandler.process()
            uiAdapter.draw(screen)
            touchHandler.draw(screen)

            pygame.display.flip()

    except Exception as ex:
        print("MainLoop Exception: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))


if __name__ == "__main__":
    try:
        print("Starting screen service...")

        print("  setting up mixer volume to max...")
        os.system("amixer cset numid=1 100%")
        print("  set up mixer volume to max.")

        pyroslib.init("screen", unique=True, onConnected=connected)
        pyroslib.subscribe("screen/say", handleSay)
        print("Started screen service.")

        startPyGame()

        uiAdapter = gccui.UIAdapter(screen)
        uiFactory = gccui.BoxBlueSFTheme.BoxBlueSFThemeFactory(uiAdapter, font=font)

        touchHandler = TouchHandler(uiAdapter)

        roverscreen.init(uiFactory, uiAdapter, font, smallFont)

        oldHandleWheelsStatus = pyroslib.subscribedMethod("wheel/feedback/status")
        oldHandleJoystickStatus = pyroslib.subscribedMethod("joystick/status")
        oldHandleUptimeStatus = pyroslib.subscribedMethod("power/uptime")
        pyroslib.subscribe("wheel/feedback/status", handleWheelsStatus)
        pyroslib.subscribe("joystick/status", handleJoystickStatus)
        pyroslib.subscribe("power/uptime", handleUptimeStatus)

        pyroslib.forever(0.04, mainLoop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
