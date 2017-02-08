#!/usr/bin/python3

import paho.mqtt.client as mqtt
import time
import traceback
import smbus

DELAY = 0.15

speed = 100

STRAIGHT = 1
SLANT = 2
SIDEWAYS = 3

wheelPosition = STRAIGHT

client = mqtt.Client("DriveAgent")

gyroCentre = 0
gyroMin = 0
gyroMax = 0

i2c_bus=smbus.SMBus(1)
i2c_address=0x69 # i2c slave address of the L3G4200D
i2c_bus.write_byte_data(i2c_address, 0x20, 0x0F) # normal mode and all axes on to control reg1
i2c_bus.write_byte_data(i2c_address, 0x23, 0x20) # full 2000dps to control reg4

lastTimeGyroRead = time.time()

stack = []

def readGyroZ():
    global lastTimeGyroRead

    # print("        readGyroZ():")
    thisTimeGyroRead = time.time()

    # print("          reading first byte... ")
    i2c_bus.write_byte(i2c_address, 0x2C)
    zl = i2c_bus.read_byte(i2c_address)
    # print("          reading first byte - zl=" + str(zl))

    i2c_bus.write_byte(i2c_address, 0x2D)
    zh = i2c_bus.read_byte(i2c_address)
    # print("          reading second byte - zh=" + str(zh))

    z = zh << 8 | zl
    if z & (1 << 15):
        z = z | ~65535
    else:
        z = z & 65535

    degreesPerSecond = z * 70.00 / 1000
    degrees = degreesPerSecond * (lastTimeGyroRead - thisTimeGyroRead)

    # degrees = degreesPerSecond

    # print("          done: z=" + str(z) + " degrees=" + str(degrees) + " dps=" + str(degreesPerSecond) + " time=" + str(lastTimeGyroRead - thisTimeGyroRead))

    lastTimeGyroRead = thisTimeGyroRead

    return degrees


def calibrateGyro():
    global gyroCentre, gyroMin, gyroMax

    c = 0
    avg = 0

    min = readGyroZ()
    max = readGyroZ()
    while c < 50:
        z = readGyroZ()

        avg += z

        c += 1
        if z > max:
            max = z
        if z < min:
            min = z

        time.sleep(0.02)

    gyroCentre = avg / 50.0
    gyroMin = min
    gyroMax = max





def straightenWheels():
    global wheelPosition, DELAY, STRAIGHT

    wheelDeg("fl", 0)
    wheelDeg("fr", 0)
    wheelDeg("bl", 0)
    wheelDeg("br", 0)

    if wheelPosition != STRAIGHT:
        time.sleep(DELAY)
        wheelPosition = STRAIGHT

def slantWheels():
    global wheelPosition, DELAY, SLANT

    wheelDeg("fl", 60.0)
    wheelDeg("fr", -60.0)
    wheelDeg("bl", -60.0)
    wheelDeg("br", 60.0)
    if wheelPosition != SLANT:
        time.sleep(DELAY)
        wheelPosition = SLANT


def sidewaysWheels():
    global wheelPosition, DELAY, SIDEWAYS

    wheelDeg("fl", 90.0)
    wheelDeg("fr", -90.0)
    wheelDeg("bl", -90.0)
    wheelDeg("br", 90.0)
    if wheelPosition != SIDEWAYS:
        time.sleep(DELAY)
        wheelPosition = SIDEWAYS


def stopAllWheels():
    print("  Stop")
    wheelSpeed("fl", 0)
    wheelSpeed("fr", 0)
    wheelSpeed("bl", 0)
    wheelSpeed("br", 0)


