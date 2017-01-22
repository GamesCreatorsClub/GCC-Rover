#!/usr/bin/python3

import os
import sys
import time
import subprocess
import threading

import paho.mqtt.client as mqtt

dir = os.getcwd()

DEBUG = True
host = "localhost"
port = 1883
timeout = 60

scriptname = None

processes = {}

print("Starting PyROS...")


client = mqtt.Client("PyROS")

def processCommonHostSwitches(args):
    global help, timeout, host, port

    scriptname = args[0]
    del args[0]

    while len(args) > 0 and args[0].startswith("-"):
        if args[0] == "-t":
            del args[0]
            if len(args) == 0:
                print("ERROR: -t option must be followed with a number.")
            try:
                timeout = int(args[0])
                if timeout < 0:
                    print("ERROR: -t option must be followed with a positive number.")
                    sys.exit(1)
            except:
                print("ERROR: -t option must be followed with a number. '" +  args[0] + "' is not a number.")
                sys.exit(1)
        # elif args[0] == "-h":
        #     help = True
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

    return args



def makeProcessDir(id, isService):
    if isService:
        if not os.path.exists("services"):
            os.mkdir("services")
        if not os.path.exists("services/" + id):
            os.mkdir("services/" + id)
    else:
        if not os.path.exists("agents"):
            os.mkdir("agents")
        if not os.path.exists("agents/" + id):
            os.mkdir("agents/" + id)

def processFilename(processId):
    if isService(processId):
        return "services/" + processId + "/" + processId + ".py"
    elif isAgent(processId):
        return "agents/" + processId + "/" + processId + ".py"
    else:
        return None

def _output(processId, line):
    client.publish("exec/" + processId + "/out", line)
    if DEBUG:
        if line.endswith("\n"):
            print("exec/" + processId + "/out > " + line, end="")
        else:
            print("exec/" + processId + "/out > " + line)

def output(processId, line):
    if "logs" not in processes[processId]:
        logs = []
        processes[processId]["logs"] = logs
    else:
        logs = processes[processId]["logs"]

    if len(logs) > 1000:
        del logs[0]

    logs.append(line)
    _output(processId, line)


def outputStatus(processId, status):
    client.publish("exec/" + processId + "/status", status)
    if DEBUG:
        print("exec/" + processId + "/status > " + status)


def systemOutput(commandId, line):
    client.publish("system/" + commandId + "/out", line + "\n")
    if DEBUG:
        if line.endswith("\n"):
            print("system/" + commandId + "/out > " + line, end="")
        else:
            print("system/" + commandId + "/out > " + line)


def systemOutputEOF(commandId):
    client.publish("system/" + commandId + "/out", "")


def isService(processId):
    return processId in processes and processes[processId]["type"] == "service"


def isAgent(processId):
    return processId in processes and processes[processId]["type"] == "agent"


def runProcess(processId):
    processIsService = isService(processId)
    processIsAgent = isAgent(processId)

    if processIsService:
        print("Starting new service " + processId)
    elif processIsAgent:
        print("Starting new agent " + processId)
    else:
        print("Unknown process id " + processId + ", not staring!")

    try:
        filename = processFilename(processId)
        subprocessDir = dir + "/" + os.path.dirname(filename)
        if DEBUG:
            print("Starting " + filename + " at dir " + subprocessDir)

        process = subprocess.Popen(["python3", "-u", processId + ".py"],
                                   bufsize=0,
                                   stdout=subprocess.PIPE,
                                   shell=False,
                                   universal_newlines=True,
                                   cwd=subprocessDir)
        outputStatus(processId, "started")
    except Exception as e:
        print("Start file " + filename + " (" + os.path.abspath(filename) + ") failed; " + str(e))
        outputStatus(processId, "exit")
        return

    processes[processId]["process"] = process
    if "old" in processes[processId]:
        del processes[processId]["old"]

    textStream = process.stdout
    process.poll()
    while process.returncode is None:
        line = textStream.readline()
        output(processId, line)
        process.poll()


    for line in textStream.readlines():
        if len(len) > 0:
            output(processId, line)

    outputStatus(processId, "exit " + str(process.returncode))


def startProcess(processId):
    thread = threading.Thread(target=runProcess, args=(processId,))
    thread.daemon = True
    thread.start()


def getProcessTypeName(processId):
    if isService(processId):
        return "service"
    elif isAgent(processId):
        return "agent"
    else:
        return "unknown-process"

def getProcessProcess(processId):
    if processId in processes:
        if "process" in processes[processId]:
            return processes[processId]["process"]

    return None


def storeCode(processId, payload, isService):
    if processId in processes:
        processes[processId]["old"] = True

    makeProcessDir(processId, isService)

    if isService:
        type = "service"
    else:
        type = "agent"

    if processId not in processes:
        processes[processId] = {}

    processes[processId]["type"] = type

    filename = processFilename(processId)

    try:
        textFile = open(filename, "wt")
        textFile.write(payload)
        textFile.close()

        outputStatus(processId, "stored")
    except:
        print("Cannot save file " + filename + " (" + os.path.abspath(filename) + ")")
        outputStatus(processId, "stored error")



def stopProcess(processId):
    process = getProcessProcess(processId)
    if process is not None:
        if process.returncode is None:
            process.kill()
            output(processId, "PyROS: killed " + getProcessTypeName(processId))

        time.sleep(0.01)
        # Just in case - we really need that process killed!!!
        subprocess.call(["/usr/bin/pkill", "-9", "python3 -u " + processId + ".py"])


