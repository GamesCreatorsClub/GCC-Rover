import paho.mqtt.client as mqtt
import time
import smbus


client = mqtt.Client("Straightlineagent")

leftSideSpeed = 0
rightSideSpeed = 0
integratedError = 0

gyroCentre = 0
gyroMin = 0
gyroMax = 0

driving = False


def onConnect(client, data, rc):
    global connected
    print("connected")
    client.subscribe("straight")


def onMessage(client, data, msg):
    global  centre, integratedError
    print("Ding! You've got mail!")
    payload= str(msg.payload, 'utf-8')
    if msg.topic == "straight":
        if payload == "forward":
            startDriving()
        if payload == "calibrate":
            centre = getCentre()
            integratedError = 0
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
i2c_address=0x69 # i2c slave address of the L3G4200D
i2c_bus.write_byte_data(i2c_address, 0x20, 0x0F) # normal mode and all axes on to control reg1
i2c_bus.write_byte_data(i2c_address, 0x23, 0x20) # full 2000dps to control reg4

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


def getError(gyroAngle):
    if gyroAngle > gyroMax or gyroAngle < gyroMin:
        return gyroAngle + z - gyroCentre
    return 0.0

calibrateGyro()

SPEED = 250

SPEED_GAIN = 0.3 # 0.4
SPEED_MAX_CONTROL = 75

CONTROL_STEERING = True
CONTROL_MOTORS = False

CONTROL_TYPE = CONTROL_STEERING

STEER_GAIN = 0.015
SPEER_MAX_CONTROL = 4.5
INTEGRAL_FADE_OUT = 0.95

# P_GAIN = 0.9 and I_GAIN = 0.1

P_GAIN = 0.85
I_GAIN = 0.15
D_GAIN = 0.0


wheelDeg("fl", 0)
wheelDeg("fr", 0)
wheelDeg("bl", 0)
wheelDeg("br", 0)

rightSideSpeed = 75
leftSideSpeed = 75

leftDeg = 0
rightDeg = 0

proportionalError = 0
integratedError = 0

z = readGyroZ()
lastTimeGyroRead = time.time()

while True:
    for i in range(0, 10):
        time.sleep(0.045)
        client.loop(0.005)

    z = readGyroZ()
    thisTimeGyroRead = time.time()
    if driving:

        integratedError = integratedError * INTEGRAL_FADE_OUT


        proportionalError = getError(z)
        integratedError = integratedError + proportionalError * (thisTimeGyroRead - lastTimeGyroRead)


        control = P_GAIN * proportionalError + I_GAIN * integratedError

        controlSpeed = int(control * SPEED_GAIN)

        if controlSpeed > SPEED_MAX_CONTROL:
            controlSpeed = SPEED_MAX_CONTROL
        elif controlSpeed < -SPEED_MAX_CONTROL:
            controlSpeed = -SPEED_MAX_CONTROL

        controlSteer = control * STEER_GAIN
        if controlSteer > SPEER_MAX_CONTROL:
            controlSteer = SPEER_MAX_CONTROL
        elif controlSteer < -SPEER_MAX_CONTROL:
            controlSteer = -SPEER_MAX_CONTROL


        if CONTROL_TYPE == CONTROL_MOTORS:
            rightSideSpeed = SPEED - controlSpeed
            leftSideSpeed = SPEED + controlSpeed
        else:
            rightSideSpeed = SPEED
            leftSideSpeed = SPEED

        if CONTROL_TYPE == CONTROL_STEERING:
            leftDeg = int(controlSteer)
            rightDeg = int(controlSteer)
        else:
            leftDeg = 1
            rightDeg = 1

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

    print("Z: " + str(z) + " drift: " + str(proportionalError) + " speed: " + str(leftSideSpeed) + " <-> " + str(rightSideSpeed) + " / " + str(leftDeg) + " <-> " + str(rightDeg))