def turnOnSpot(speed, angle):
    print("  Turn on spot " + str(speed) + ", angle " + str(angle))
    slantWheels()
    startSpeed = speed
    if speed > 0 and speed < 45:
        startSpeed = 45
    elif speed < 0 and speed > -45:
        startSpeed = -45


    wheelSpeed("fl", startSpeed)
    wheelSpeed("fr", -startSpeed)
    wheelSpeed("bl", startSpeed)
    wheelSpeed("br", -startSpeed)
    time.sleep(0.001)
    # print("    ... allowing other process...")
    client.loop(0.001)
    if angle is not None:
        angle = float(angle)
        # print("    angle is not None - reading gyro.")
        z = readGyroZ()
        gyroAngle = 0
        while (angle < 0 and gyroAngle > angle) or (angle > 0 and gyroAngle < angle):
            time.sleep(0.02)
            z = readGyroZ()
            # if z < gyroMin or z > gyroMax:
            #     gyroAngle = gyroAngle + z - gyroCentre
            gyroAngle = gyroAngle + z - gyroCentre
            # print("    waiting to turn on spot: z=" + str(round(z, 3)) + " total=" + str(round(gyroAngle, 3)))
            if abs(gyroAngle / angle) > 0.2 and speed != startSpeed:
                wheelSpeed("fl", speed)
                wheelSpeed("fr", -speed)
                wheelSpeed("bl", speed)
                wheelSpeed("br", -speed)
                time.sleep(0.001)
                # print("    ... allowing other process...")
                client.loop(0.001)

        stopAllWheels()

def moveMotors(amount):
    print("  Move motors " + str(amount))
    straightenWheels()
    wheelSpeed("fl", amount)
    wheelSpeed("fr", amount)
    wheelSpeed("bl", amount)
    wheelSpeed("br", amount)

def crabAlong(amount):
    print("  Crab along " + str(amount))
    sidewaysWheels()
    wheelSpeed("fl", amount)
    wheelSpeed("fr", -amount)
    wheelSpeed("bl", -amount)
    wheelSpeed("br", amount)


def wheelDeg(wheelName, angle):
    topic = "wheel/" + wheelName + "/deg"
    client.publish(topic, str(angle))
    # print("Published topic=" +  topic + "; msg=" + str(angle))

def wheelSpeed(wheelName, speed):
    topic = "wheel/" + wheelName + "/speed"
    client.publish(topic, str(speed))
    # print("Published topic=" +  topic + "; msg=" + str(speed))


def onConnect(client, data, rc):
    client.subscribe("drive/#")
    print("DriverAgent: Connected to rover")
    straightenWheels()


def onMessage(client, data, msg):
    global stack
    payload = str(msg.payload, 'utf-8')

    if msg.topic == "drive":
        stack.append(payload)

def processStack():
    global stack

    if len(stack) > 0:
        payload = stack[0]
        del stack[0]

        command = payload.split(">")[0]
        if len(payload.split(">")) > 1:
            command_args_list = payload.split(">")[1].split(",")
            args1 = command_args_list[0]
            args2 = None
            args3 = None
            if len(command_args_list) > 1:
                args2 = command_args_list[1]
            if len(command_args_list) > 2:
                args3 = command_args_list[2]
        else:
            args1 = 0
        if command == "forward":
            moveMotors(int(args1))
        elif command == "back":
            moveMotors(-int(args1))
        elif command == "motors":
            moveMotors(int(args1))
        elif command == "align":
            straightenWheels()
        elif command == "slant":
            slantWheels()
        elif command == "rotate":
            turnOnSpot(int(args1), args2)
        elif command == "pivotLeft":
            turnOnSpot(-int(args1), args2)
        elif command == "pivotRight":
            turnOnSpot(int(args1), args2)
        elif command == "stop":
            stopAllWheels()
        elif command == "sideways":
            sidewaysWheels()
        elif command == "crabLeft":
            crabAlong(-int(args1))
        elif command == "crabRight":
            crabAlong(int(args1))


client.on_connect = onConnect
client.on_message = onMessage

print("DriverAgent: Starting...")

client.connect("localhost", 1883, 60)

calibrateGyro()
print("Calibrated gyro offset=" + str(gyroCentre) + " min=" + str(gyroMin) + " max=" + str(gyroMax))

try:
    while True:
        for it in range(0, 10):
            time.sleep(0.0015)
            client.loop(0.0005)
            processStack()

except Exception as ex:
    print("ERROR: " + str(ex))
    print("ERROR: " + str(ex) + "\n" + str(traceback.format_exception(ex)))