def restartProcess(processId):
    stopProcess(processId)
    if isAgent(processId):
        startProcess(processId)
        output(processId, "PyROS: Restarted agent " + processId)
    elif isService(processId):
        startProcess(processId)
        output(processId, "PyROS: Restarted service " + processId)
    else:
        output(processId, "PyROS ERROR: Restart process command is not implemented")


def removeProcess(processId):
    stopProcess(processId)

    if os.path.exists("services/" + processId):
        dir = "services/" + processId
    elif os.path.exists("agents/" + processId):
        dir = "agents/" + processId
    else:
        output(processId, "PyROS ERROR: cannot find process files")
        return

    files = os.listdir(dir)
    for file in files:
        if not os.remove(file):
            output(processId, "PyROS ERROR: cannot remove file " +  file)

    if not os.remove(dir):
        output(processId, "PyROS ERROR: cannot remove dir " + file)

    del processes[processId]

    output(processId, "PyROS: removed " + getProcessTypeName(processId))


def readLog(processId):
    if processId in processes:
        logs = processes[processId]["logs"]
        if logs is None:
            logs = []

        for log in logs:
            _output(processId, log)

def psComamnd(commandId, args):
    for processId in processes:
        process = getProcessProcess(processId)
        if process is not None:
            returnCode = process.returncode
            if returnCode is None:
                status = "running"
                returnCode = "-"
                if "old" in processes[processId] and processes[processId]["old"]:
                    status = "running-old"
            else:
                status = "stopped"
                returnCode = str(returnCode)

        else:
            status = "new"
            returnCode = ""

        if isAgent(processId):
            filename = "agents/" + processId + "/" + processId + ".py"
        elif isService(processId):
            filename = "services/" + processId + "/" + processId + ".py"
        else:
            filename = None

        fileLen = "-"
        fileDate = "-"

        if filename is not None and os.path.exists(filename):
            fileStat = os.stat(filename)
            fileLen = str(fileStat.st_size)
            fileDate = str(fileStat.st_mtime)

        systemOutput(commandId,
                     "{0} {1} {2} {3} {4} {5}".format(
                         processId,
                         getProcessTypeName(processId),
                         status,
                         returnCode,
                         fileLen,
                         fileDate))


def servicesCommand(commandId, args):
    for serviceId in processes:
        if isService(serviceId):
            systemOutput(commandId, serviceId)


def agentsCommand(commandId, args):
    for agentId in processes:
        if isAgent(agentId):
            systemOutput(commandId, agentId)


def processCommand(processId, command):
    if "stop" == command:
        stopProcess(processId)
    elif "start" == command:
        startProcess(processId)
    elif "restart" == command:
        restartProcess(processId)
    elif "remove" == command:
        removeProcess(processId)
    elif "logs":
        readLog(processId)
    else:
        output(processId, "PyROS ERROR: Unknown command " + command)


def processSystemCommand(commandId, commandLine):
    args = commandLine.split(" ")
    command = args[0]
    del args[0]
    if command == "ps":
        psComamnd(commandId, args)
    elif command == "services":
        servicesCommand(commandId, args)
    elif command == "agents":
        agentsCommand(commandId, args)
    else:
        systemOutput(commandId, "Command " + commandLine + " is not implemented")

    systemOutputEOF(commandId)


def onConnect(client, data, rc):
    try:
        if rc == 0:
            client.subscribe("system/+", 0)
            client.subscribe("exec/+", 0)
            client.subscribe("exec/+/agent", 0)
            client.subscribe("exec/+/service", 0)
        else:
            print("ERROR: Connection returned error result: " + str(rc))
            sys.exit(rc)
    except Exception as e:
        print("ERROR: Got exception on connect; " + str(e))


def onMessage(client, data, msg):
    try:
        payload = str(msg.payload, 'utf-8')
        topic = msg.topic

        if topic.startswith("exec/") and topic.endswith("/agent"):
            processId = topic[5:len(topic) - 6]
            storeCode(processId, payload, False)
        elif topic.startswith("exec/") and topic.endswith("/service"):
            processId = topic[5:len(topic) - 8]
            storeCode(processId, payload, True)
        elif topic.startswith("exec/"):
            processId = topic[5:]
            if processId in processes:
                processCommand(processId, payload)
            else:
                output(processId, "No such process '" + processId + "'")
        elif topic.startswith("system/"):
            commandId = topic[7:]
            processSystemCommand(commandId, payload)
        else:
            print("ERROR: No such topic " + topic)
    except Exception as e:
        print("ERROR: Got exception on message; " + str(e))


def startupServices():
    if not os.path.exists("services"):
        os.mkdir("services")
    if not os.path.exists("agents"):
        os.mkdir("agents")
    serviceDirs = os.listdir("services")
    for serviceDir in serviceDirs:
        if os.path.isdir("services/" + serviceDir):
            processes[serviceDir] = { "type" : "service" }
            startProcess(serviceDir)


client.on_connect = onConnect
client.on_message = onMessage

args = processCommonHostSwitches(sys.argv)

print("    Connecting to " + str(host) + ":" + str(port) + " (timeout " + str(timeout) + ").")
client.connect(host, port, timeout)


print("Started PyROS.")

startupServices()


while True:
    try:
        for i in range(0, 10):
            time.sleep(0.0015)
            client.loop(0.0005)
    except Exception as e:
        print("ERROR: Got exception in main loop; " + str(e))
