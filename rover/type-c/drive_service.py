#!/usr/bin/env python3

#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import math
import pyroslib
import time
import traceback


# noinspection PyMethodMayBeStatic
class DriveService:
    def __init__(self):
        self.debug = True
        self.debug_timing = True

    def log(self, source: str, msg: str):
        print(source + ": " + msg)

    def all_wheels(self, fld: float, frd: float, bld: float, brd: float, fls: int, frs: int, bls: int, brs: int):
        pyroslib.publish("wheel/all", "fld:" + str(fld) + " frd:" + str(frd) + " bld:" + str(bld) + " brd:" + str(brd) + " fls:" + str(fls) + " frs:" + str(frs) + " bls:" + str(bls) + " brs:" + str(brs))

    def all_wheels_deg(self, fld: float, frd: float, bld: float, brd: float):
        pyroslib.publish("wheel/all", "fld:" + str(fld) + " frd:" + str(frd) + " bld:" + str(bld) + " brd:" + str(brd))

    def all_wheels_speed(self, fls: int, frs: int, bls: int, brs: int):
        pyroslib.publish("wheel/all", "fls:" + str(fls) + " frs:" + str(frs) + " bls:" + str(bls) + " brs:" + str(brs))

    def rotate(self, speed: int):
        self.all_wheels_deg(45.0, 135.0, 315.0, 225.0)
        self.all_wheels_speed(speed, speed, speed, speed)
        if self.debug:
            self.log("rotate", "s=" + str(speed))

    def steer(self, args):
        def calc_angle(_xo, _yo, xw, yw, _distance):
            xw = xw - _xo
            yw = yw - _yo
            a = int(math.atan2(xw, yw) * 180 / math.pi)
            if _distance >= 0:
                return a + 90
            else:
                return a - 90

        def calc_speed_difference(_speed, _xo, _yo, xw, yw):
            mr = math.sqrt(_xo * _xo + _yo * _yo)
            wr = math.sqrt((xw - _xo) * (xw - _xo) + (yw - _yo) * (yw - _yo))
            return int(wr * _speed / mr)

        distance = int(float(args[0]))
        if len(args) > 1:
            speed = int(float(args[1]))
        else:
            speed = 0

        if len(args) > 2:
            angle = - int(float(args[2])) * math.pi / 180
        else:
            angle = 0  # 0 * math.pi / 180

        if speed < 0:
            angle = angle + math.pi
            if angle > 2 * math.pi:
                angle = angle - 2 * math.pi

        xo = math.cos(angle) * distance
        yo = math.sin(angle) * distance

        wheel_distance = 53

        fr_angle = calc_angle(xo, yo, wheel_distance, wheel_distance, distance)
        fl_angle = calc_angle(xo, yo, -wheel_distance, wheel_distance, distance)
        br_angle = calc_angle(xo, yo, wheel_distance, -wheel_distance, distance)
        bl_angle = calc_angle(xo, yo, -wheel_distance, -wheel_distance, distance)

        fr_speed = min(300, calc_speed_difference(speed, xo, yo, wheel_distance, wheel_distance))
        fl_speed = min(300, calc_speed_difference(speed, xo, yo, -wheel_distance, wheel_distance))
        br_speed = min(300, calc_speed_difference(speed, xo, yo, wheel_distance, -wheel_distance))
        bl_speed = min(300, calc_speed_difference(speed, xo, yo, -wheel_distance, -wheel_distance))

        if self.debug:
            self.log("steer", "d=" + str(distance) + " s=" + str(speed) + " a=" + str(angle) + " fra=" + str(fr_angle) + " fla=" + str(fl_angle) + " bra=" + str(br_angle) + " bla=" + str(bl_angle) + " frs=" + str(fr_speed) + " fls=" + str(fl_speed) + " brs=" + str(br_speed) + " bls=" + str(bl_speed) + " args:" + str(args))

        if speed != 0:
            self.all_wheels(fl_angle, fr_angle, bl_angle, br_angle, fl_speed, fr_speed, bl_speed, br_speed)
        else:
            self.all_wheels_deg(fl_angle, fr_angle, bl_angle, br_angle)

    def drive(self, args):
        angle = float(args[0])
        speed = int(args[1])

        if angle < 0:
            angle += 360
        if angle >= 360:
            angle -= 360

        if self.debug_timing:
            print(str(int(time.time() * 1000) % 10000000) + ": driving  fld:" + str(angle) + " frd:" + str(angle) + " bld:" + str(angle) + " brd:" + str(angle) + " fls:" + str(speed) + " frs:" + str(speed) + " bls:" + str(speed) + " brs:" + str(speed))
        self.all_wheels(angle, angle, angle, angle, speed, speed, speed, speed)

    def stop_all_wheels(self):
        self.all_wheels_speed(0, 0, 0, 0)

    def align_all_wheels(self):
        self.all_wheels_deg(0, 0, 0, 0)

    # noinspection PyUnusedLocal
    def process_command(self, topic, message, groups):
        try:
            command = groups[0]
            args = message.split(" ")
            if command == "drive":
                self.drive(args)
            elif command == "rotate":
                speed = int(args[0])
                self.rotate(speed)
            elif command == "steer":
                self.steer(args)
            elif command == "stop":
                self.stop_all_wheels()
            else:
                print("Received unknown command " + command)
        except Exception as exception:
            print("ERROR: " + str(exception) + "\n" + ''.join(traceback.format_tb(exception.__traceback__)))

    def start_service(self):
        print("Starting drive service...")

        pyroslib.subscribe("move/+", self.process_command)
        pyroslib.init("drive-service")

        print("Started drive service.")

        self.stop_all_wheels()
        self.align_all_wheels()

    def loop(self):
        # Nothing to do
        pass


if __name__ == "__main__":
    try:
        service = DriveService()
        service.start_service()

        pyroslib.forever(0.02, service.loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
