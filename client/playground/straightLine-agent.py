import paho.mqtt.client as mqtt
import time
import smbus


client = mqtt.Client("Straightlineagent")

leftSideSpeed = 0
rightSideSpeed = 0
integratedDrift = 0


driving = False


def onConnect(client, data, rc):
    global connected
    print("connected")
    client.subscribe("straight")


def onMessage(client, data, msg):
    global  centre, integratedDrift
    print("Ding! You've got mail!")
    payload= str(msg.payload, 'utf-8')
    if msg.topic == "straight":
        if payload == "forward":
            startDriving()
        if payload == "calibrate":
            centre = getCentre()
            integratedDrift = 0
        if payload == "stop":
            stopDriving()




client.on_connect = onConnect
client.on_message = onMessage

print("DriverAgent: Starting...")

client.connect("localhost", 1883, 60)



def wheelDeg(wheelName, angle):
    topic = "wheel/" + wheelName + "/deg"
    client.publish(topic, str(angle))

def startDriving():
    global driving, leftSideSpeed, rightSideSpeed

    print("DRIVE DIRVE DRIVE!")
    driving = True
    leftSideSpeed = 75
    rightSideSpeed = 75

def stopDriving():
    global leftSideSpeed, rightSideSpeed, driving
    print("STOP STOP STOP!")
    leftSideSpeed = 0
    rightSideSpeed = 0

    driving = False



i2c_bus=smbus.SMBus(1)
#i2c slave address of the L3G4200D
i2c_address=0x69

#initialise the L3G4200D

#normal mode and all axes on to control reg1
i2c_bus.write_byte_data(i2c_address,0x20,0x0F)
#full 2000dps to control reg4
i2c_bus.write_byte_data(i2c_address,0x23,0x20)


def getZ():
    i2c_bus.write_byte(i2c_address, 0x2C)
    Z_L = i2c_bus.read_byte(i2c_address)
    i2c_bus.write_byte(i2c_address, 0x2D)
    Z_H = i2c_bus.read_byte(i2c_address)
    Z = Z_H << 8 | Z_L

    if Z & (1 << 15):
        Z = Z | ~0xff
    else:
        Z = Z & 0xff
    return Z

def getCentre():
    c = 0
    avg = 0

    min = getZ()
    max = getZ()
    while c < 100:
        print("collecting still gyroscope...")
        Z = getZ()

        avg += Z

        c += 1
        if Z > max:
            max = Z
        if Z < min:
            min = Z

        time.sleep(0.02)
        avg = avg / 100.0

    return {"min" : min, "max" : max, "avg" : avg}


def getDrift(z, centre):
    if z < centre["min"]:
        return z - centre["avg"]
    if z > centre["max"]:
        return z - centre["avg"]
    return 0.0

centre = getCentre()

SPEED = 250

SPEED_GAIN = 0.3 # 0.4
SPEED_MAX_CONTROL = 75

STEER_GAIN = 0.015
SPEER_MAX_CONTROL = 4.5

wheelDeg("fl", 0)
wheelDeg("fr", 0)
wheelDeg("bl", 0)
wheelDeg("br", 0)

rightSideSpeed = 75
leftSideSpeed = 75

leftDeg = 0
rightDeg = 0

proportionalDrift = 0
integratedDrift = 0

while True:
    for i in range(0, 10):
        time.sleep(0.045)
        client.loop(0.005)

    z = getZ()
    if driving:

        proportionalDrift = getDrift(z, centre)
        integratedDrift = integratedDrift + proportionalDrift


        integratedDrift = integratedDrift * 0.98

        # 0.9 i 0.1
        control = 0.9 * proportionalDrift + 0.1 * integratedDrift
        control = 0.85 * proportionalDrift + 0.15 * integratedDrift

        controlSpeed = int(control * SPEED_GAIN)

        if controlSpeed > SPEED_MAX_CONTROL:
            controlSpeed = SPEED_MAX_CONTROL
        elif controlSpeed < -SPEED_MAX_CONTROL:
            controlSpeed = -SPEED_MAX_CONTROL

        # rightSideSpeed = SPEED - controlSpeed
        # leftSideSpeed = SPEED + controlSpeed
        rightSideSpeed = SPEED
        leftSideSpeed = SPEED

        controlSteer = control * STEER_GAIN
        if controlSteer > SPEER_MAX_CONTROL:
            controlSteer = SPEER_MAX_CONTROL
        elif controlSteer < -SPEER_MAX_CONTROL:
            controlSteer = -SPEER_MAX_CONTROL

        leftDeg = int(controlSteer)
        rightDeg = int(controlSteer)
        # leftDeg = 1
        # rightDeg = 1

    else:
        rightSideSpeed = 0
        leftSideSpeed = 0

    client.publish("wheel/fl/speed", leftSideSpeed)
    client.publish("wheel/bl/speed", leftSideSpeed)
    client.publish("wheel/fr/speed", rightSideSpeed)
    client.publish("wheel/br/speed", rightSideSpeed)

    wheelDeg("fl", str(int(leftDeg)))
    wheelDeg("fr", str(int(rightDeg)))
    wheelDeg("bl", 0)
    wheelDeg("br", 0)

    print("Z: " + str(z) + " drift: " + str(proportionalDrift) + " speed: " + str(leftSideSpeed) + " <-> " + str(rightSideSpeed) + " / " + str(leftDeg) + " <-> " + str(rightDeg))

