#!/usr/bin/env python3

#
# Copyright 2016-2019 Games Creators Club
#
# MIT License
#

import os
import psutil
import pyroslib
import time
import traceback

#
# power service
#
# This service is trying to calculate total current (or power) consumption
#

DEBUG = False

RPI_AVERAGE_CURRENT = 800  # mA
BATTERY_CAPACITY = 2200
BATTERY_PERCENTAGE_CAPACITY = 1750
BATTERY_WARNING = 1200
BATTERY_CRITICAL = 1600

last_uptime_broadcast = 0
uptime_broadcast_freq = 30

last_status_broadcast = 0
status_broadcast_freq = 5  # every 5 seconds

service_started_time = 0

rpimAh = 0
dmAh = 0
smAh = 0
wtmAh = 0


def handleWheelsStatus(topic, message, groups):
    global dmAh, smAh, wtmAh, rpimAh

    status = {s[0]: s[1] for s in [s.split(":") for s in message.split(" ")]}
    # if 's' in status:
    #     pass
    #
    if 'dmAh' in status:
        dmAh = int(status['dmAh'])

    if 'smAh' in status:
        smAh = int(status['smAh'])

    if 'wtmAh' in status:
        wtmAh = int(status['wtmAh'])


def stopCallback():
    print("Asked to stop!")


def readUptime():
    with open("/proc/uptime", 'r') as fh:
        return float(float(fh.read().split(" ")[0]))


def readCPUTemp():
    res = os.popen('vcgencmd measure_temp').readline()
    return res[5:res.index("'")]


def readCPULoad():
    return psutil.cpu_percent()


def broadcastPowerStatus():
    global rpimAh

    now = time.time()

    rpimAh = (now - service_started_time) * RPI_AVERAGE_CURRENT / 3600
    totalmAh = rpimAh + wtmAh

    if totalmAh < BATTERY_PERCENTAGE_CAPACITY:
        ebp = int((BATTERY_PERCENTAGE_CAPACITY - totalmAh) * 100 / BATTERY_PERCENTAGE_CAPACITY)
    else:
        ebp = 0

    if totalmAh >= BATTERY_WARNING and totalmAh < BATTERY_CRITICAL:
        bs = 'warning'
    elif totalmAh >= BATTERY_CRITICAL:
        bs = 'critical'
    else:
        bs = 'nominal'

    currents = "t:" + str(int(totalmAh)) + " wtmAh:" + str(wtmAh) + " dmAh:" + str(dmAh) + " smAh:" + str(smAh) + " ebp:" + str(ebp) + " bs:" + bs
    pyroslib.publish("power/current", currents)

    cpu_temp = readCPUTemp()
    cpu_load = readCPULoad()
    pyroslib.publish("power/cpu", "temp:" + str(cpu_temp) + " load:" + "{0:.2f}".format(cpu_load))


def broadcastUptimeStatus():
    uptime = readUptime()
    uptime_seconds = uptime % 60
    uptime_minutes = int(uptime / 60)
    uptime_hours = int(uptime_minutes / 60)
    uptime_minutes = uptime_minutes % 60
    uptime = "{:02d}:{:02d}:{:06.3f}".format(uptime_hours, uptime_minutes, uptime_seconds)

    pyroslib.publish("power/uptime", str(uptime))


def main_loop():
    global last_status_broadcast, last_uptime_broadcast

    now = time.time()
    if last_status_broadcast + status_broadcast_freq < now:
        broadcastPowerStatus()
        last_status_broadcast = now

    if last_uptime_broadcast + uptime_broadcast_freq < now:
        broadcastUptimeStatus()
        last_uptime_broadcast = now


if __name__ == "__main__":
    try:
        print("Starting power service...")
        already_up_for_seconds = readUptime()
        service_started_time = time.time() - already_up_for_seconds
        print("  set started time " + str(already_up_for_seconds) + " seconds ago.")

        pyroslib.subscribe("wheel/feedback/status", handleWheelsStatus)

        pyroslib.init("power-service", unique=True, onStop=stopCallback)

        print("Started power service.")

        pyroslib.forever(0.5, main_loop)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
