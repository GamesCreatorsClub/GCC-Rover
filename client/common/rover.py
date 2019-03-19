
#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import math
import time
import struct


WHEEL_CIRCUMFERENCE = 68 * math.pi
WHEEL_NAMES = ['fl', 'fr', 'bl', 'br']
RADAR_ANGLES = [0, 45, 90, 135, 180, 225, 270, 315]
SQRT2 = math.sqrt(2)
EMPTY_WHEEL_DATA = {'fl': 0, 'fr': 0, 'bl': 0, 'br': 0}
EMPTY_RADAR_DATA = {v: 0 for v in RADAR_ANGLES}


def angleDiference(a1, a2):
    diff = a1 - a2
    if diff >= 180:
        return diff - 360
    elif diff <= -180:
        return diff + 360
    return diff


def normaiseAngle(a):
    a = a % 360
    if a < 0:
        a += 360
    return a


class WheelOdos:
    WHEEL_DIAMETER = 68  # mm
    ODO_PER_CIRCLE = 4096  # parts of the circle
    MM_PER_CIRCLE = 2 * math.pi * WHEEL_DIAMETER
    MM_PER_ODO = MM_PER_CIRCLE / ODO_PER_CIRCLE

    def __init__(self, odos_time, odos, status, old_odos: 'WheelOdos' = None):
        self.time = odos_time
        self.odos = odos
        self.status = status
        if old_odos is not None:
            self.last_odos = old_odos.odos
            self.last_time = old_odos.time
        else:
            self.last_odos = self.odos
            self.last_time = self.time

        self.odos_deltas = None
        self.updateDeltas()

    def updateDeltas(self):
        self.odos_deltas = {k: self.deltaOdo(self.odos[k], self.last_odos[k]) for k in self.odos}

    def deltaTime(self):
        return self.time - self.last_time

    def averageSpeed(self):
        if self.time == self.last_time:
            return 0

        total = 0
        for wheel in self.odos:
            total += abs(self.normaliseOdo(self.odos[wheel] - self.last_odos[wheel]))

        total = total / 4

        return self.MM_PER_ODO * total / (self.time - self.last_time)

    @staticmethod
    def deltaOdo(old, new):
        return normaiseAngle(new - old)

    @staticmethod
    def normaliseOdo(d):
        if d > 32768:
            d -= 32768
        elif d < -32768:
            d += 32768

        return d

    @staticmethod
    def deltaOdoInmm(old, new):
        d = new - old
        if d > 32768:
            d -= 32768
        elif d < -32768:
            d += 32768

        return d * WHEEL_CIRCUMFERENCE / 4096


class WheelOrientations:
    def __init__(self, orientations_time, orientations, status, old_orientations: 'WheelOrientations' = None):
        self.time = orientations_time
        self.orientations = orientations
        self.status = status
        if old_orientations is not None:
            self.last_orientations = old_orientations.orientations
            self.last_time = old_orientations.time
        else:
            self.last_orientations = self.orientations
            self.last_time = self.time

        self.orientations_deltas = None
        self.updateDeltas()

    def updateDeltas(self):
        self.orientations_deltas = {k: angleDiference(self.orientations[k], self.last_orientations[k]) for k in self.orientations}

    def deltaTime(self):
        return self.time - self.last_time


class Radar:
    def __init__(self, radar_time, radar_values, radar_status, previous_radar: 'Radar' = None):
        self.time = radar_time
        self.radar = {k: v for k, v in radar_values.items()}
        self.status = radar_status
        if previous_radar is not None:
            self.last_radar = {k: v for k, v in previous_radar.radar.items()}
            self.last_time = previous_radar.time
        else:
            self.last_radar = {k: v for k, v in self.radar.items()}
            self.last_time = self.time

        self.radar_deltas = None
        self.updateDeltas()

    def updateDeltas(self):
        self.radar_deltas = {k: self.radar[k] - self.last_radar[k] for k in self.radar}

    def deltaTime(self):
        return self.time - self.last_time

    def speedInDirection(self, direction):
        if self.time == self.last_time:
            return 0

        res = []
        opposite_direction = direction + 180
        if opposite_direction >=360:
            opposite_direction -= 360

        for a in self.radar:
            next_a = a + 45
            if a < direction < next_a:
                res.append((a, self.last_radar[a] - self.radar[a]))
                if a == 315:
                    next_a = 0
                res.append((next_a, self.last_radar[next_a] - self.radar[next_a]))
            if a < opposite_direction < next_a:
                res.append((a, self.radar[a] - self.last_radar[a]))
                if a == 315:
                    next_a = 0
                res.append((next_a, self.radar[next_a] - self.last_radar[next_a]))

        total = 0
        for p in res:
            angle = p[0] - direction
            angle = angle * math.pi / 180
            delta = math.cos(angle)
            total += delta

        total = total / len(res)
        return total / (self.time - self.last_time)


