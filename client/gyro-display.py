
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import sys
import time
import pygame
import pyros
import pyros.gcc
import pyros.gccui
import pyros.pygamehelper
from operator import sub

screen = pyros.gccui.initAll((600, 600), True)
bigFont = pyros.gccui.bigFont

arrow_image = pygame.image.load("arrow.png")
rect = arrow_image.get_rect(center=(300, 300))

rate_gyr_z = 0.0
accelData = [0.0,0.0,0.0, 0, 0.0,0.0,0.0]
dt = 0.2
CFangleZ=1000

AA=0.98 # percentage to take from accelerometer

def connected():
    pyros.publish("sensor/gyro/continuous", "")
    pyros.publish("sensor/accel/continuous", "")


def handleGyroData(topic, message, groups):
    global gyroAngle

    data = message.split(",")
    rate_gyr_x = float(data[2])
    dt = float(data[3])

def handleAccelData(topic, message, groups):
    global accelData

    data = message.split(",")
    accelData[0] = float(data[0])
    accelData[1] = float(data[1])
    accelData[2] = float(data[2])
    accelData[4] = float(data[4])
    accelData[5] = float(data[5])
    accelData[6] = float(data[6])

def onKeyDown(key):
    if pyros.gcc.handleConnectKeyDown(key):
        pass


def onKeyUp(key):
    if pyros.gcc.handleConnectKeyUp(key):
        pass


pyros.subscribe("sensor/accel", handleAccelData)
pyros.subscribe("sensor/gyro", handleGyroData)
pyros.init("gyro-display-#", unique=True, onConnected=connected, host=pyros.gcc.getHost(), port=pyros.gcc.getPort(), waitToConnect=False)


resubscribe = time.time()

while True:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    pyros.pygamehelper.processKeys(onKeyDown, onKeyUp)

    pyros.loop(0.03)
    pyros.gccui.background(True)

    textsurface = bigFont.render(f'g: {rate_gyr_z:.2f}', False, (255, 255, 255))
    textsurface2 = bigFont.render(f'a: {accelData[0]:.2f}, {accelData[1]:.2f}, {accelData[2]:.2f}, {accelData[4]:.2f}, {accelData[5]:.2f}, {accelData[6]:.2f}', False, (255,255,255))

    # complementary filter : http://ozzmaker.com/guide-to-interfacing-a-gyro-and-accelerometer-with-a-raspberry-pi/

    if CFangleZ == 1000:
        CFangleZ = accelData[6]

    CFangleZ = AA * (CFangleZ + rate_gyr_z * dt) + (1 - AA) * accelData[6];


    # Rotate the original image without modifying it.
    rot_arrow_image = pygame.transform.rotate(arrow_image, CFangleZ)
    # Get a new rect with the center of the old rect.
    image_rect = rot_arrow_image.get_rect(center=rect.center)

    screen.blit(rot_arrow_image, image_rect)
    textcentre = tuple(map(sub, rect.center, (textsurface.get_width()//2,0)))
    screen.blit(textsurface, textcentre)

    textcentre = tuple(map(sub, rect.center, (textsurface2.get_width()//2,20)))
    screen.blit(textsurface2, textcentre)

    pyros.gcc.drawConnection()
    pyros.gccui.frameEnd()

    if time.time() - resubscribe > 2:
        resubscribe = time.time()
        if pyros.isConnected():
            pyros.publish("sensor/accel/continuous", "calibrate,50")
            pyros.publish("sensor/gyro/continuous", "calibrate,50")
