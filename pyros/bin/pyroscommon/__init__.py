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

hasHelpSwitch = False
timeout = None
connected = False
host = None
port = 1883
client = None


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
    def _aliasLine(t):
        return t[0] + "=" + t[1]

    aliasStr = "\n".join(list(map(_aliasLine, list(aliases.items())))) + "\n"
    #    print(aliasStr)
    with open(aliasFile, 'wt') as f:
        f.write(aliasStr)


def expandArgs(arguments):
    if len(arguments) == 0:
        return ""

    return " " + " ".join(arguments)


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


def processCommonHostSwitches(arguments):
    global hasHelpSwitch, host, port

    while len(arguments) > 0 and arguments[0].startswith("-"):
        if arguments[0] == "-h":
            hasHelpSwitch = True
        elif arguments[0] == "-t":
            _processTOption(0)
        del arguments[0]

    if len(arguments) > 0:
        hostSplit = arguments[0].split(":")
        if len(hostSplit) == 1:
            host = hostSplit[0]
        elif len(hostSplit) == 2:
            host = hostSplit[0]
            try:
                port = int(hostSplit[1])
            except:
                print("ERROR: Port must be a number. '" + hostSplit[1] + "' is not a number.")
                sys.exit(1)
        else:
            print("ERROR: Host and port should in host:port format not '" + arguments[0] + "'.")
            sys.exit(1)
        del arguments[0]

        if host in aliases:
            host = aliases[host]
            if ":" in host:
                splithost = host.split(":")
                host = splithost[0]
                port = int(splithost[1])

    i = 0
    while i < len(arguments) and arguments[i].startswith("-"):
        if arguments[i] == "-t":
            _processTOption(i)
            del arguments[i]
        else:
            i += 1

    return arguments


def printOutCommand(executeCommand, processLine, header, footer):
    global connected, client, countdown

    client = mqtt.Client("PyROS." + uniqueId)

    connected = False
    afterCommand = False

    def onConnect(c, data, flags, rc):
        global connected

        if rc == 0:
            c.subscribe("system/+/out", 0)
        else:
            print("ERROR: Connection returned error result: " + str(rc))
            sys.exit(rc)

        connected = True

    def onMessage(c, data, msg):
        global connected, countdown

        payload = str(msg.payload, 'utf-8')
        topic = msg.topic

        if afterCommand:
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
                print("ERROR: reached timeout waiting to connect to " + str(host))
                sys.exit(1)
            elif countdown < 0:
                countdown = 0

        if header is not None:
            print(header)

        connected = executeCommand(client, commandId)
        afterCommand = True

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

        if footer is not None:
            print(footer)
    except KeyboardInterrupt:
        sys.exit(1)


def processCommand(processId, executeCommand, processOut, processStatus):
    global connected, countdown, client

    client = mqtt.Client("PyROS." + uniqueId)

    connected = False
    afterCommand = False

    def onConnect(c, data, flags, rc):
        global connected

        if rc == 0:
            c.subscribe("exec/" + processId + "/out", 0)
            c.subscribe("exec/" + processId + "/status", 0)
        else:
            print("ERROR: Connection returned error result: " + str(rc))
            sys.exit(rc)

        connected = True

    def onMessage(c, data, msg):
        global connected, countdown

        payload = str(msg.payload, 'utf-8')
        topic = msg.topic

        if afterCommand:
            if topic.startswith("exec/"):
                if topic.endswith("/out"):
                    pid = topic[5:len(topic)-4]
                    connected = processOut(payload, pid)
                elif topic.endswith("/status"):
                    pid = topic[5:len(topic)-7]
                    connected = processStatus(payload, pid)

            countdown = getTimeout()
        else:
            print("Before command: " + payload)

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
                print("ERROR: reached timeout waiting to connect to " + str(host))
                sys.exit(1)
            elif countdown < 0:
                countdown = 0

        connected = executeCommand(client)
        afterCommand = True

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


def processGlobalCommand(topic, executeCommand, processOut, processStatus):
    global connected, countdown, client

    client = mqtt.Client("PyROS." + uniqueId)

    connected = False
    afterCommand = False

    def onConnect(c, data, flags, rc):
        global connected

        if rc == 0:
            c.subscribe(topic + "/out", 0)
        else:
            print("ERROR: Connection returned error result: " + str(rc))
            sys.exit(rc)

        connected = True

    def onMessage(c, data, msg):
        global connected, countdown

        payload = str(msg.payload, 'utf-8')
        topic = msg.topic

        if afterCommand:
            if topic.startswith("exec/"):
                if topic.endswith("/out"):
                    pid = topic[5:len(topic)-4]
                    connected = processOut(payload, pid)
                elif topic.endswith("/status"):
                    pid = topic[5:len(topic)-7]
                    connected = processStatus(payload, pid)
            else:
                connected = processOut(payload, -1)

            countdown = getTimeout()
        else:
            print("Before command: " + payload)

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
                print("ERROR: reached timeout waiting to connect to " + str(host))
                sys.exit(1)
            elif countdown < 0:
                countdown = 0

        connected = executeCommand(client)
        afterCommand = True

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
