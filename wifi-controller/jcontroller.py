#!/usr/bin/env python3

import joystick
import subprocess
from lib_oled96 import ssd1306

from time import sleep
from PIL import ImageFont, ImageDraw, Image
from smbus import SMBus
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)


# font = ImageFont.load_default()

font = ImageFont.truetype('FreeMono.ttf', 16)
fontBig = ImageFont.truetype('FreeMono.ttf', 32)

i2cbus = SMBus(1)

oled = ssd1306(i2cbus)
draw = oled.canvas
joystick.startNewThread()

batteryBlink = 0


def clear():
    # draw.rectangle((0, 0, oled.width - 1, oled.height - 1), outline=0, fill=0)
    draw.rectangle((0, 0, oled.width - 1, oled.height - 1), fill=0)


def drawText(xy, text):
    draw.text(xy, text, font=font, fill=1)


def drawJoysticks():
    x1 = int(joystick.axis_states["x"] * 20)
    y1 = int(joystick.axis_states["y"] * 20)
    x2 = int(joystick.axis_states["rx"] * 20)
    y2 = int(joystick.axis_states["ry"] * 20)

    draw.line((x1 + 20, 0, x1 + 20, 40), fill=255)
    draw.line((0, y1 + 20, 40, y1 + 20), fill=255)
    draw.line((87 + x2 + 20, 0, 87 + x2 + 20, 40), fill=255)
    draw.line((87, y2 + 20, 87 + 40, y2 + 20), fill=255)

    x3 = int(joystick.axis_states["hat0x"])
    y3 = int(joystick.axis_states["hat0y"])

    if x3 < 0:
        draw.rectangle((0, 50, 7, 57), fill=255)
        draw.rectangle((16, 50, 23, 57), outline=255)
    elif x3 > 0:
        draw.rectangle((0, 50, 7, 57), outline=255)
        draw.rectangle((16, 50, 23, 57), fill=255)
    else:
        draw.rectangle((0, 50, 7, 57), outline=255)
        draw.rectangle((16, 50, 23, 57), outline=255)

    if y3 < 0:
        draw.rectangle((8, 42, 15, 49), fill=255)
        draw.rectangle((8, 58, 15, 63), outline=255)
    elif y3 > 0:
        draw.rectangle((8, 42, 15, 49), outline=255)
        draw.rectangle((8, 58, 15, 63), fill=255)
    else:
        draw.rectangle((8, 42, 15, 49), outline=255)
        draw.rectangle((8, 58, 15, 63), outline=255)

    x = 54
    y = 0
    for i in range(0, 12):
        buttonState = joystick.button_states[joystick.button_map[i]]
        if buttonState:
            draw.rectangle((x, y, x + 7, y + 7), fill=255)
        else:
            draw.rectangle((x, y, x + 7, y + 7), outline=255)

        x = x + 8 + 2
        if x > 72:
            x = 54
            y = y + 8 + 2


def drawBattery(x, y, width):
    global batteryBlink

    batteryBlink += 1
    if batteryBlink > 8:
        batteryBlink = 0

    batteryState = GPIO.input(17)

    if batteryState:
        draw.rectangle((x + 2, y, x + width - 2, y + 5), fill=255)
        draw.rectangle((x, y + 2, x + 1, y + 3), fill=255)
        draw.line((x + 3, y + 1, x + 3, y + 1), fill=0)
        draw.line((x + 3, y + 2, x + 4, y + 1), fill=0)
        draw.line((x + 3, y + 3, x + 5, y + 1), fill=0)
        draw.line((x + 3, y + 4, x + 6, y + 1), fill=0)
        draw.line((x + 4, y + 4, x + 7, y + 1), fill=0)
        draw.line((x + 5, y + 4, x + 8, y + 1), fill=0)
        # drawText((0, 50), "B: OKW")
    else:
        if batteryBlink > 4:
            draw.rectangle((x + 2, y, x + width - 2, y + 5), outline=255)
            draw.rectangle((x, y + 2, x + 1, y + 3), fill=255)
            draw.line((x + width - 3, y + 5, x + width - 3, y + 5), fill=255)
            draw.line((x + width - 4, y + 5, x + width - 3, y + 4), fill=255)
            draw.line((x + width - 5, y + 5, x + width - 3, y + 3), fill=255)
            draw.line((x + width - 6, y + 5, x + width - 3, y + 2), fill=255)
            draw.line((x + width - 7, y + 5, x + width - 3, y + 1), fill=255)
        # drawText((0, 50), "B: LOW")


def doShutdown():
    print("Shutting down now!")
    try:
        subprocess.call(["/usr/bin/sudo", "/sbin/shutdown", "-h", "now"])
    except Exception as exception:
        print("ERROR: Failed to shutdown; " + str(exception))


def countDownToShutdown():
    i = 10
    while joystick.button_states["select"] and joystick.button_states["start"]:
        clear()

        i -= 1
        if i == 0:
            x = (128 - draw.textsize("Shutdown in", font)[0]) // 2
            draw.text((x, 10), "Shutdown in", font=font, fill=1)

            x = (128 - draw.textsize("NOW", fontBig)[0]) // 2
            draw.text((x, 32), "NOW", font=fontBig, fill=1)
            oled.display()

            doShutdown()

        x = (128 - draw.textsize("Shutdown in", font)[0]) // 2
        draw.text((x, 10), "Shutdown in", font=font, fill=1)

        x = (128 - draw.textsize(str(i), fontBig)[0]) // 2
        draw.text((x, 32), str(i), font=fontBig, fill=1)
        oled.display()
        sleep(0.5)


# Main event loop
while True:
    clear()

    drawJoysticks()
    drawBattery(106, 58, 21)

    if joystick.button_states["select"] and joystick.button_states["start"]:
        countDownToShutdown()

    oled.display()
    sleep(0.01)
