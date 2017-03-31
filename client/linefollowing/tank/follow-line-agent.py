
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import sys
import math
import time
import traceback
import pyroslib
from PIL import Image

DEBUG = True

MINIMAL_PIXELS = 3
ACTION_TIMEOUT = 4
STEER_GAIN = 20
VALUE_EXPO = 0.2

TURNING_NONE = 0
TURNING_WAIT = 1
TURNING_DONE = 2

MAX_TIMEOUT = 5

ACTION_NONE = 0
ACTION_FORWARD = 1
ACTION_STEER = 2
ACTION_TURN = 3

action = ACTION_NONE
actionTimeout = 0

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
actionStr = ""
forwardSpeed = 2

leftSpeed = 0
rightSpeed = 0

turningState = TURNING_NONE


def log(source, msg):
    if DEBUG:
        print(source + ": " + msg)


def wheelDeg(wheelName, angle):
    topic = "wheel/" + wheelName + "/deg"
    pyroslib.publish(topic, str(angle))
    # print("Published topic=" +  topic + "; msg=" + str(angle))


def wheelSpeed(wheelName, speed):
    topic = "wheel/" + wheelName + "/speed"
    pyroslib.publish(topic, str(speed))
    # print("Published topic=" +  topic + "; msg=" + str(speed))


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
    wheelDeg("fl", str(0))
    wheelDeg("bl", str(0))
    wheelDeg("fr", str(0))
    wheelDeg("br", str(0))

    print("Starting...")
    run = True
    continuousMode = True
    pyroslib.publish("camera/continuous", "on")


def prepare():
    global run, continuousMode
    print("Preparing...")
    run = False
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
    elif message == "prepare":
        prepare()


def toPyImage(imageBytes):
    return Image.frombytes("L", (80, 64), imageBytes)


def testRightValue(cameraImage, pixelMap, r):
    value = 0
    pixelMap = processedImage.load()
    v = 1

    for i in range(31, -1, -1):
        x = 40 - r
        y = i
        p = cameraImage.getpixel((x, y))
        if p < 128:
            pixelMap[x, y] = (0, 255, 0)
            value += v
        else:
            pixelMap[x, y] = (255, 0, 0)

        v += VALUE_EXPO

    return value


def testLeftValue(cameraImage, pixelMap, r):
    value = 0
    pixelMap = processedImage.load()

    v = 1

    for i in range(32, 64, 1):
        x = 40 - r
        y = i
        p = cameraImage.getpixel((x, y))
        if p < 128:
            pixelMap[x, y] = (0, 255, 0)
            value += v
        else:
            pixelMap[x, y] = (255, 0, 0)

        v += VALUE_EXPO

    return value


def processImage():
    global processedImage, maxAngle, minAngle, angle, turnDistance, action, actionStr, actionTimeout, turningState, leftSpeed, rightSpeed

    cameraImage = receivedProcessedImage.copy()

    processedImage = Image.new("RGB", cameraImage.size)
    processedImage.paste(cameraImage)

    r = 30  # 28 pixels = 35mm

    pixelMap = processedImage.load()

    leftValue = testLeftValue(cameraImage, pixelMap, r)
    rightValue = testRightValue(cameraImage, pixelMap, r)

    while leftValue < MINIMAL_PIXELS and rightValue < MINIMAL_PIXELS and r > -30:
        r -= 10
        leftValue = testLeftValue(cameraImage, pixelMap, r)
        rightValue = testRightValue(cameraImage, pixelMap, r)

    # - - -

    if leftValue < MINIMAL_PIXELS and rightValue < MINIMAL_PIXELS:
        actionTimeout += 1
        if actionTimeout >= ACTION_TIMEOUT:
            leftSpeed = 0
            rightSpeed = 0
    elif leftValue < MINIMAL_PIXELS:
        leftSpeed = forwardSpeed * 2
        rightSpeed = forwardSpeed / 2
        actionTimeout = 0
        actionStr = "< steer " + str(turnDistance) + " " + str(forwardSpeed)
        action = ACTION_STEER
    elif rightValue < MINIMAL_PIXELS:
        rightSpeed = forwardSpeed * 2
        leftSpeed = forwardSpeed / 2
        actionTimeout = 0
        actionStr = "> steer " + str(turnDistance) + " " + str(forwardSpeed)
        action = ACTION_STEER
    else:
        prefix = " "
        actionTimeout = 0
        if leftValue < rightValue:
            prefix = "> "
            turnDistance = leftValue / rightValue
            turnDistance *= STEER_GAIN

            leftSpeed = int(forwardSpeed - turnDistance)
            rightSpeed = int(forwardSpeed + turnDistance)
        else:
            prefix = "< "
            turnDistance = rightValue / leftValue
            turnDistance *= STEER_GAIN

            leftSpeed = int(forwardSpeed + turnDistance)
            rightSpeed = int(forwardSpeed - turnDistance)

        actionStr = prefix + "steer " + str(turnDistance) + " " + str(forwardSpeed)
        action = ACTION_STEER

    pyroslib.publish("followLine/feedback",
                     "frameTime:" + frameTime + ","
                     + "angle:" + str(round(angle, 1)) + ","
                     + "turnDistance:" + str(turnDistance) + ","
                     + "action:" + actionStr + ","
                     + "left:" + str(round(leftValue, 1)) + ","
                     + "right:" + str(round(rightValue, 1)))

    message = processedImage.tobytes("raw")
    pyroslib.publish("followLine/processed", message)

    if DEBUG:
        print("Angle " + str(angle) + ", turnDistance " + str(turnDistance) + ", action " + actionStr + ", frame time " + frameTime)

    # print("Scanned " + str(c) + " points, midAngle=" + str(midAngle) + ", minAngle=" + str(minAngle) + ", maxAngle=" + str(maxAngle) + " turnDistance=" + str(turnDistance))


def goOneStep():
    print("LeftSpeed=" + str(leftSpeed) + " rightSpeed=" + str(rightSpeed))
    wheelSpeed("fl", str(leftSpeed))
    wheelSpeed("bl", str(leftSpeed))
    wheelSpeed("fr", str(rightSpeed))
    wheelSpeed("br", str(rightSpeed))


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
