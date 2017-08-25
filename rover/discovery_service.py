#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import os
import socket
import fcntl
import struct
import traceback
import threading
import pyroslib

#
# discovery service
#
# This service is responding to UDP discovery packets.
#

DEBUG = False

INTERFACES_TO_TEST = [ "wlan0", "wlan1", "eth0", "eth1" ]


def getIpAddressFromInterface(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', bytes(ifname[:15], 'utf-8'))
    )[20:24])


def getHostname():
    if os.path.exists("/etc/hostname"):
        with open("/etc/hostname", "rt") as textFile:
            hostname = textFile.read()

        return hostname.split(".")[0]
    else:
        return "UNKNOWN"


def getIpAddress():
    for interface in INTERFACES_TO_TEST:
        try:
            return getIpAddressFromInterface(interface)
        except:
            pass


def handleEcho(topic, payload, groups):
    print("Got echo in " + payload)
    if len(groups) > 0:
        pyroslib.publish("echo/out", groups[0] + ":" + payload)
    else:
        pyroslib.publish("echo/out", "default:" + payload)


if __name__ == "__main__":
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.bind(('', 0xd15c))


        def send(packet):
            # print("Debug: sending packet " + packet)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(bytes(packet, 'utf-8'), ('255.255.255.255', 0xd15c))


        def receive():
            s.settimeout(10)
            print("    Started receive thread...")
            while True:
                try:
                    data, addr = s.recvfrom(1024)
                    p = str(data, 'utf-8')
                    # print("Debug: got reqest " + p)

                    if p.startswith("Q#"):
                        ip = getIpAddress()
                        # print("Debug: ip=" + ip)
                        name = getHostname()
                        # print("Debug: name=" + name)
                        send("A#IP=" + ip + ";NAME=" + name + ";TYPE=ROVER")
                        # print("Debug: got request " + p)
                        # else:
                        #     print("Unknown packet " + p)
                except:
                    pass


        print("Starting discovery service...")

        pyroslib.init("discovery-service")

        thread = threading.Thread(target=receive, args=())
        thread.daemon = True
        thread.start()

        print("Started discovery service.")

        pyroslib.forever(0.5)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