class Heading:
    def __init__(self, heading_time, heading_value, heading_status, old_heading: 'Heading' = None):
        self.time = heading_time
        self.heading = heading_value
        self.status = heading_status
        self.last_heading = heading_value if old_heading is None else old_heading.heading
        self.last_time = heading_time if old_heading is None else old_heading.time
        self.heading_delta = None
        self.updateDelta()

    def updateDelta(self):
        self.heading_delta = angleDiference(self.heading, self.last_heading)

    def deltaTime(self):
        return self.time - self.last_time


class RoverCommand:
    def __init__(self, speed, angle, distance=32000):
        self.time = None
        self.speed = speed
        self.angle = angle
        self.distance = distance if -32000 < distance < 32000 else 32000
        self.display = ""

    def send(self, publish_method):
        self.time = time.time()
        if self.distance == 0:
            publish_method("move/rotate", str(int(self.speed)))
        elif self.speed == 0:
            publish_method("move/drive", str(int(self.angle)) + " 0")  # Orient wheels only
        elif self.distance >= 32000 or self.distance <= -32000:
            publish_method("move/drive", str(int(self.angle)) + " " + str(int(self.speed)))
        else:
            publish_method("move/steer", str(int(self.distance)) + " " + str(int(self.speed)) + " " + str(int(self.angle)))
        self.updateDisplayValue()

    def updateDisplayValue(self):
        if self.distance == 0:
            self.display = "move/rotate s={:>3d}".format(int(self.speed))
        elif self.speed == 0:
            self.display = "move/drive a={:>3d} 0 0".format(int(self.angle))  # Orient wheels only
        elif self.distance >= 32000 or self.distance <= -32000:
            self.display = "move/drive a={:>3d} s={:>3d}".format(int(self.angle), int(self.speed))
        else:
            self.display = "move/steer d={:>3d} s={:>3d} a={:>3d}".format(int(self.distance), int(self.speed), int(self.angle))


