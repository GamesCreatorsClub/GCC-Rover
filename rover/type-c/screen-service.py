
#
# Copyright 2016-2018 Games Creators Club
#
# MIT License
#

import time
import traceback

import pyroslib
import pygame
import subprocess
import RPi.GPIO as GPIO
import spidev

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
touchDown = False
touchChanged = False
touchX = 0
touchY = 0

FADEOUT = 3

trail = []

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(25, GPIO.IN)

spi = spidev.SpiDev()

shutdownText = None
confirmText = None
showConfirm = False
showShutdownStarted = False

def doNothing():
    pass


lastProcessed = time.time()


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


def handleAgentCommands(topic, message, groups):
    data = message.split(":")

    cmd = data[0]

    if cmd == "stop":
        stop()
    elif cmd == "start":
        start()


def startPyGame():
    global working, screen, font, shutdownText, confirmText

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

    # process = subprocess.Popen(["ls", "-la", "/dev/pty/0"],
    #                            stdout=subprocess.PIPE)
    # textStream = process.stdout
    # for line in textStream.readlines():
    #     if len(line) > 0:
    #         print("ls -la /dev/tty: " + str(line))

    # os.environ['SDL_VIDEODRIVER'] = "fbcon"
    # os.environ["SDL_VIDEODRIVER"] = "dummy"
    # os.environ["SDL_FBDEV"] = "/dev/fb0"
    # os.environ["SDL_MOUSEDEV"] = "/dev/input/mice"
    # os.environ["SDL_MOUSEDRV"] = "TSLIB"
    # os.environ["SDL_NOMOUSE"] = "1"

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
            # screen = pygame.display.set_mode((320, 480), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)
            screen = pygame.display.set_mode((320, 480))
        except BaseException as e:
            print("Got exception again while trying to set display mode " + str(e))

    print("New surface size " + str(screen.get_size()))

    pygame.mouse.set_visible(False)

    # screen = pygame.display.set_mode((480, 320), pygame.HWSURFACE | pygame.DOUBLEBUF)
    # screen = pygame.display.set_mode((480, 320), pygame.FULLSCREEN)
    # pygame.mouse.set_visible(False)

    screen.fill((128, 128, 0))
    pygame.display.flip()
    font = pygame.font.SysFont("comicsansms", 40)

    shutdownText = font.render("SHUTDOWN", True, (255, 255, 255))
    confirmText = font.render("Confirm", True, (255, 255, 255))

    working = True


def stop():
    global working

    log(DEBUG_LEVEL_ALL, "Stopped driving...")

    pygame.quit()
    working = False


def start():
    log(DEBUG_LEVEL_ALL, "Started driving...")

    try:
        startPyGame()
    except Exception as exception:
        print("ERROR: Got exception on message; " + str(exception) + "\n" + ''.join(traceback.format_tb(exception.__traceback__)))


def mainLoop():
    global touchDown, touchX, touchY, trail, showConfirm, touchChanged, showShutdownStarted

    def fixValue(value, minv, maxv, dest_max):
        if value < minv:
            value = minv
        elif value >= maxv:
            value = maxv - 1

        value = value - minv
        value = (maxv - 1 - minv - value)
        value = value * dest_max / (maxv - minv)
        return int(value)

    def readReg(reg, minv, maxv, dest_max):
        spi.open(0, 1)
        spi.max_speed_hz = 200000
        spi.lsbfirst = False
        data = spi.xfer([reg, 0, 0])
        spi.close()

        return fixValue((data[1] << 5) | (data[2] >> 3), minv, maxv, dest_max)

    touchChanged = False
    if not GPIO.input(25):
        # spi.open(0, 1)
        # spi.max_speed_hz = 200000
        # spi.lsbfirst = False
        # data = spi.xfer([0xD0, 0, 0])
        # spi.close()

        touchY = 480 - readReg(0x90, 200, 3900, 480)
        touchX = readReg(0xD0, 200, 3900, 320)

        if touchY > 0 and touchY < 480 and touchX > 0 and touchX < 320:
            if not touchDown:
                touchChanged = True
            touchDown = True
        else:
            if touchDown:
                touchChanged = True
            touchDown = False
    else:
        if touchDown:
            touchChanged = True
        touchDown = False

    if working and screen is not None:
        screen.fill((0, 0, 0))

        textDown = font.render("Down" if touchDown else "", True, (255, 255, 255))
        textX = font.render("X: " + str(touchX), True, (255, 255, 255))
        textY = font.render("Y: " + str(touchY), True, (255, 255, 255))

        now = time.time()

        if touchDown:
            trail.append((now, (touchX, touchY)))

            if touchChanged:
                if showConfirm:
                    if 140 <= touchX <= 320 and 400 <= touchY <= 480:
                        print("Shutting down")
                        pyroslib.publish("system/shutdown", "secret_message_now")
                        showShutdownStarted = True
                    else:
                        showConfirm = False
                else:
                    if 140 <= touchX <= 320 and 0 <= touchY <= 80:
                        showConfirm = True

        if len(trail) > 0:
            for i in range(len(trail) - 1, -1, -1):
                t = now - trail[i][0]
                if t > FADEOUT:
                    del trail[i]
                # else:
                #     t = FADEOUT - t
                #     size = int(t * 10)
                #     colour = int(255.0 / FADEOUT * t)
                #     pygame.draw.circle(screen, (colour, colour, 0), trail[i][1], size, 0)

        for tr in trail:
            t = FADEOUT - (now - tr[0])
            size = int(t * 10)
            colour = int(255.0 / FADEOUT * t)
            pygame.draw.circle(screen, (colour, colour, colour / 2), tr[1], size, 0)

        screen.blit(textDown, (0, 0))
        screen.blit(textX, (0, 40))
        screen.blit(textY, (0, 80))

        if showShutdownStarted:
            screen.blit(shutdownText, (10, 200))
        elif showConfirm:
            pygame.draw.rect(screen, (200, 50, 0), pygame.Rect(140, 400, 320, 480))
            screen.blit(confirmText, (180, 430))
        else:
            pygame.draw.rect(screen, (200, 150, 0), pygame.Rect(140, 0, 320, 80))
            screen.blit(shutdownText, (150, 30))

        pygame.display.flip()


if __name__ == "__main__":
    try:
        print("Starting screen service...")

        pyroslib.subscribe("screen/command", handleAgentCommands)

        pyroslib.init("screen", unique=True, onConnected=connected)

        print("Started screen service.")

        startPyGame()

        # pyroslib.forever(0.016949152542373, mainLoop)
        pyroslib.forever(0.04, mainLoop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
