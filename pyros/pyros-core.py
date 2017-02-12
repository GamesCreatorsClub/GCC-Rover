#!/usr/bin/python3

import os
import sys
import time
import subprocess
import threading

import paho.mqtt.client as mqtt

startedInDir = os.getcwd()

DEBUG_LEVEL = 0

CODE_DIR_NAME = "code"

host = "localhost"
port = 1883
timeout = 60

scriptName = None

processes = {}


def important(line):
    print(line)


def info(line):
    if DEBUG_LEVEL > 0:
        print(line)


def debug(line):
    if DEBUG_LEVEL > 1:
        print(line)


def trace(line):
    if DEBUG_LEVEL > 2:
        print(line)


important("Starting PyROS...")


client = mqtt.Client("PyROS")

args = sys.argv

i = 0
while i < len(args):
    if args[i] == "-v":
        DEBUG_LEVEL = 1
        del args[i]
    elif args[i] == "-vv":
        DEBUG_LEVEL = 2
        del args[i]
    elif args[i] == "-vvv":
        DEBUG_LEVEL = 3
        del args[i]
    else:
        i += 1


def processCommonHostSwitches(arguments):
    global timeout, host, port, scriptName

    scriptName = arguments[0]
    del arguments[0]

    while len(arguments) > 0 and arguments[0].startswith("-"):
        if arguments[0] == "-t":
            del arguments[0]
            if len(arguments) == 0:
                important("ERROR: -t option must be followed with a number.")
            try:
                timeout = int(arguments[0])
                if timeout < 0:
                    important("ERROR: -t option must be followed with a positive number.")
                    sys.exit(1)
            except:
                important("ERROR: -t option must be followed with a number. '" + arguments[0] + "' is not a number.")
                sys.exit(1)

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
                important("ERROR: Port must be a number. '" + hostSplit[1] + "' is not a number.")
                sys.exit(1)
        else:
            important("ERROR: Host and port should in host:port format not '" + arguments[0] + "'.")
            sys.exit(1)
        del arguments[0]

    return arguments


def processDir(processId):
    return CODE_DIR_NAME + "/" + processId


def processFilename(processId):
    return processDir(processId) + "/" + processId + ".py"


def processInitFilename(processId):
    return processDir(processId) + "/__init__.py"


def processServiceFilename(processId):
    return processDir(processId) + "/.service"


def makeProcessDir(processId):
    if not os.path.exists(CODE_DIR_NAME):
        os.mkdir(CODE_DIR_NAME)

    if not os.path.exists(processDir(processId)):
        os.mkdir(processDir(processId))


def loadServiceFile(processId):
    properties = {}
    serviceFile = processServiceFilename(processId)
    if os.path.exists(serviceFile):
        with open(serviceFile, 'rt') as f:
            lines = f.read().splitlines()
        for line in lines:
            if not line.strip().startswith("#"):
                split = line.split('=')
                if len(split) == 2:
                    properties[split[0].strip()] = split[1].strip()
    return properties


def saveServiceFile(processId, properties):
    def _line(t):
        return t[0] + "=" + t[1]

    serviceFile = processDir(processId) + "/.service"

    lines = "\n".join(list(map(_line, list(properties.items())))) + "\n"
    with open(serviceFile, 'wt') as f:
        f.write(lines)


def isRunning(processId):
    if processId in processes:
        process = getProcessProcess(processId)
        if process is not None:
            returnCode = process.returncode
            if returnCode is None:
                return True

    return False


def _output(processId, line):
    client.publish("exec/" + processId + "/out", line)
    if DEBUG_LEVEL > 2:
        if line.endswith("\n"):
            trace("exec/" + processId + "/out > " + line[:len(line) - 1])
        else:
            trace("exec/" + processId + "/out > " + line)


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
    if DEBUG_LEVEL > 2:
        trace("exec/" + processId + "/status > " + status)


def systemOutput(commandId, line):
    client.publish("system/" + commandId + "/out", line + "\n")
    if DEBUG_LEVEL > 2:
        if line.endswith("\n"):
            trace("system/" + commandId + "/out > " + line[:len(line) - 1])
        else:
            trace("system/" + commandId + "/out > " + line)


def systemOutputEOF(commandId):
    client.publish("system/" + commandId + "/out", "")


def isService(processId):
    return processId in processes and processes[processId]["type"] == "service"


