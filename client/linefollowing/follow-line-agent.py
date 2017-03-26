
import sys
import math
import time
import traceback
import pygame
import pyroslib
from PIL import Image

DEBUG = True

STEER_GAIN = 0.5

TURNING_NONE = 0
TURNING_WAIT = 1
TURNING_DONE = 2

MAX_TIMEOUT = 5

run = False
continuousMode = False

lastPing = time.time()
resubscribe = time.time()
lastReceivedTime = time.time()

receivedProcessedImage = Image.new("L", [80, 64])
processedImage = receivedProcessedImage.copy()

frameTime = ""
turnDistance = 0
feedback = ""

minAngle = 0
maxAngle = 0
angle = 0
forwardSpeed = 2

turningState = TURNING_NONE


def stop():
    global run, continuousMode
    print("Stopping...")
    run = False
    continuousMode = False
    pyroslib.publish("move/stop", "stop")
    pyroslib.publish("camera/continuous", "stop")
    print("Stopped.")


def start():
    global run, continuousMode
    print("Starting...")
    run = True
    continuousMode = True
    pyroslib.publish("camera/continuous", "on")

def connected():
    stop()


def handlePing(topic, message, groups):
    global lastPing
    lastPing = time.time()


def handleSpeed(topic, message, group):
    global forwardSpeed

    forwardSpeed = int(message)


def handleFeedbackMessage(topic, message, groups):
    global turningState

    turningState = TURNING_DONE
    #
    # if not continuousMode:
    #     pyros.publish("camera/processed/fetch", "")


def handleCommand(topic, message, groups):
    if message == "start":
        start()
    elif message == "stop":
        stop()
    elif message == "oneStep":
        goOneStep()


def toPyImage(imageBytes):
    return Image.frombytes("L", (80, 64), imageBytes)


def processImage():
    global processedImage, maxAngle, minAngle, angle, turnDistance

    cameraImage = receivedProcessedImage.copy()

    processedImage = Image.new("RGB", cameraImage.size)
    processedImage.paste(cameraImage)

    r = 28  # 28 pixels = 35mm

    ha = math.atan2(0.5, r + 0.5) * 180 / math.pi
    ha *= 2

    # print("Angle is " + str(ha))

    p1 = 255
    p2 = 0

    minAngle = 90
    maxAngle = -90

    pixelMap = processedImage.load()

    array = []

    a = -90
    c = 0
    while a <= 90:
        a += ha
        ra = a * math.pi / 180 + math.pi

        x = int(r * math.cos(ra) + 40)
        y = int(r * math.sin(ra) + 32)

        p = cameraImage.getpixel((x, y))
        if p > 127:
            pixelMap[x, y] = (0, 255, 0)
            array.append(0)
        else:
            pixelMap[x, y] = (255, 0, 0)
            array.append(1)

        c += 1

    i = 0
    count = 0
    while i < len(array):
        if array[i] == 0:
            if count == 1:
                array[i - 1] = 0
            elif count == 2:
                array[i - 1] = 0
                array[i - 2] = 0
            count = 0
        else:
            count += 1
        i += 1

    a = -90
    i = 0
    while i < len(array):
        a += ha
        if array[i] != 0:
            if a > maxAngle:
                maxAngle = a
            if a < minAngle:
                minAngle = a
        i += 1

    midAngle = (maxAngle + minAngle) / 2

    angle = round(midAngle, 1)

    rDistance = 35  # 28 pixels = 35mm

    if midAngle > 0:
        a = 90 - midAngle * STEER_GAIN

        apr = a * math.pi / 180.0

        divideWith = 2.0 * math.cos(apr)

        if divideWith < 0.01:
            turnDistance = 2000
        else:
            turnDistance = rDistance / divideWith
            if turnDistance > 2000:
                turnDistance = 2000
            elif turnDistance < 60:
                turnDistance = 60

        # turnDistance = - turnDistance
    else:
        a = 90 + midAngle * STEER_GAIN

        apr = a * math.pi / 180.0

        divideWith = 2.0 * math.cos(apr)

        if divideWith < 0.01:
            turnDistance = 2000
        else:
            turnDistance = rDistance / divideWith
            if turnDistance > 2000:
                turnDistance = 2000
            elif turnDistance < 60:
                turnDistance = 60

        turnDistance = - turnDistance
    turnDistance = int(turnDistance)

    # print("Scanned " + str(c) + " points, midAngle=" + str(midAngle) + ", minAngle=" + str(minAngle) + ", maxAngle=" + str(maxAngle) + " turnDistance=" + str(turnDistance))


def goOneStep():
    global turningState

    if abs(angle) < 12:
        action = "drive 0 " + str(forwardSpeed)
        pyroslib.publish("move/drive", "0 " + str(forwardSpeed))
    else:
    # elif abs(angle) < 60:
        action = "steer " + str(turnDistance) + " " + str(forwardSpeed)
        pyroslib.publish("move/steer", str(turnDistance) + " " + str(forwardSpeed))
    # else:
    #     action = "turn " + str(-angle)
    #     turningState = TURNING_WAIT
    #     pyroslib.publish("move/turn", str(-angle))

    message = processedImage.tobytes("raw")

    pyroslib.publish("followLine/frameTime", frameTime)
    pyroslib.publish("followLine/angle", str(round(angle, 1)))
    pyroslib.publish("followLine/turnDistance", str(turnDistance))
    pyroslib.publish("followLine/action", action)
    pyroslib.publish("followLine/processed", message)

    if DEBUG:
        print("Angle " + str(angle) + ", turnDistance " + str(turnDistance) + ", action " + action + ", frame time " + frameTime)


def handleCameraProcessed(topic, message, groups):
    global receivedProcessedImage, processedImage
    global frameTime, lastReceivedTime
    global turningState

    receivedProcessedImage = toPyImage(message)

    processImage()

    now = time.time()
    if now - lastReceivedTime > 5:
        frameTime = ">5s"
    else:
        frameTime = str(round(now - lastReceivedTime, 4))

    lastReceivedTime = now

    if turningState == TURNING_DONE:
        turningState = TURNING_NONE
    else:
        if run and turningState == TURNING_NONE:
            goOneStep()


def loop():
    global resubscribe

    if continuousMode and time.time() - resubscribe > 2:
        resubscribe = time.time()
        if pyroslib.isConnected():
            pyroslib.publish("camera/continuous", "on")

    now = time.time()

    if now - lastPing > MAX_TIMEOUT:
        print("** Didn't receive ping for more than " + str(now - lastPing) + "s. Leaving...")
        sys.exit(0)


if __name__ == "__main__":
    try:
        print("Starting follow-line agent...")

        pyroslib.subscribe("followLine/ping", handlePing)
        pyroslib.subscribe("followLine/speed", handleSpeed)
        pyroslib.subscribe("followLine/command", handleCommand)
        pyroslib.subscribe("move/feedback", handleFeedbackMessage)
        pyroslib.subscribeBinary("camera/processed", handleCameraProcessed)

        pyroslib.init("follow-line-agent", unique=True)

        print("Started follow-line agent.")

        pyroslib.forever(0.02, loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