class RoverState:
    FRONT = 1
    BACK = -1
    LEFT = -1
    RIGHT = 1
    NONE = 0
    CORNER = 1
    CHICANE = 2

    def __init__(self, rover, wheel_odos, wheel_orientations, radar, heading, last_command):
        self.rover = rover
        self.wheel_odos = wheel_odos
        self.wheel_orientations = wheel_orientations
        self.radar = radar
        self.heading = heading
        self.last_command = last_command

        self.left_wall_angle = 0
        self.left_wall_distance = 0
        self.left_front_distance_of_wall = 0
        self.left_wall_type = self.FRONT

        self.right_wall_angle = 0
        self.right_wall_distance = 0
        self.right_front_distance_of_wall = 0
        self.right_wall_type = self.FRONT

        self.front_wall_angle = 0
        self.front_wall_distance = 0
        self.front_wall_type = self.LEFT

        self.back_wall_angle = 0
        self.back_wall_distance = 0
        self.back_wall_type = self.LEFT

        self.left_front_gap_type = self.NONE
        self.right_front_gap_type = self.NONE
        self.selection = "-"

    def calculateAngleAndFrontDistance(self, df, dm, db):
        dfsqrt2 = df / SQRT2
        dbsqrt2 = db / SQRT2

        if df < db:
            # angle = math.atan2(dfsqrt2, dfsqrt2 - dm) * 180 / math.pi - 90
            angle = math.atan2(dfsqrt2, dfsqrt2 - dm) - math.pi / 2
            calc_type = self.FRONT

            d = 0

        else:
            # angle = 90 - math.atan2(dbsqrt2, dbsqrt2 - dm) * 180 / math.pi
            angle = math.pi / 2 - math.atan2(dbsqrt2, dbsqrt2 - dm)
            calc_type = self.BACK

            xf, yf = dfsqrt2, dfsqrt2
            xm, ym = dm, 0
            xb, yb = dbsqrt2, -dbsqrt2

            d = ((ym - yb) * xf + (xb - xm) * yf + (xm * yb - xb * ym)) / math.sqrt((xb - xm) * (xb - xm) + (yb - ym) * (yb - ym))

        return angle, int(d), calc_type

    @staticmethod
    def calculateRealDistance(side_distance, side_angle):
        if side_distance < 1:
            return 0
        return math.sin(math.pi / 2 - side_angle) * side_distance

    def calculate(self):
        if self.hasRadar():
            self.left_wall_angle, self.left_front_distance_of_wall, self.left_wall_type = self.calculateAngleAndFrontDistance(self.radar.radar[315], self.radar.radar[270], self.radar.radar[225])
            self.left_wall_distance = self.calculateRealDistance(self.radar.radar[270], self.left_wall_angle)
            self.right_wall_angle, self.right_front_distance_of_wall, self.right_wall_type = self.calculateAngleAndFrontDistance(self.radar.radar[45], self.radar.radar[90], self.radar.radar[135])
            self.right_wall_distance = self.calculateRealDistance(self.radar.radar[90], self.right_wall_angle)

    def log(self, logger, selection):
        selection_str = selection + "                                  "
        selection_str = selection_str[0:17]

        if selection_str.endswith("\n"):
            selection_str = selection_str[0:len(selection_str) - 1] + " "

        self.selection = selection_str

        data = [
            # 0
            float(self.wheel_odos.time),
            int(self.wheel_odos.odos['fl']), int(self.wheel_odos.odos['fr']),
            int(self.wheel_odos.odos['bl']), int(self.wheel_odos.odos['br']),
            int(self.wheel_odos.status['fl']), int(self.wheel_odos.status['fr']),
            int(self.wheel_odos.status['bl']), int(self.wheel_odos.status['br']),

            # 9
            float(self.wheel_odos.last_time),
            int(self.wheel_odos.last_odos['fl']), int(self.wheel_odos.last_odos['fr']),
            int(self.wheel_odos.last_odos['bl']), int(self.wheel_odos.last_odos['br']),

            # 14
            float(self.wheel_orientations.time),
            int(self.wheel_orientations.orientations['fl']), int(self.wheel_orientations.orientations['fr']),
            int(self.wheel_orientations.orientations['bl']), int(self.wheel_orientations.orientations['br']),
            int(self.wheel_orientations.status['fl']), int(self.wheel_orientations.status['fr']),
            int(self.wheel_orientations.status['bl']), int(self.wheel_orientations.status['br']),

            # 23
            float(self.wheel_orientations.last_time),
            int(self.wheel_orientations.last_orientations['fl']), int(self.wheel_orientations.last_orientations['fr']),
            int(self.wheel_orientations.last_orientations['bl']), int(self.wheel_orientations.last_orientations['br']),

            # 28
            float(self.radar.time),
            int(self.radar.radar[0]), int(self.radar.radar[45]), int(self.radar.radar[90]), int(self.radar.radar[135]),
            int(self.radar.radar[180]), int(self.radar.radar[225]), int(self.radar.radar[270]), int(self.radar.radar[315]),

            int(self.radar.status[0]), int(self.radar.status[45]), int(self.radar.status[90]), int(self.radar.status[135]),
            int(self.radar.status[180]), int(self.radar.status[225]), int(self.radar.status[270]), int(self.radar.status[315]),

            # 45
            float(self.radar.last_time),
            int(self.radar.last_radar[0]), int(self.radar.last_radar[45]), int(self.radar.last_radar[90]), int(self.radar.last_radar[135]),
            int(self.radar.last_radar[180]), int(self.radar.last_radar[225]), int(self.radar.last_radar[270]), int(self.radar.last_radar[315]),

            # 54
            float(self.heading.time), int(self.heading.heading), int(self.heading.status), int(self.heading.last_time), int(self.heading.last_heading),

            # 59
            float(self.last_command.time if self.last_command.time is not None else 0), int(self.last_command.speed), int(self.last_command.angle), int(self.last_command.distance),

            # 62
            bytes(selection_str, 'ascii')
        ]

        # print("Logging " + str(data))
        logger.log(time.time(), *data)

    def recreate(self, received_data):
        data = [e for e in received_data]

        log_timestamp = data[0]
        del data[0]

        odos_time = data[0]
        odos = {'fl': data[1], 'fr': data[2], 'bl': data[3], 'br': data[4]}
        odos_status = {'fl': data[5], 'fr': data[6], 'bl': data[7], 'br': data[8]}
        last_odos_time = data[9]
        last_odos = {'fl': data[10], 'fr': data[11], 'bl': data[12], 'br': data[13]}
        prev_odos = WheelOdos(last_odos_time, last_odos, EMPTY_WHEEL_DATA)
        self.wheel_odos = WheelOdos(odos_time, odos, odos_status, prev_odos)

        ori_time = data[14]
        oris = {'fl': data[15], 'fr': data[16], 'bl': data[17], 'br': data[18]}
        oris_status = {'fl': data[19], 'fr': data[20], 'bl': data[21], 'br': data[22]}
        last_oris_time = data[23]
        last_oris = {'fl': data[24], 'fr': data[25], 'bl': data[26], 'br': data[27]}
        prev_oris = WheelOrientations(last_oris_time, last_oris, EMPTY_WHEEL_DATA)
        self.wheel_orientations = WheelOrientations(ori_time, oris, oris_status, prev_oris)

        radar_time = data[28]
        radar = {0: data[29], 45: data[30], 90: data[31], 135: data[32],
                 180: data[33], 225: data[34], 270: data[35], 315: data[36]}
        radar_status = {0: data[37], 45: data[38], 90: data[39], 135: data[40],
                        180: data[41], 225: data[42], 270: data[43], 315: data[44]}
        last_radar_time = data[45]
        last_radar = {0: data[46], 45: data[47], 90: data[48], 135: data[49],
                      180: data[50], 225: data[51], 270: data[52], 315: data[53]}

        prev_radar = Radar(last_radar_time, last_radar, EMPTY_RADAR_DATA)
        self.radar = Radar(radar_time, radar, radar_status, prev_radar)

        heading_time = data[54]
        heading_value = data[55]
        heading_status = data[56]
        last_heading_time = data[57]
        last_heading = data[58]
        prev_heading = Heading(last_heading_time, last_heading, 0)
        self.heading = Heading(heading_time, heading_value, prev_heading)

        cmd_time = data[59]
        cmd_speed = data[60]
        cmd_angle = data[61]
        cmd_dist = data[62]
        self.last_command = RoverCommand(cmd_speed, cmd_angle, cmd_dist)
        if cmd_time != 0:
            self.last_command.time = cmd_time
            self.last_command.updateDisplayValue()

        self.selection = str(data[63])

    @staticmethod
    def defineLogger(logger):
        logger.addDouble('odos_time')
        logger.addWord('odo_fl')
        logger.addWord('odo_fr')
        logger.addWord('odo_bl')
        logger.addWord('odo_br')
        logger.addByte('odo_s_fl')
        logger.addByte('odo_s_fr')
        logger.addByte('odo_s_bl')
        logger.addByte('odo_s_br')  # 20

        logger.addDouble('odos_last_time')
        logger.addWord('last_odo_fl')
        logger.addWord('last_odo_fr')
        logger.addWord('last_odo_bl')
        logger.addWord('last_odo_br')  # 36 bytes (16)

        logger.addDouble('ori_time')
        logger.addWord('ori_fl')
        logger.addWord('ori_fr')
        logger.addWord('ori_bl')
        logger.addWord('ori_br')
        logger.addByte('ori_s_fl')
        logger.addByte('ori_s_fr')
        logger.addByte('ori_s_bl')
        logger.addByte('ori_s_br')  # 56 (20)

        logger.addDouble('last_ori_time')
        logger.addWord('last_ori_fl')
        logger.addWord('last_ori_fr')
        logger.addWord('last_ori_bl')
        logger.addWord('last_ori_br')  # 72 bytes (16)

        logger.addDouble('radar_time')
        logger.addWord('radar_0')
        logger.addWord('radar_45')
        logger.addWord('radar_90')
        logger.addWord('radar_135')
        logger.addWord('radar_180')
        logger.addWord('radar_225')
        logger.addWord('radar_270')
        logger.addWord('radar_315')  # 96 bytes (24)

        logger.addByte('radar_s_0')
        logger.addByte('radar_s_45')
        logger.addByte('radar_s_90')
        logger.addByte('radar_s_135')
        logger.addByte('radar_s_180')
        logger.addByte('radar_s_225')
        logger.addByte('radar_s_270')
        logger.addByte('radar_s_315')  # 104 bytes (8)

        logger.addDouble('last_radar_time')
        logger.addWord('last_radar_0')
        logger.addWord('last_radar_45')
        logger.addWord('last_radar_90')
        logger.addWord('last_radar_135')
        logger.addWord('last_radar_180')
        logger.addWord('last_radar_225')
        logger.addWord('last_radar_270')
        logger.addWord('last_radar_315')  # 128 bytes (24)

        logger.addDouble('heading_time')
        logger.addWord('heading')  #
        logger.addByte('heading_s')  # 139 (11)

        logger.addDouble('last_heading_time')
        logger.addWord('last_heading')  # 149 (10)

        logger.addDouble('cmd_time')
        logger.addWord('cmd_speed', signed=True)
        logger.addWord('cmd_angle', signed=True)
        logger.addWord('cmd_dist', signed=True)  # 163 (14)

        logger.addFixedString('selection', 17)  # 180 (18)

        return logger

    def hasHeading(self):
        return self.heading.time != 0.0

    def hasRadar(self):
        return self.radar.time != 0.0

    def hasWheelOrientation(self):
        return self.wheel_orientations.time != 0.0

    def hasWheelOdos(self):
        return self.wheel_odos.time != 0.0

    def hasCompleteState(self):
        return self.hasWheelOdos() and self.hasWheelOrientation() and self.hasHeading() and self.hasRadar()


