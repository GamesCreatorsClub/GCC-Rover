
#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import math

from maze import MazeAttitude
from rover import Radar, RoverState

import unittest

SQRT2 = math.sqrt(2)




class BasicTests(unittest.TestCase):
    def __init__(self, methodName):
        super(BasicTests, self).__init__(methodName)
        self.attitude = None
        self.radar = None
        self.state = None

    def printWallLines(self, a):
        if self.attitude.lines[a].angle is None:
            print("{:3d} -> point too far - not calculated".format(a))
        else:
            angle = int(self.attitude.lines[a].angle * 180 / math.pi)
            point = self.attitude.points[a]

            if point is None:
                print("{:3d} -> line at {:3d} angle".format(a, angle))
            else:
                if point == MazeAttitude.LEFT_WALL:
                    wall = "left wall"
                elif point == MazeAttitude.RIGHT_WALL:
                    wall = "right wall"
                elif point == MazeAttitude.FRONT_WALL:
                    wall = "front wall"
                elif point == MazeAttitude.BACK_WALL:
                    wall = "back wall"
                else:
                    wall = "no wall"

                print("{:3d} -> line at {:3d} angle belogs to {:s}".format(a, angle, wall))

    def printWall(self, w):
        if w.angle is None:
            print("Wall {:3d} -> is too far - not calculated".format(w.ds_angle))
        else:
            if w.distance is None:
                print("Wall {:3d} -> has angle {:3d} but is too far - distance not calculated".format(w.ds_angle, int(w.angle * 180 / math.pi)))
            else:
                print("Wall {:3d} -> has angle {:3d} and is at {:3d}".format(w.ds_angle, int(w.angle * 180 / math.pi), w.distance))

    def printWalls(self, attitude):
        for p in attitude.points:
            self.printWallLines(p)
        for a, w in attitude.walls.items():
            self.printWall(w)
        print("----------------------------------------------------------")

    def createAttitudeWithDistances(self, distances_array):
        radar_values = {k: v for k, v in zip(MazeAttitude.POINTS, distances_array)}
        radar_last_values = {k: v for k, v in radar_values.items()}
        radar_status = {k: 0 for k in radar_values}

        self.attitude = MazeAttitude()
        self.radar = Radar(0, radar_values, radar_status, Radar(0, radar_last_values, radar_status))
        self.state = RoverState(None, None, None, self.radar, None, None)
        self.attitude.calculate(self.state)
        self.printWalls(self.attitude)

    def assertWallPoints(self, wall_types):
        for i in zip(MazeAttitude.POINTS, range(len(MazeAttitude.POINTS))):
            assert self.attitude.points[i[0]] == wall_types[i[1]]

    def assertWallAnglesAndDistances(self, walls_to_assert):
        for wall_angle in walls_to_assert:
            angle = walls_to_assert[wall_angle][0]
            distance = walls_to_assert[wall_angle][1]

            wall = self.attitude.walls[wall_angle]
            wall_angle = wall.angle * 180 / math.pi
            wall_distance = wall.distance

            if angle < 0:
                assert angle * 1.05 <= wall_angle <= angle / 1.05
            else:
                assert angle * 1.05 >= wall_angle >= angle / 1.05
            assert distance * 1.05 >= wall_distance >= distance / 1.05

    def test_box(self):
        self.createAttitudeWithDistances([10, SQRT2 * 10, 10, SQRT2 * 10, 10, SQRT2 * 10, 10, SQRT2 * 10])

        self.assertWallPoints([MazeAttitude.FRONT_WALL, MazeAttitude.RIGHT_WALL, MazeAttitude.RIGHT_WALL, MazeAttitude.RIGHT_WALL,
                               MazeAttitude.BACK_WALL, MazeAttitude.LEFT_WALL, MazeAttitude.LEFT_WALL, MazeAttitude.LEFT_WALL])

        self.assertWallAnglesAndDistances({0: (90, 10), 90: (0, 10), 180: (90, 10), 270: (0, 10)})

    def test_front_back_long(self):
        self.createAttitudeWithDistances([50, SQRT2 * 10, 10, SQRT2 * 10, 50, SQRT2 * 10, 10, SQRT2 * 10])

        self.assertWallPoints([MazeAttitude.FRONT_WALL, MazeAttitude.RIGHT_WALL, MazeAttitude.RIGHT_WALL, MazeAttitude.RIGHT_WALL,
                               MazeAttitude.BACK_WALL, MazeAttitude.LEFT_WALL, MazeAttitude.LEFT_WALL, MazeAttitude.LEFT_WALL])

        self.assertWallAnglesAndDistances({0: (90, 50), 90: (0, 10), 180: (90, 50), 270: (0, 10)})

    def test_chicane(self):
        self.createAttitudeWithDistances([15, SQRT2 * 10, 10, SQRT2 * 10, 50, SQRT2 * 10, 10, 25])

        self.assertWallPoints([MazeAttitude.FRONT_WALL, MazeAttitude.RIGHT_WALL, MazeAttitude.RIGHT_WALL, MazeAttitude.RIGHT_WALL,
                               MazeAttitude.BACK_WALL, MazeAttitude.LEFT_WALL, MazeAttitude.LEFT_WALL, MazeAttitude.FRONT_WALL])

        self.assertWallAnglesAndDistances({0: (-81, 14), 90: (0, 10), 180: (90, 50), 270: (0, 10)})

    # state.radar.radar[180] = 50
    # state.radar.radar[315] = 30
    # attitude.calculate(state)
    # printWalls()


if __name__ == '__main__':
    import nose2
    nose2.main()