def runProcess(processId):
    time.sleep(0.25)
    processIsService = isService(processId)

    if processIsService:
        info("Starting new service " + processId)
    else:
        info("Starting new process " + processId)

    filename = processFilename(processId)
    try:
        subprocessDir = startedInDir + "/" + os.path.dirname(filename)
        debug("Starting " + filename + " at dir " + subprocessDir)

        new_env = os.environ.copy()
        if "PYTHONPATH" in new_env:
            new_env["PYTHONPATH"] = new_env["PYTHONPATH"] + ":" + ".."
        else:
            new_env["PYTHONPATH"] = ".."

        process = subprocess.Popen(["python3", "-u", processId + ".py"],
                                   env=new_env,
                                   bufsize=0,
                                   stdout=subprocess.PIPE,
                                   shell=False,
                                   universal_newlines=True,
                                   cwd=subprocessDir)
        outputStatus(processId, "PyROS: started process.")
    except Exception as exception:
        important("Start file " + filename + " (" + os.path.abspath(filename) + ") failed; " + str(exception))
        outputStatus(processId, "PyROS: exit.")
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
        if len(line) > 0:
            output(processId, line)

    outputStatus(processId, "PyROS: exit " + str(process.returncode))


def getProcessTypeName(processId):
    if isService(processId):
        if "enabled" in processes[processId] and processes[processId]["enabled"] == "True":
            return "service"
        else:
            return "service(disabled)"
    else:
        return "process"


def getProcessProcess(processId):
    if processId in processes:
        if "process" in processes[processId]:
            return processes[processId]["process"]

    return None


def startProcess(processId):
    if processId in processes:
        thread = threading.Thread(target=runProcess, args=(processId,))
        thread.daemon = True
        thread.start()
    else:
        output(processId, "PyROS ERROR: process " + processId + " does not exist.")


def storeCode(processId, payload):
    if processId in processes:
        processes[processId]["old"] = True

    makeProcessDir(processId)

    if processId not in processes:
        processes[processId] = {}

    processes[processId]["type"] = "process"

    filename = processFilename(processId)
    initFilename = processInitFilename(processId)

    try:
        with open(filename, "wt") as textFile:
            textFile.write(payload)
        with open(initFilename, "wt") as textFile:
            textFile.write("from " + processId + "." + processId + " import *\n")

        outputStatus(processId, "stored")
    except:
        important("ERROR: Cannot save file " + filename + " (" + os.path.abspath(filename) + "); ")
        outputStatus(processId, "stored error")


def stopProcess(processId):
    if processId in processes:
        process = getProcessProcess(processId)
        if process is not None:
            if process.returncode is None:
                process.kill()
                output(processId, "PyROS: killed " + getProcessTypeName(processId))

            time.sleep(0.01)
            # Just in case - we really need that process killed!!!
            subprocess.call(["/usr/bin/pkill", "-9", "python3 -u " + processId + ".py"])
    else:
        output(processId, "PyROS ERROR: process " + processId + " does not exist.")


def restartProcess(processId):
    if processId in processes:
        stopProcess(processId)
        if isService(processId):
            startProcess(processId)
            output(processId, "PyROS: Restarted service " + processId)
        else:
            startProcess(processId)
            output(processId, "PyROS: Restarted process " + processId)
    else:
        output(processId, "PyROS ERROR: process " + processId + " does not exist.")


def removeProcess(processId):
    if processId in processes:
        stopProcess(processId)

        if os.path.exists(processDir(processId)):
            pDir = processDir(processId)
        else:
            output(processId, "PyROS ERROR: cannot find process files")
            return

        files = os.listdir(pDir)
        for file in files:
            os.remove(pDir + "/" + file)
            if os.path.exists(pDir + "/" + file):
                output(processId, "PyROS ERROR: cannot remove file " + pDir + "/" + file)

        os.removedirs(pDir)
        if os.path.exists(pDir):
            output(processId, "PyROS ERROR: cannot remove dir " + pDir)

        del processes[processId]

        output(processId, "PyROS: removed " + getProcessTypeName(processId))
    else:
        output(processId, "PyROS ERROR: process " + processId + " does not exist.")


def readLog(processId):
    if processId in processes:
        logs = processes[processId]["logs"]
        if logs is None:
            logs = []

        for log in logs:
            _output(processId, log)


def makeServiceProcess(processId):
    if processId in processes:
        if processes[processId]["type"] == "service":
            output(processId, "PyROS: " + processId + " is already service")
        else:
            processes[processId]["type"] = "service"
            processes[processId]["enabled"] = "True"

            properties = {"type": "service", "enabled": "True"}
            saveServiceFile(processId, properties)
            output(processId, "PyROS: made " + processId + " service")
    else:
        output(processId, "PyROS ERROR: process " + processId + " does not exist.")


