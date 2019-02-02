import sys
import os
import time
import paho.mqtt.client as mqtt
import socket
import netifaces

DEFAULT_TIMEOUT = 10

debug = False

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

uniqueId = str(socket.gethostname()) + "." + str(os.getpid())

del args[0]

defaultAlias = None
aliases = {}

hasHelpSwitch = False
timeout = None
DISCOVERY_TIMEOUT = None
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


DISCOVERY_TIMEOUT = 5  # Default timeout 5 seconds
discoverySockets = []
discoveryIPs = []


def setupListening():
    global listeningSocket

    listeningSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listeningSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listeningSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    listeningSocket.setblocking(0)
    listeningSocket.settimeout(DISCOVERY_TIMEOUT)

    listeningSocket.bind(('', 0))
    # sockets.append(listeningSocket)
    # ips.append('255.255.255.255')

    if debug:
        print("  Discovered network adapters:")

    ifaceNames = netifaces.interfaces()

    for ifaceName in ifaceNames:
        iface = netifaces.ifaddresses(ifaceName)
        if netifaces.AF_INET in iface:
            addrs = iface[netifaces.AF_INET]

            for addr in addrs:
                if 'broadcast' in addr or ('addr' in addr and addr['addr'] == '127.0.0.1'):
                    if 'broadcast' in addr:
                        ip = addr['broadcast']
                    else:
                        ip = addr['addr']
                        i = ip.rfind('.')
                        ip = ip[:i] + ".255"

                    sck = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sck.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sck.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sck.setblocking(0)
                    sck.settimeout(DISCOVERY_TIMEOUT)

                    # sck.bind((ip, 0))
                    discoverySockets.append(sck)
                    discoveryIPs.append(ip)
                    if debug:
                        print("    " + str(ip))


def sendDiscoveryPacket(packet):
    for i in range(0, len(discoverySockets)):
        s = discoverySockets[i]
        sendIp = discoveryIPs[i]
        ipSplit = sendIp.split(".")
        ipSplit[3] = "255"
        sendIp = ".".join(ipSplit)
        updated_packet = packet + "IP=" + discoveryIPs[i] + ";PORT=" + str(listeningSocket.getsockname()[1])
        s.sendto(bytes(updated_packet, 'utf-8'), (sendIp, 0xd15c))
        if debug:
            print("  send discovery packet to " + str(sendIp) + ":0xd15c, packet=" + str(updated_packet))
        # print("Sent packet " + updated_packet + " to  " + sendIp)


def receiveDiscoveryPackets(processResponseCallback):
    startTime = time.time()
    while time.time() - startTime < DISCOVERY_TIMEOUT:
        try:
            data, addr = listeningSocket.recvfrom(1024)
            p = str(data, 'utf-8')
            if p.startswith("A#"):
                processResponseCallback(p[2:])
            # elif p.startswith("Q#"):
            #     print("Received self query:" + p)
        except:
            pass


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
        # else:
        #     print("Before command: " + payload)

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
            if topic.endswith("#"):
                c.subscribe(topic, 0)
            elif topic.endswith("!"):
                c.subscribe(topic[0:len(topic) - 2], 0)
            else:
                c.subscribe(topic + "/out", 0)
        else:
            print("ERROR: Connection returned error result: " + str(rc))
            sys.exit(rc)

        connected = True

    def onMessage(c, data, msg):
        global connected, countdown

        payload = str(msg.payload, 'utf-8')
        currentTopic = msg.topic

        if afterCommand:
            if currentTopic.startswith("exec/"):
                if currentTopic.endswith("/out"):
                    pid = currentTopic[5:len(currentTopic)-4]
                    connected = processOut(payload, pid)
                elif currentTopic.endswith("/status"):
                    pid = currentTopic[5:len(currentTopic)-7]
                    connected = processStatus(payload, pid)
            else:
                connected = processOut(payload, currentTopic)

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
