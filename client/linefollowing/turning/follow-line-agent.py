
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

MIN_PIXLES = 5
ACTION_TIMEOUT = 4
STEER_GAIN = 0.3

TURNING_NONE = 0
TURNING_WAIT = 1
TURNING_DONE = 2

MAX_TIMEOUT = 5

ACTION_NONE = 0
ACTION_FORWARD = 1
ACTION_STEER = 2
ACTION_TURN = 3

action = ACTION_NONE

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
actionStr = ""

actionTimeout = 0
minAngle = 0
maxAngle = 0
angle = 0
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
    global run, continuousMode, turningState
    print("Starting...")
    turningState = TURNING_NONE
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


def processImage():
    global processedImage, maxAngle, minAngle, angle, turnDistance, action, turningState, actionTimeout, actionStr

    cameraImage = receivedProcessedImage.copy()

    processedImage = Image.new("RGB", cameraImage.size)
    processedImage.paste(cameraImage)

    r = 28  # 28 pixels = 35mm

    ha = math.atan2(0.5, r + 0.5) * 180 / math.pi
    ha *= 2

    # print("Angle is " + str(ha))

    p1 = 255
    p2 = 0

    pixelMap = processedImage.load()

    angles = []
    currentAngle = None

    a = -135
    c = 0
    while a <= 135:
        a += ha
        ra = a * math.pi / 180 + math.pi

        x = int(r * math.cos(ra) + 40)
        y = int(r * math.sin(ra) + 32)

        p = cameraImage.getpixel((x, y))
        if p > 127:
            pixelMap[x, y] = (255, 0, 0)
            if currentAngle is not None:
                currentAngle["ae"] = a - ha
                currentAngle["ce"] = c - 1
                currentAngle = None
        else:
            pixelMap[x, y] = (0, 255, 0)
            if currentAngle is None:
                currentAngle = {"as": a, "cs": c}
                angles.append(currentAngle)

        c += 1

    if currentAngle is not None:
        currentAngle["ae"] = a - ha
        currentAngle["ce"] = c - 1

    print("Angles " + str(angles))

    angle = None
    for a in angles:
        c = a["ce"] - a["cs"]
        if c > MIN_PIXLES:
            midAngle = (a["ae"] + a["as"]) / 2
            if angle is None or abs(midAngle) < abs(angle):
                angle = midAngle

    rDistance = 35  # 28 pixels = 35mm

    if angle is not None:
        if angle > 0:
            a = 90 - angle * STEER_GAIN

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
            a = 90 + angle * STEER_GAIN

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

    if angle is None:
        actionTimeout += 1
        if actionTimeout >= ACTION_TIMEOUT:
            action = ACTION_NONE
            actionStr = "drive 0 0"
    elif abs(angle) < 2:
        actionTimeout = 0
        action = ACTION_FORWARD
        actionStr = "drive 0 " + str(forwardSpeed)
    elif abs(angle) <= 90:
        actionTimeout = 0
        action = ACTION_STEER
        actionStr = "steer " + str(turnDistance) + " " + str(forwardSpeed)
    else:
        actionTimeout = 0
        action = ACTION_TURN
        actionStr = "turn " + str(-round(angle, 1))

    pyroslib.publish("followLine/feedback",
                     "frameTime:" + frameTime + ","
                     + "angle:" + str(round(angle, 1)) + ","
                     + "turnDistance:" + str(turnDistance) + ","
                     + "action:" + actionStr)

    message = processedImage.tobytes("raw")
    pyroslib.publish("followLine/processed", message)

    if DEBUG:
        print("Angle " + str(angle) + ", turnDistance " + str(turnDistance) + ", action " + actionStr + ", frame time " + frameTime)

    # print("Scanned " + str(c) + " points, midAngle=" + str(midAngle) + ", minAngle=" + str(minAngle) + ", maxAngle=" + str(maxAngle) + " turnDistance=" + str(turnDistance))


def goOneStep():
    global turningState

    # if action == ACTION_FORWARD:
    #     pyroslib.publish("move/drive", "0 " + str(forwardSpeed - 2))
    # elif action == ACTION_STEER:
    #     pyroslib.publish("move/steer", str(turnDistance) + " " + str(forwardSpeed))

    if action == ACTION_FORWARD:
        # pyroslib.publish("move/drive", "0 " + str(forwardSpeed - 1))
        wheelDeg("fl", str(0))
        wheelDeg("bl", str(0))
        wheelDeg("fr", str(0))
        wheelDeg("br", str(0))

        wheelSpeed("fl", forwardSpeed - 1)
        wheelSpeed("fr", forwardSpeed - 1)
        wheelSpeed("bl", forwardSpeed - 1)
        wheelSpeed("br", forwardSpeed - 1)
    elif action == ACTION_STEER:
        # pyroslib.publish("move/steer", str(turnDistance) + " " + str(forwardSpeed))
        print("STEER " + str(turnDistance) + " " + str(forwardSpeed))
        steer(turnDistance, forwardSpeed)
    elif action == ACTION_TURN:
        pyroslib.publish("move/turn", str(int(angle)))
        print("PUBLISHED TURN!!!")
        turningState = TURNING_WAIT
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
