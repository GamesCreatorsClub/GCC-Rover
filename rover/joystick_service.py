#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import math
import time
import traceback

from approxeng.input.selectbinder import ControllerResource

import pyroslib as pyros


joystick = None
last_presses = None
last_axes = {}
trying_counter = 0
trying_frequency = 50  # 5 seconds
last_status_broadcast = 0
status_broadcast_time = 5  # every 5 seconds

TRIGGER_LOW = 110
TRIGGER_HIGH = 170
TRIGGER_SERVO = 1

ELEVATOR_LOW = 85
ELEVATOR_HIGH = 210
ELEVATOR_SERVO = 2

BARRLES_LOW = 90
BARRLES_HIGH = 130
BARRLES_SERVO = 0

max_speed = 100
max_rot_speed = 100

motor_speed = 0.5
motor_current_speed = -1
motor_change_speed = 0.01


def moveServo(servoid, position):
    # try:
    #     with open("/dev/servoblaster", 'w') as f:
    #         f.write(str(servoid) + "=" + str(position) + "\n")
    # except Exception as ex:
    #     print("Sending servo exception: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
    pass

def increase(value):
    if value < 300:
        if value >= 150:
            value += 50
        elif value >= 100:
            value += 25
        elif value >= 50:
            value += 10
        else:
            value += 5
    return value


def decrease(value):
    if value > 10:
        if value <= 50:
            value -= 5
        elif value <= 100:
            value -= 10
        elif value <= 150:
            value -= 25
        else:
            value -= 50
    return value


def send_motor_servo(servo_position):
    print("  Setting motor servo to " + str(servo_position) + "; motor_speed=" + str(motor_speed))
    moveServo(BARRLES_SERVO, servo_position)


def loop():
    global joystick, last_presses, trying_counter, last_status_broadcast
    global max_speed, max_rot_speed, motor_speed, motor_current_speed

    if motor_current_speed >= 0:
        print("Testing motor speed motor_current_speed=" + str(motor_current_speed) + " <--> " + str(motor_speed))
        motor_changed = False
        if motor_current_speed > motor_speed:
            motor_current_speed -= motor_change_speed
            motor_changed = True
        elif motor_current_speed < motor_speed:
            motor_current_speed += motor_change_speed
            motor_changed = True

        if motor_changed:
            print("Changed motor current speed to " + str(motor_current_speed))
            send_motor_servo(int(((BARRLES_HIGH - BARRLES_LOW) * motor_current_speed + BARRLES_LOW)))

    try:
        if joystick is None:
            try:
                if trying_counter % trying_frequency == 0:
                    print("Obtaining joystick...")
                joystick = ControllerResource().__enter__()
                trying_counter = 0
                print("Obtained joystick.")

                try:
                    axes = joystick.axes

                    print("Setting up joystick values...")
                    for axis_name in joystick.axes.names:
                        last_axes[axis_name] = joystick[axis_name]
                    print("Set up joystick values.")
                except Exception as ex:
                    print("At creation: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
                    joystick = None
            except:
                trying_counter += 1
                now = time.time()
                if last_status_broadcast + status_broadcast_time < now:
                    pyros.publish("joystick/status", "none")
                    last_status_broadcast = now

        else:
            if joystick.connected:
                presses = joystick.check_presses()

                axes = joystick.axes
                axes_changed = False
                for axis_name in joystick.axes.names:
                    if last_axes[axis_name] != joystick[axis_name]:
                        axes_changed = True

                if presses['dup']:
                    max_speed = increase(max_speed)
                    axes_changed = True
                    print("  increased speed to " + str(max_speed))
                elif presses['ddown']:
                    max_speed = decrease(max_speed)
                    axes_changed = True
                    print("  decreased speed to " + str(max_speed))
                if presses['dright']:
                    max_rot_speed = increase(max_rot_speed)
                    axes_changed = True
                elif presses['dleft']:
                    max_rot_speed = decrease(max_rot_speed)
                    axes_changed = True

                if axes_changed:
                    lx = joystick['lx']
                    ly = joystick['ly']

                    ld = math.sqrt(lx * lx + ly * ly)
                    if ld > 1:
                        ld = 1.0

                    rx = joystick['rx']
                    ry = joystick['ry']

                    rd = math.sqrt(rx * rx + ry * ry)
                    if rd > 1:
                        rd = 1.0

                    if rd < 0.1 and abs(lx) < 0.1:
                        pyros.publish("move/stop", "")
                    elif abs(lx) < 0.1:
                        rd = math.sqrt(rx * rx + ry * ry)
                        if rd > 1:
                            rd = 1.0
                        ra = math.atan2(rx, ry) * 180 / math.pi
                        pyros.publish("move/drive", str(int(ra)) + " " + str(int(rd * max_speed)))
                    elif rd < 0.1:
                        pyros.publish("move/rotate", str(int(lx * max_rot_speed)))
                    else:
                        ra = math.atan2(rx, ry) * 180 / math.pi

                        if abs(lx) < 0.1:
                            distance = 1.0
                        else:
                            distance = math.atan(rd / lx) * 2 / math.pi

                        distance *= 300

                        speed = max(rd * max_speed, abs(lx * max_rot_speed))

                        if ra > 90 and ra < 270:
                            speed = -speed

                        pyros.publish("move/steer", str(int(distance)) + " " + str(int(speed)) + " " + str(int(ra)))

                    if joystick['r1'] is not None:
                        motor_changed = False
                        if presses['l2']:
                            motor_speed -= 0.1
                            if motor_speed < 0:
                                motor_speed = 0

                        elif presses['r2']:
                            motor_speed += 0.1
                            if motor_speed > 1:
                                motor_speed = 1

                    else:
                        rt = joystick['rt']
                        servo_position = int((TRIGGER_HIGH - TRIGGER_LOW) * (1 - rt) + TRIGGER_LOW)
                        # print("  Setting trigger servo to " + str(servo_position) + "; rt=" + str(rt))
                        moveServo(TRIGGER_SERVO, servo_position)

                    if joystick['l1'] is not None:
                        servo_position = int((ELEVATOR_HIGH - ELEVATOR_LOW) * (1 - ly) / 2 + TRIGGER_LOW)
                        # print("  Setting elevator servo to " + str(servo_position) + "; ly=" + str(ly))
                        moveServo(ELEVATOR_SERVO, servo_position)

                    if presses['square']:
                        if motor_current_speed > 0:
                            motor_current_speed = -1
                            send_motor_servo(BARRLES_LOW)
                        else:
                            motor_current_speed = 0

                    for axis_name in joystick.axes.names:
                        last_axes[axis_name] = joystick[axis_name]

                now = time.time()
                if last_status_broadcast + status_broadcast_time < now:
                    pyros.publish("joystick/status", "connected")
                    last_status_broadcast = now

            else:
                print("Joystick is disconnected...")
                joystick = None

    except Exception as ex:
        joystick = None
        print("At loop: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))


if __name__ == "__main__":
    try:
        print("Starting jcontroller service...")

        pyros.init("joystick-service", unique=True)

        print("Started joystick service.")

        pyros.publish("servo/9", "175")

        pyros.forever(0.1, loop, loop_sleep=0.02)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
