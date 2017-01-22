import sys
import os
import time
import paho.mqtt.client as mqtt

DEFAULT_TIMEOUT = 10

args = sys.argv
binDir = os.path.dirname(args[0])

if binDir == "" or binDir == ".":
    installDir = ".."
else:
    installDir = os.path.dirname(binDir)

if installDir == "":
    aliasFile = ".aliases"
else:
    aliasFile = installDir + "/.aliases"

# print("binDir=" + binDir)
# print("installDir=" + installDir)

uniqueId = str(os.uname().nodename) + "." + str(os.getpid())

del args[0]

defaultAlias = None
aliases = {}

help = False
timeout = None
connected = False;
host = None
port = 1883
client = None

def _aliasLine(t):
    return t[0] + "=" + t[1]


def loadAliases():
    global defaultAlias

    if os.path.exists(aliasFile):
        with open(aliasFile, 'rt') as f:
            lines = f.read().splitlines()
            for line in lines:
                if not line.strip().startswith("#"):
                    split = line.split('=')
                    if len(split) == 2:
                        aliases[split[0].strip()] = split[1].strip()
    if "default" in aliases:
        defaultAlias = aliases["default"]

loadAliases()

def saveAliases():
    aliasStr = "\n".join(list(map(_aliasLine, list(aliases.items())))) + "\n"
    #    print(aliasStr)
    with open(aliasFile, 'wt') as f:
        f.write(aliasStr)


def expandArgs(args):
    if len(args) == 0:
        return ""

    return " " + " ".join(args)


def getTimeout():
    if timeout is None:
        return DEFAULT_TIMEOUT

    return timeout


def _processTOption(i):
    global timeout

    del args[i]
    if len(args) == 0:
        print("ERROR: -t option must be followed with a number.")
    try:
        timeout = int(args[i])
        if timeout < 0:
            print("ERROR: -t option must be followed with a positive number.")
            sys.exit(1)
    except:
        print("ERROR: -t option must be followed with a number. '" + args[i] + "' is not a number.")
        sys.exit(1)


def processCommonHostSwitches(args):
    global help, host, port

    while len(args) > 0 and args[0].startswith("-"):
        if args[0] == "-h":
            help = True
        elif args[0] == "-t":
            _processTOption(0)
        del args[0]

    if len(args) > 0:
        hostSplit = args[0].split(":")
        if len(hostSplit) == 1:
            host = hostSplit[0]
        elif len(hostSplit) == 2:
            host = hostSplit[0]
            try:
                port = int(hostSplit[1])
            except:
                print("ERROR: Port must be a number. '" +  hostSplit[1] + "' is not a number.")
                sys.exit(1)
        else:
            print("ERROR: Host and port should in host:port format not '" + args[0] + "'.")
            sys.exit(1)
        del args[0]

        if host in aliases:
            host = aliases[host]

    i = 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] == "-t":
            _processTOption(i)
            del args[i]
        i = +1

    return args


def printOutCommand(executeCommand, processLine, header, footer):
    global connected
    client = mqtt.Client("PyROS." + uniqueId)

    connected = False;

    def onConnect(client, data, rc):
        global connected

        if rc == 0:
            client.subscribe("system/+/out", 0)
        else:
            print("ERROR: Connection returned error result: " + str(rc))
            sys.exit(rc)

        connected = True

    def onMessage(client, data, msg):
        global connected, countdown

        payload = str(msg.payload, 'utf-8')
        topic = msg.topic

        if topic.endswith("/out"):
            if payload != "":
                processLine(payload)
            else:
                connected = False
        countdown = getTimeout()

    client.on_connect = onConnect
    client.on_message = onMessage

    try:
        try:
            client.connect(host, port, 60)
        except Exception as e:
            print("ERROR: failed to connect to " + str(host) + ":" + str(port) + "; " + str(e))
            sys.exit(1)


        commandId = uniqueId + str(time.time())

        countdown = getTimeout()

        while not connected:
            client.loop(1)
            countdown -= 1
            if countdown == 0:
                print("ERROR: reached timeout waiting to connect to " + host)
                sys.exit(1)
            elif countdown < 0:
                countdown = 0

        if header is not None:
            print(header)

        connected = executeCommand(client, commandId)

        countdown = getTimeout()

        while connected:
            client.loop(1)
            countdown -= 1
            if countdown == 0:
                print("ERROR: reached timeout waiting for response")
                sys.exit(1)
            elif countdown < 0:
                countdown = 0

        if footer is not None:
            print(footer)
    except KeyboardInterrupt:
        sys.exit(1)


def processCommand(processId, executeCommand, processOut, processStatus):
    global connected, countdown
    client = mqtt.Client("PyROS." + uniqueId)

    connected = False;

    def onConnect(client, data, rc):
        global connected

        if rc == 0:
            client.subscribe("exec/" + processId + "/out", 0)
            client.subscribe("exec/" + processId + "/status", 0)
        else:
            print("ERROR: Connection returned error result: " + str(rc))
            sys.exit(rc)

        connected = True

    def onMessage(client, data, msg):
        global connected, countdown

        payload = str(msg.payload, 'utf-8')
        topic = msg.topic

        if topic.startswith("exec/"):
            if topic.endswith("/out"):
                processId = topic[5:len(topic)-4]
                connected = processOut(payload, processId)
            elif topic.endswith("/status"):
                processId = topic[5:len(topic)-7]
                connected = processStatus(payload, processId)

        countdown = getTimeout()

    client.on_connect = onConnect
    client.on_message = onMessage

    try:
        client.connect(host, port, 60)

        countdown = getTimeout()

        while not connected:
            for i in range(0, 50):
                time.sleep(0.015)
                client.loop(0.005)
            countdown -= 1
            if countdown == 0:
                print("ERROR: reached timeout waiting to connect to " + host)
                sys.exit(1)
            elif countdown < 0:
                countdown = 0

        connected =  executeCommand(client)

        countdown = getTimeout()

        while connected:
            for i in range(0, 50):
                time.sleep(0.015)
                client.loop(0.005)
            countdown -= 1
            if countdown == 0:
                print("ERROR: reached timeout waiting for response")
                sys.exit(1)
            elif countdown < 0:
                countdown = 0
    except KeyboardInterrupt:
        sys.exit(1)
