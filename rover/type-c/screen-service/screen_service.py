
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
import traceback

import RPi.GPIO as GPIO

DEBUG_LEVEL_OFF = 0
DEBUG_LEVEL_INFO = 1
DEBUG_LEVEL_DEBUG = 2
DEBUG_LEVEL_ALL = 3
DEBUG_LEVEL = DEBUG_LEVEL_ALL

working = False

# to change console to special group...
# $ sudo addgroup --system console
# $ sudo chgrp console /dev/console
# $ sudo chmod g+rw /dev/console
# $ sudo usermod -a -G console pi


screen = None
font = None
smallFont = None

uptime_updated = 0

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
                    self.uiAdapter.mouseDown((self.touchX, self.touchY))
                    self.touchDown = True
                    self.touchX = newX
                    self.touchY = newY
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


def log(level, what):
    if level <= DEBUG_LEVEL:
        print(what)


def logArgs(*msg):
    tnow = time.time()

    logMsg = formatArgR("", int(tnow * 1000) % 100000, 7) + " " + " ".join(msg)
    log(DEBUG_LEVEL_DEBUG, logMsg)


def connected():
    # pyroslib.publish("sensor/gyro/continuous", "calibrate,50")
    pass


def startPyGame():
    global working, screen, font, smallFont

    log(DEBUG_LEVEL_ALL, "Started driving...")

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
        # screen = pygame.display.set_mode((480, 320), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)
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

    # screen.fill((128, 128, 0))
    # pygame.display.flip()

    font = pygame.font.Font("garuda.ttf", 20)
    smallFont = pygame.font.Font("garuda.ttf", 16)

    working = True


def mainLoop():
    global uptime_updated

    try:
        if working and screen is not None:
            screen.fill((0, 0, 0))

            touchHandler.process()
            uiAdapter.draw(screen)
            touchHandler.draw(screen)

            pygame.display.flip()

            uptime_updated = 0
            now = time.time()
            if uptime_updated + 60 < now:
                now = time.time()
                if os.path.exists("/proc/uptime"):
                    with open("/proc/uptime", 'r') as fh:
                        uptime_minutes = int(float(fh.read().split(" ")[0]) / 60)
                        uptime_hours = int(uptime_minutes / 60)
                        uptime_minutes = uptime_minutes % 60
                        uptime = "{:02d}:{:02d}".format(uptime_hours, uptime_minutes)

                else:
                    uptime = os.popen('uptime').readline().split(" ")[0][:5]

                pyroslib.publish("rover/status/uptime", uptime)

                uptime_updated = now
    except Exception as ex:
        print("MainLoop Exception: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))


if __name__ == "__main__":
    try:
        print("Starting screen service...")

        print("  setting up mixer volume to max...")
        os.system("amixer cset numid=1 100%")
        print("  set up mixer volume to max.")

        pyroslib.init("screen", unique=True, onConnected=connected)

        print("Started screen service.")

        startPyGame()

        # uiFactory = gccui.FlatTheme.FlatThemeFactory()
        uiFactory = gccui.BoxBlueSFTheme.BoxBlueSFThemeFactory(font=font)

        uiAdapter = gccui.UIAdapter(screen)
        touchHandler = TouchHandler(uiAdapter)

        roverscreen.init(uiFactory, uiAdapter, font, smallFont)

        pyroslib.forever(0.04, mainLoop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
