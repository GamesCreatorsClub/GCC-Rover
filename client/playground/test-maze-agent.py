
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import RPi.GPIO as GPIO
import time, sys, random
import paho.mqtt.client as mqtt


GPIO.setmode(GPIO.BCM)

TRIG = 11 # 23
ECHO = 8 # ß24

SERVO_NUMBER = 8

print("Distance measurement in progress")

GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

GPIO.output(TRIG, False)

print("Waiting for sensor to settle")

time.sleep(1)

connected = False

TURNING_STEP = 22.5
SERVO_SPEED = 0.5
TURN_SPEED = 44
FORWARD_SPEED = 50
TOTAL_STEPS = 30

direction = TURNING_STEP
servoAngle = -90


client = mqtt.Client("Maze1#" + str(random.randint(1000, 9999)))

wheelsStopped = False

def moveServo(angle):
    angle += 150
    angle = int(angle)

    f = open("/dev/servoblaster", 'w')
    f.write(str(SERVO_NUMBER) + "=" + str(angle) + "\n")
    f.close()
    #print("Servo to " + str(angle))


def toStr(n):
    s = str(n)
    i = s.index('.')
    l = len(s)
    if i + 2 >= l:
        s = s + '0'
        l = l + 1
    if i + 2 >= l:
        s = s + '0'
        l = l + 1
    while l < 8:
        s = ' ' + s
        l = l + 1
    return s



def readDistance():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    start = time.time()
    while GPIO.input(ECHO) == 0 and time.time() - start < 0.1:
        pass

    pulse_start = time.time()

    while GPIO.input(ECHO) == 1 and time.time() - start < 0.3:
        pass

    pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start

    distance = pulse_duration * 171500

    distance = round(distance, 2)

    return distance


def onConnect(mqttClient, data, flags, rc):
    global connected
    try:
        if rc == 0:
            connected = True
            client.subscribe("wheel/fl/speed")
        else:
            print("ERROR: Connection returned error result: " + str(rc))
            sys.exit(rc)
    except Exception as ex:
        print("ERROR: Got exception on connect; " + str(ex))


def onMessage(mqttClient, data, msg):
    global wheelsStopped

    try:
        payload = str(msg.payload, 'utf-8')
        topic = msg.topic
        # print("   Received message on " + topic + ": " + payload)
        if topic == "wheel/fl/speed" and payload == "0":
            # print("     Signalling that wheels have stopped!")
            wheelsStopped = True

    except Exception as ex:
        print("ERROR: Got exception on message; " + str(ex))


def maxDistanceAngle(m):
    mxd = 0
    mxda = -90
    for a in m:
        d = m[a]
        if d > mxd:
            mxd = d
            mxda = a
    return mxda

def minDistanceAngle(m):
    mnd = 10000
    mnda = -90
    for a in m:
        d = m[a]
        if d < mnd:
            mnd = d
            mnda = a
    return mnda


def scan():
    global servoAngle, direction

    values = {}
    loop = True
    while loop:
        moveServo(servoAngle)
        time.sleep(SERVO_SPEED * TURNING_STEP / 60.0)
        distance = readDistance()
        values[servoAngle] = distance

        servoAngle = servoAngle + direction
        if servoAngle > 90:
            servoAngle = servoAngle - direction
            loop = False
        elif servoAngle < -90:
            servoAngle = servoAngle - direction
            loop = False

    direction = -direction
    return values


def checkValue(values, mxda):
        moveServo(mxda)
        time.sleep(1)
        distance = readDistance()
        print("  Checked " + str(mxda) + ", old=" + str(values[mxda]) + " new="+ str(distance))
        values[mxda] = distance
        newMxda = maxDistanceAngle(values)

        return mxda == newMxda

def sleep(amount):
    for i in range(0, int(amount / 0.02)):
        client.loop(0.005)
        time.sleep(0.015)

def forward():
    try:
        print("** going forward")
        client.publish("drive", "forward>" + str(0))
        sleep(1)
        client.publish("drive", "forward>" + str(FORWARD_SPEED))
        sleep(0.3)
    finally:
        client.publish("drive", "stop")


def back():
    try:
        print("** going back")
        client.publish("drive", "back>" + str(0))
        sleep(1)
        client.publish("drive", "back>" + str(FORWARD_SPEED))
        sleep(0.3)
    finally:
        client.publish("drive", "stop")


def rotate(rotateDirection, angle):
    global wheelsStopped
    sleepTime = 0.025 * angle
    print("** going " + rotateDirection + " - angle " + str(angle) + " sleep " + str(sleepTime))
    try:
        client.publish("drive", rotateDirection + str(0))
        sleep(0.5)
        # client.publish("drive", rotateDirection + str(int(TURN_SPEED * 0.6)))
        # sleep(0.5)
        # client.publish("drive", rotateDirection + str(int(TURN_SPEED)) + "," + str(int(angle * 22.5)))
        wheelsStopped = False
        if angle >= 0:
            client.publish("drive", rotateDirection + str(int(TURN_SPEED)) + "," + str(int(15)))
        else:
            client.publish("drive", rotateDirection + str(int(TURN_SPEED)) + "," + str(int(-15)))

        # print("-- waiting for wheels to stop...")
        while not wheelsStopped:
            for it in range(0, 10):
                time.sleep(0.0015)
                client.loop(0.0005)
        # print("-- wheels to stopped.")
        #
        # sleep(sleepTime)
    finally:
        client.publish("drive", "stop")
    sleep(0.1)


def printValues(values, mxda, mnda):
    angles = list(values.keys())
    angles.sort()
    print("  ", end="")
    for a in angles:
        if a == mxda:
            print("{0!s:<10}".format((str(a) + "*")), end="")
        elif a == mnda:
            print("{0!s:<10}".format((str(a) + "^")), end="")
        else:
            print("{0!s:<10}".format(a), end="")
    print("")

    print("  ", end="")
    for a in angles:
        print("{0!s:<10}".format(values[a]), end="")
    print("")


#
# Initialisation
#

print("Starting maze program...")

client.on_connect = onConnect
client.on_message = onMessage

client.connect("localhost", 1883, 60)

while not connected:
    client.loop()


print("Connected to the broker.")
steps = 0
try:
    while steps < TOTAL_STEPS:

        print("Scanning...")
        values = scan()
        mxda = maxDistanceAngle(values)
        mnda = minDistanceAngle(values)

        printValues(values, mxda, mnda)
        print("  Max distance @ " + str(mxda) + " (" + str(values[mxda]) + "), min distance @ " + str(mnda) + " (" + str(values[mnda]) + ")")
        print("")

        for it in range(0, 10):
            time.sleep(0.0015)
            client.loop(0.0005)

        if values[mnda] < 50:
            back()
        else:
            print("  Checking values...")
            if checkValue(values, mxda):
                if abs(mxda) < TURNING_STEP * 1.5:
                    forward()
                else:
                    if mxda < 0:
                        delta = int(abs(mxda / TURNING_STEP))
                        rotate("pivotLeft>", -delta)
                        forward()
                    else:
                        delta = int(abs(mxda / TURNING_STEP))
                        rotate("pivotRight>", delta)
                        forward()
            else:
                print("  Check failed. Error - new max is now " + str(values[mxda]))

        steps += 1
except Exception as ex:
    print("ERROR: " + str(ex))
finally:
    GPIO.cleanup()