def unmakeServiceProcess(processId):
    if processId in processes:
        if os.path.exists(processServiceFilename(processId)):
            if not os.remove(processServiceFilename(processId)):
                output(processId, "PyROS ERROR: failed to unmake process " + processId + "; failed deleting .service file.")

        processes[processId]["type"] = "process"
        del processes[processId]["enabled"]

    else:
        output(processId, "PyROS ERROR: process " + processId + " does not exist.")


def enableServiceProcess(processId):
    if processId in processes:
        if processes[processId]["type"] != "service":
            makeServiceProcess(processId)
        else:
            properties = loadServiceFile(processId)
            properties["enabled"] = "True"
            saveServiceFile(processId, properties)

            processes[processId]["enabled"] = "True"

        output(processId, "PyROS: enabled " + processId + " service")
    else:
        output(processId, "PyROS ERROR: process " + processId + " does not exist.")


def disableServiceProcess(processId):
    if processId in processes:
        if processes[processId]["type"] == "service":
            properties = loadServiceFile(processId)
            properties["enabled"] = "False"
            saveServiceFile(processId, properties)

            processes[processId]["enabled"] = "False"

            output(processId, "PyROS: enabled " + processId + " service")
        else:
            output(processId, "PyROS: " + processId + " not a service")

    else:
        output(processId, "PyROS ERROR: process " + processId + " does not exist.")


def psComamnd(commandId, arguments):
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

        filename = processFilename(processId)

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


def servicesCommand(commandId, arguments):
    for serviceId in processes:
        if isService(serviceId):
            systemOutput(commandId, serviceId)


def processCommand(processId, command):
    trace("Processing received comamnd " + command)
    if "stop" == command:
        stopProcess(processId)
    elif "start" == command:
        startProcess(processId)
    elif "restart" == command:
        restartProcess(processId)
    elif "remove" == command:
        removeProcess(processId)
    elif "logs" == command:
        readLog(processId)
    elif "make-service" == command:
        makeServiceProcess(processId)
    elif "unmake-service" == command:
        unmakeServiceProcess(processId)
    elif "disable-service" == command:
        disableServiceProcess(processId)
    elif "enable-service" == command:
        enableServiceProcess(processId)
    else:
        output(processId, "PyROS ERROR: Unknown command " + command)


def processSystemCommand(commandId, commandLine):
    arguments = commandLine.split(" ")
    command = arguments[0]
    del arguments[0]

    trace("Processing received system comamnd " + command + ", args=" + str(arguments))
    if command == "ps":
        psComamnd(commandId, arguments)
    elif command == "services":
        servicesCommand(commandId, arguments)
    else:
        systemOutput(commandId, "Command " + commandLine + " is not implemented")

    systemOutputEOF(commandId)


def onConnect(mqttClient, data, rc):
    try:
        if rc == 0:
            mqttClient.subscribe("system/+", 0)
            mqttClient.subscribe("exec/+", 0)
            mqttClient.subscribe("exec/+/process", 0)
        else:
            important("ERROR: Connection returned error result: " + str(rc))
            sys.exit(rc)
    except Exception as exception:
        important("ERROR: Got exception on connect; " + str(exception))


def onMessage(mqttClient, data, msg):
    try:
        payload = str(msg.payload, 'utf-8')
        topic = msg.topic

        if topic.startswith("exec/") and topic.endswith("/process"):
            processId = topic[5:len(topic) - 8]
            storeCode(processId, payload)
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
            important("ERROR: No such topic " + topic)
    except Exception as exception:
        important("ERROR: Got exception on message; " + str(exception))


def startupServices():
    if not os.path.exists(CODE_DIR_NAME):
        os.mkdir(CODE_DIR_NAME)
    programsDirs = os.listdir(CODE_DIR_NAME)
    for programDir in programsDirs:
        if os.path.isdir(processDir(programDir)):
            if os.path.exists(processFilename(programDir)):
                properties = loadServiceFile(programDir)
                if "type" not in properties:
                    properties["type"] = "process"

                processes[programDir] = {"type": properties["type"]}
                if isService(programDir):
                    if "enabled" in properties and properties["enabled"] == "True":
                        processes[programDir]["enabled"] = "True"
                    else:
                        processes[programDir]["enabled"] = "False"

                    if processes[programDir]["enabled"] == "True":
                        startProcess(programDir)


client.on_connect = onConnect
client.on_message = onMessage

args = processCommonHostSwitches(sys.argv)

important("    Connecting to " + str(host) + ":" + str(port) + " (timeout " + str(timeout) + ").")
client.connect(host, port, timeout)


important("Started PyROS.")

startupServices()


while True:
    try:
        for it in range(0, 10):
            time.sleep(0.0015)
            client.loop(0.0005)
    except Exception as e:
        important("ERROR: Got exception in main loop; " + str(e))
