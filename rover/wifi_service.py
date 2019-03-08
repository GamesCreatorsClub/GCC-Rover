#!/usr/bin/env python3

#
# Copyright 2016-2018 Games Creators Club
#
# MIT License
#

import traceback
import pyroslib

#
# wifi service
#
# This service is showing known wifi access points and allows setting new
#

DEBUG = False


def parse():
    networks = []
    with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'r') as file:
        networkStarted = False
        name = None
        for line in file.readlines():
            if "network={" in line:
                networkStarted = True
            elif "}" in line:
                networkStarted = False
            elif "ssid=\"" in line:
                i = line.index("ssid=\"")
                name = line[i + 6:]
                i = name.index("\"")
                if i > 0:
                    name = name[0:i]
                networks.append(name)

    return networks


def readWifi():
    networks = parse()
    pyroslib.publish("wifi/out", "Networks:\n" + str("\n".join(networks)) + "\n:end\n")


def writeWifi(sidPass):
    sid = sidPass.split(":")
    if len(sid) > 1:
        pwd = sid[1]
        sid = sid[0]

        networks = parse()

        if sid in networks:
            pyroslib.publish("wifi/out", "error:\n" + sid + " aleady defined. Delete it first\n:end\n")

        else:
            with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'r') as file:
                lines = file.readlines()

            lines.append("\n")
            lines.append("network={\n")
            lines.append("    ssid=\"" + sid + "\"\n")
            lines.append("    psk=\"" + pwd + "\"\n")
            lines.append("}\n")

            with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w') as file:
                file.writelines(lines)

            pyroslib.publish("wifi/out", "Added:\n" + sid + "\n:end\n")
    else:
        pyroslib.publish("wifi/out", "error:\nWrong command write - got \"" + sidPass + "\"\n:end\n")


def deleteWifi(sid):
    deleted = False
    result = []
    with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'r') as file:
        name = None
        network = None
        for line in file.readlines():
            if "network={" in line:
                network = []
                network.append(line)
            elif not network is None:
                network.append(line)
                if "ssid=\"" in line:
                    i = line.index("ssid=\"")
                    name = line[i + 6:]
                    i = name.index("\"")
                    if i > 0:
                        name = name[0:i]
                elif "}" in line:
                    if name != sid:
                        for networkLine in network:
                            result.append(networkLine)
                    else:
                        deleted = True
                    network = []
            else:
                result.append(line)

    with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w') as file:
        file.writelines(result)

    if deleted:
        pyroslib.publish("wifi/out", "Deleted:\n" + sid + "\n:end\n")
    else:
        pyroslib.publish("wifi/out", "error:\nDid not delete \"" + sid + "\"\n:end\n")


def handleWifi(topic, payload, groups):
    print("Got wifi command " + payload)
    if "read" == payload:
        readWifi()
    elif payload.startswith("write "):
        writeWifi(payload[6:].strip())
    elif payload.startswith("delete "):
        deleteWifi(payload[7:].strip())

    # pyroslib.publish("wifi/out", "payload was :" + payload)


if __name__ == "__main__":
    try:
        print("Starting wifi service...")

        pyroslib.subscribe("wifi", handleWifi)
        pyroslib.init("wifi-service")

        print("Started wifi service.")

        pyroslib.forever(1, priority=pyroslib.PRIORITY_LOW)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
