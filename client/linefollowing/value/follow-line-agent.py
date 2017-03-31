
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
STEER_GAIN = 10
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


def sideAngleFront(dist):
    x = math.atan2(69, dist - 36.5)

    return math.degrees(x)


def sideAngleBack(dist):
    x = math.atan2(69, dist + 36.5)

    return math.degrees(x)


def calcInnerSpeed(spd, dist):
    midc = 2 * math.pi * dist
    inc = 2 * math.pi * (dist - 36.5)
    return spd * (inc / midc)


def calcOuterSpeed(spd, dist):
    midc = 2 * math.pi * dist
    outc = 2 * math.pi * (dist + 36.5)
    return spd * (outc / midc)


def steer(d, speed):

    frontAngle = sideAngleFront(abs(d))
    backAngle = sideAngleBack(abs(d))

    innerSpeed = calcInnerSpeed(speed, abs(d))
    outerSpeed = calcOuterSpeed(speed, abs(d))

    adjust = 0
    if innerSpeed > 300:
        adjust = innerSpeed - 300
    elif innerSpeed < -300:
        adjust = innerSpeed + 300
    elif outerSpeed > 300:
        adjust = outerSpeed - 300
    elif outerSpeed < -300:
        adjust = outerSpeed + 300

    innerSpeed -= adjust
    outerSpeed -= adjust

    log("steer", "d=" + str(d) + " s=" + str(speed) + " fa=" + str(frontAngle) + " ba=" + str(backAngle) + " is=" + str(innerSpeed) + " os=" + str(outerSpeed) + " adj=" + str(adjust))

    if d >= 0:
        wheelDeg("fl", str(backAngle))
        wheelDeg("bl", str(-backAngle))
        wheelDeg("fr", str(frontAngle))
        wheelDeg("br", str(-frontAngle))
        if speed != 0:
            wheelSpeed("fl", str(outerSpeed))
            wheelSpeed("fr", str(innerSpeed))
            wheelSpeed("bl", str(outerSpeed))
            wheelSpeed("br", str(innerSpeed))
    else:
        wheelDeg("fl", str(-frontAngle))
        wheelDeg("bl", str(frontAngle))
        wheelDeg("fr", str(-backAngle))
        wheelDeg("br", str(backAngle))
        if speed != 0:
            wheelSpeed("fl", str(innerSpeed))
            wheelSpeed("fr", str(outerSpeed))
            wheelSpeed("bl", str(innerSpeed))
            wheelSpeed("br", str(outerSpeed))


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
    global processedImage, maxAngle, minAngle, angle, turnDistance, action, actionStr, actionTimeout, turningState

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
            action = ACTION_NONE
            actionStr = "drive 0 0"
    elif leftValue < MINIMAL_PIXELS:
        actionTimeout = 0
        turnDistance = 60
        actionStr = "< steer " + str(turnDistance) + " " + str(forwardSpeed)
        action = ACTION_STEER
    elif rightValue < MINIMAL_PIXELS:
        actionTimeout = 0
        turnDistance = -60
        actionStr = "> steer " + str(turnDistance) + " " + str(forwardSpeed)
        action = ACTION_STEER
    else:
        prefix = " "
        actionTimeout = 0
        if leftValue < rightValue:
            prefix = "> "
            turnDistance = leftValue * 2000 / rightValue
            turnDistance *= STEER_GAIN
            turnDistance += 60
        else:
            prefix = "< "
            turnDistance = rightValue * 2000 / leftValue
            turnDistance *= STEER_GAIN
            turnDistance = - turnDistance
            turnDistance -= 60

        if turnDistance > 2000:
            turnDistance = 2000
        elif turnDistance < -2000:
            turnDistance = -2000

        turnDistance = int(turnDistance)

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
    if action == ACTION_FORWARD:
        # pyroslib.publish("move/drive", "0 " + str(forwardSpeed - 1))
        wheelSpeed("fl", forwardSpeed - 1)
        wheelSpeed("fr", forwardSpeed - 1)
        wheelSpeed("bl", forwardSpeed - 1)
        wheelSpeed("br", forwardSpeed - 1)
    elif action == ACTION_STEER:
        # pyroslib.publish("move/steer", str(turnDistance) + " " + str(forwardSpeed))
        steer(turnDistance, forwardSpeed)
    else:
        wheelSpeed("fl", 0)
        wheelSpeed("fr", 0)
        wheelSpeed("bl", 0)
        wheelSpeed("br", 0)
        # pyroslib.publish("move/drive", "0 0")


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
