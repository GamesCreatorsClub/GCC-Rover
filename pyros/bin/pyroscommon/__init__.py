import sys
import os
import time
import paho.mqtt.client as mqtt

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
timeout = 10
connected = False;

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



def saveAliases():
    aliasStr = "\n".join(list(map(_aliasLine, list(aliases.items())))) + "\n"
    #    print(aliasStr)
    with open(aliasFile, 'wt') as f:
        f.write(aliasStr)


def expandArgs(args):
    if len(args) == 0:
        return ""

    return " " + " ".join(args)


def processCommonHostSwitches(args):
    global help, timeout, host

    while len(args) > 0 and args[0].startswith("-"):
        if args[0] == "-h":
            help = True
        elif args[0] == "-t":
            del args[0]
            if len(args) == 0:
                print("ERROR: -t option must be followed with a number.")
            try:
                timeout = int(args[0])
                if timeout < 0:
                    print("ERROR: -t option must be followed with a positive number.")
            except:
                print("ERROR: -t option must be followed with a number. '" +  args[0] + "' is not a number.")

        del args[0]

    if len(args) > 0:
        host = args[0]
        del args[0]

    return args


def printOutCommand(command, processLine, header, footer):
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
        countdown = timeout

    client.on_connect = onConnect
    client.on_message = onMessage

    try:
        client.connect(host, 1883, 60)

        commandId = uniqueId + str(time.time())

        countdown = timeout

        while not connected:
            client.loop(1)
            countdown -= 1
            if countdown == 0:
                print("ERROR: reached timeout waiting to connect to " + host)
                sys.exit(1)

        if header is not None:
            print(header)

        client.publish("system/" + commandId, command)

        countdown = timeout

        while connected:
            client.loop(1)
            countdown -= 1
            if countdown == 0:
                print("ERROR: reached timeout waiting for response")
                sys.exit(1)

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

        if topic.endswith("/out"):
            connected = processOut(payload)
        elif topic.endswith("/status"):
            connected = processStatus(payload)

        countdown = timeout

    client.on_connect = onConnect
    client.on_message = onMessage

    try:
        client.connect(host, 1883, 60)

        commandId = uniqueId + str(time.time())

        countdown = timeout

        while not connected:
            client.loop(1)
            countdown -= 1
            if countdown == 0:
                print("ERROR: reached timeout waiting to connect to " + host)
                sys.exit(1)

        countdown = timeout

        connected =  executeCommand(client)

        while connected:
            client.loop(1)
            countdown -= 1
            if countdown == 0:
                print("ERROR: reached timeout waiting for response")
                sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)