class Rover:
    def __init__(self):
        self.wheel_odos = None
        self.wheel_orientations = None
        self.radar = None
        self.heading = None
        self.last_command = None
        self.start_heading_value = None
        self.current_state = None
        self.reset()

    def reset(self):
        self.wheel_odos = WheelOdos(0, EMPTY_WHEEL_DATA, EMPTY_WHEEL_DATA)
        self.wheel_orientations = WheelOrientations(0, EMPTY_WHEEL_DATA, EMPTY_WHEEL_DATA)
        self.radar = Radar(0, EMPTY_RADAR_DATA, EMPTY_RADAR_DATA)
        self.heading = Heading(0, 0, 0)
        self.last_command = RoverCommand(0, 0, 0)
        self.start_heading_value = None

    def handleHeading(self, topic, message, groups):
        heading_data = struct.unpack('>fffBf', message)

        heading_time = heading_data[4]
        heading_time = time.time()
        heading_status = heading_data[3]
        new_heading = normaiseAngle(heading_data[2])

        if self.start_heading_value is None:
            self.start_heading_value = new_heading

        self.heading = Heading(heading_time, normaiseAngle(new_heading - self.start_heading_value), heading_status, self.heading)

    def handleRadar(self, topic, message, groups):
        values = [v.split(":") for v in message.split(" ")]
        radar_values = {}
        radar_status = {}
        radar_time = None
        for (k, v) in values:
            if k == 'timestamp':
                radar_time = float(v)
            elif k == 'status':
                i = 0
                for angle in RADAR_ANGLES:
                    radar_status[angle] = int(v[i:i+2], 16)
                    i += 2
            else:
                radar_values[int(k)] = int(v)

        self.radar = Radar(radar_time, radar_values, radar_status, self.radar)

    def handleOdo(self, topic, message, groups):
        data = message.split(",")

        odo_time = float(data[0])

        odos = {}
        odos_status = {}

        for i in range(4):
            data_index = i * 2
            if data[data_index + 2] == "0":
                odos[WHEEL_NAMES[i]] = int(data[data_index + 1])
            elif self.wheel_odos is not None:
                odos[WHEEL_NAMES[i]] = self.wheel_odos.odos[WHEEL_NAMES[i]]  # TODO handle wrong values!
            else:
                odos[WHEEL_NAMES[i]] = -1  # TODO handle wrong values!
            odos_status[WHEEL_NAMES[i]] = int(data[data_index + 2])

        self.wheel_odos = WheelOdos(odo_time, odos, odos_status, self.wheel_odos)

    def handleWheelOrientation(self, topic, message, group):
        data = message.split(",")

        wheel_orientations_time = float(data[0])

        wheel_orientations = {}
        wheel_status = {}

        for i in range(4):
            data_index = i * 2
            if data[data_index + 2] == "32":
                wheel_orientations[WHEEL_NAMES[i]] = int(data[data_index + 1])
            else:
                wheel_orientations[WHEEL_NAMES[i]] = int(data[data_index + 1])  # -1  # TODO handle wrong values!
            wheel_status[WHEEL_NAMES[i]] = int(data[data_index + 2])

        self.wheel_orientations = WheelOrientations(wheel_orientations_time, wheel_orientations, wheel_status, self.wheel_orientations)

    def hasHeading(self):
        return self.start_heading_value is not None

    def hasRadar(self):
        return self.radar.time != 0.0

    def hasWheelOrientation(self):
        return self.wheel_orientations.time != 0.0

    def hasWheelOdos(self):
        return self.wheel_odos.time != 0.0

    def hasCompleteState(self):
        return self.hasWheelOdos() and self.hasWheelOrientation() and self.hasHeading() and self.hasRadar()

    def nextState(self):
        self.current_state = RoverState(self, self.wheel_odos, self.wheel_orientations, self.radar, self.heading, self.last_command)
        return self.current_state

    def getRoverState(self):
        if self.current_state is None:
            return self.nextState()

        return self.current_state

    def command(self, publish_method, speed, angle, distance=32000):
        cmd = RoverCommand(speed, angle, distance)
        cmd.send(publish_method)
        self.last_command = cmd
