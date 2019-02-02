#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import os
import sys
import time
import subprocess
import threading
import traceback

import paho.mqtt.client as mqtt


do_exit = False

startedInDir = os.getcwd()

THREAD_KILL_TIMEOUT = 1.0

AGENTS_CHECK_TIMEOUT = 1.0
AGENT_KILL_TIMEOT = 180

DEBUG_LEVEL = 1

CODE_DIR_NAME = "code"

host = "localhost"
port = 1883
timeout = 60
thisClusterId = None
client = None

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


def processCommonHostSwitches(arguments):
    global timeout, host, port, scriptName, DEBUG_LEVEL

    scriptName = arguments[0]
    del arguments[0]

    while len(arguments) > 0 and arguments[0].startswith("-"):
        if arguments[0] == "-v":
            DEBUG_LEVEL = 1
        elif arguments[0] == "-vv":
            DEBUG_LEVEL = 2
        elif arguments[0] == "-vvv":
            DEBUG_LEVEL = 3
        elif arguments[0] == "-t":
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
        hostStr = arguments[0]
        hostSplit = hostStr.split(":")
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
            important("ERROR: Host and port should in host:port format not '" + hostStr + "'.")
            sys.exit(1)
        del arguments[0]

    return arguments


def processEnv():
    global host, port, thisClusterId

    if 'PYROS_MQTT' in os.environ:
        hostStr = os.environ['PYROS_MQTT']
        hostSplit = hostStr.split(":")
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
            important("ERROR: Host and port should in host:port format not '" + hostStr + "'.")
            sys.exit(1)

    if 'PYROS_CLUSTER_ID' in os.environ:
        thisClusterId = os.environ['PYROS_CLUSTER_ID']


def complexProcessId(processId):
    if thisClusterId is not None:
        return thisClusterId + ":" + processId
    return processId


def processDir(processId):
    return CODE_DIR_NAME + "/" + processId


def processFilename(processId):
    return processDir(processId) + "/" + processId + ".py"


def processInitFilename(processId):
    return processDir(processId) + "/__init__.py"


def processServiceFilename(processId):
    oldServiceFilename = processDir(processId) + "/.service"
    processConfigFilename = processDir(processId) + "/.process"

    # convert from old .service files to .process file
    if os.path.exists(oldServiceFilename):
        os.rename(oldServiceFilename, processConfigFilename)

    return processConfigFilename


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

    serviceFile = processDir(processId) + "/.process"

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
    client.publish("exec/" + complexProcessId(processId) + "/out", line)
    if DEBUG_LEVEL > 2:
        if line.endswith("\n"):
            trace("exec/" + complexProcessId(processId) + "/out > " + line[:len(line) - 1])
        else:
            trace("exec/" + complexProcessId(processId) + "/out > " + line)


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
    client.publish("exec/" + complexProcessId(processId) + "/status", status)
    if DEBUG_LEVEL > 2:
        trace("exec/" + complexProcessId(processId) + "/status > " + status)


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


def isAgent(processId):
    return processId in processes and processes[processId]["type"] == "agent"


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

        process = subprocess.Popen(["python3", "-u", processId + ".py", processId],
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
    elif isAgent(processId):
        return "agent"
    elif "type" in processes[processId]:
        return processes[processId]["type"]
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

    if "type" not in processes[processId]:
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


def storeExtraCode(processId, name, payload):
    makeProcessDir(processId)

    filename = processDir(processId) + "/" + name

    filedir = os.path.split(filename)[0]
    print("  making file dir " + str(filedir))
    os.makedirs(filedir, exist_ok=True)

    print("  storing extra file " + str(filename))

    try:
        with open(filename, "wb") as textFile:
            textFile.write(payload)

        outputStatus(processId, "stored")
    except:
        important("ERROR: Cannot save file " + filename + " (" + os.path.abspath(filename) + "); ")
        outputStatus(processId, "stored error")


def stopProcess(processId):

    def finalProcessKill(processIdToKill):
        time.sleep(0.01)
        # Just in case - we really need that process killed!!!
        cmdAndArgs = ["/usr/bin/pkill -9 -f 'python3 -u " + processIdToKill + ".py " + processIdToKill + "'"]
        res = subprocess.call(cmdAndArgs, shell=True)
        if res != -9 and res != 0:
            info("Tried to kill " + processIdToKill + " but got result " + str(res) + "; command: " + str(cmdAndArgs))

    def waitForProcessStop(processIdStop):
        _now = time.time()
        while time.time() - _now < THREAD_KILL_TIMEOUT and 'stop_response' not in processes[processIdStop]:
            time.sleep(0.05)

        _process = getProcessProcess(processIdStop)
        if 'stop_response' in processes[processIdStop]:
            while time.time() - _now < THREAD_KILL_TIMEOUT and _process.returncode is None:
                time.sleep(0.05)
            if _process.returncode is None:
                _process.kill()
                output(processIdStop, "PyROS: responded with stopping but didn't stop. Killed now " + getProcessTypeName(processIdStop))
            else:
                output(processIdStop, "PyROS: stopped " + getProcessTypeName(processIdStop))
        else:
            _process.kill()
            output(processIdStop, "PyROS: didn't respond so killed " + getProcessTypeName(processIdStop))

        finalProcessKill(processIdStop)

    if processId in processes:
        process = getProcessProcess(processId)
        if process is not None:
            if process.returncode is None:
                client.publish("exec/" + processId + "/system", "stop")
                thread = threading.Thread(target=waitForProcessStop, args=(processId,))
                thread.daemon = True
                thread.start()
            else:
                output(processId, "PyROS INFO: already finished " + getProcessTypeName(processId) + " return code " + str(process.returncode))
                finalProcessKill(processId)
        else:
            output(processId, "PyROS INFO: process " + processId + " is not running.")
            finalProcessKill(processId)
    else:
        output(processId, "PyROS ERROR: process " + processId + " does not exist.")
        finalProcessKill(processId)


def restartProcess(processId):
    if processId in processes:
        stopProcess(processId)
        startProcess(processId)
        if isService(processId):
            output(processId, "PyROS: Restarted service " + processId)
        else:
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
                output(processId, "PyROS ERROR: failed to unmake process " + processId + "; failed deleting .process file.")

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


def makeAgentProcess(processId):
    if processId in processes:
        if processes[processId]["type"] == "agent":
            output(processId, "PyROS: " + processId + " is already agent")

            processes[processId]["lastPing"] = time.time()
        else:
            processes[processId]["type"] = "agent"
            processes[processId]["enabled"] = "True"
            processes[processId]["lastPing"] = time.time()

            properties = {"type": "agent", "enabled": "True"}
            saveServiceFile(processId, properties)
            output(processId, "PyROS: made " + processId + " an agent")
    else:
        output(processId, "PyROS ERROR: process " + processId + " does not exist.")


def pingProcess(processId):
    if processId in processes:
        processes[processId]["lastPing"] = time.time()
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

        lastPing = "-"
        if "lastPing" in processes[processId]:
            lastPing = str(processes[processId]["lastPing"])

        systemOutput(commandId,
                     "{0} {1} {2} {3} {4} {5} {6}".format(
                         complexProcessId(processId),
                         getProcessTypeName(processId),
                         status,
                         returnCode,
                         fileLen,
                         fileDate,
                         lastPing))


def servicesCommand(commandId, arguments):
    for serviceId in processes:
        if isService(serviceId):
            systemOutput(commandId, serviceId)


def stopPyrosCommand(commandId, arguments):
    global do_exit

    def stopAllProcesses(_commandId, excludes):
        global do_exit

        def areAllStopped():
            for _pId in processes:
                if _pId not in excludes and isRunning(_pId):
                    return False
            return True

        for processId in processes:
            if processId not in excludes and isRunning(processId):
                important("    Stopping process " + processId)
                stopProcess(processId)

        important("Stopping PyROS...")
        important("    excluding processes " + ", ".join(excludes))
        _now = time.time()
        while not areAllStopped() and time.time() - _now < THREAD_KILL_TIMEOUT * 2:
            time.sleep(0.02)

        not_stopped = []
        for _processId in processes:
            if _processId not in excludes and isRunning(_processId):
                not_stopped.append(_processId)

        if len(not_stopped) > 0:
            important("    Not all processes stopped; " + ", ".join(not_stopped))

        important("    sending feedback that we will stop (topic system/" + _commandId + ")")

        systemOutput(_commandId, "stopped")

        time.sleep(2)
        do_exit = True

    if commandId == "pyros:" + (thisClusterId if thisClusterId is not None else "master"):
        thread = threading.Thread(target=stopAllProcesses, args=(commandId, arguments))
        thread.daemon = True
        thread.start()


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
    elif "make-agent" == command:
        makeAgentProcess(processId)
    elif "ping" == command:
        pingProcess(processId)
    else:
        output(processId, "PyROS ERROR: Unknown command " + command)


def processSystemCommand(commandId, commandLine):
    arguments = commandLine.split(" ")
    command = arguments[0]
    del arguments[0]

    trace("Processing received system command " + command + ", args=" + str(arguments))
    if command == "ps":
        psComamnd(commandId, arguments)
    elif command == "services":
        servicesCommand(commandId, arguments)
    elif command == "stop":
        stopPyrosCommand(commandId, arguments)
    else:
        systemOutput(commandId, "Command " + commandLine + " is not implemented")

    systemOutputEOF(commandId)


def onConnect(mqttClient, data, flags, rc):
    try:
        if rc == 0:
            mqttClient.subscribe("system/+", 0)
            mqttClient.subscribe("exec/+", 0)
            mqttClient.subscribe("exec/+/process", 0)
            mqttClient.subscribe("exec/+/process/#", 0)
        else:
            important("ERROR: Connection returned error result: " + str(rc))
            sys.exit(rc)
    except Exception as exception:
        important("ERROR: Got exception on connect; " + str(exception))


def onMessage(mqttClient, data, msg):

    def splitProcessId(_processId):
        _split = _processId.split(":")
        if len(_split) == 1:
            return "master", _processId

        return _split[0], _split[1]

    def checkClusterId(_clusterId):
        if thisClusterId is None:
            return _clusterId == 'master'
        else:
            return thisClusterId == _clusterId

    try:
        # payload = str(msg.payload, 'utf-8')
        topic = msg.topic

        if topic.startswith("exec/") and topic.endswith("/process"):
            processId = topic[5:len(topic) - 8]
            clusterId, processId = splitProcessId(processId)
            if checkClusterId(clusterId):
                payload = str(msg.payload, 'utf-8')
                storeCode(processId, payload)
        elif topic.startswith("exec/"):
            split = topic[5:].split("/")
            if len(split) == 1:
                processId = topic[5:]
                clusterId, processId = splitProcessId(processId)
                if checkClusterId(clusterId):
                    if processId in processes:
                        payload = str(msg.payload, 'utf-8')
                        processCommand(processId, payload)
                    else:
                        output(processId, "No such process '" + processId + "'")
            elif len(split) >= 3 and split[1] == "process":
                processId = split[0]
                clusterId, processId = splitProcessId(processId)
                if checkClusterId(clusterId):
                    name = "/".join(split[2:])
                    storeExtraCode(processId, name, msg.payload)
        elif topic.startswith("system/"):
            commandId = topic[7:]
            payload = str(msg.payload, 'utf-8')
            processSystemCommand(commandId, payload)
        else:
            important("ERROR: No such topic " + topic)
    except Exception as exception:
        important("ERROR: Got exception on message; " + str(exception) + "\n" + ''.join(traceback.format_tb(exception.__traceback__)))


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


def testForAgents(currentTime):
    for processId in processes:
        if isAgent(processId) and isRunning(processId):
            if "lastPing" not in processes[processId] or processes[processId]["lastPing"] < currentTime - AGENT_KILL_TIMEOT:
                stopProcess(processId)


def _connect_mqtt():
    _connect_retries = 0
    _connected_successfully = False
    while not _connected_successfully:
        _try_lasted = 0
        _now = time.time()
        try:
            important("    Connecting to " + str(host) + ":" + str(port) + " (timeout " + str(timeout) + ").")
            _now = time.time()
            client.connect(host, port, timeout)
            _connected_successfully = True
        except BaseException as _e:
            _try_lasted = time.time() - _now
            important("    Failed to connect, retrying; error " + str(_e))
            _connect_retries += 1
            if _try_lasted < 1:
                time.sleep(1)


processEnv()
args = processCommonHostSwitches(sys.argv)

important("Starting PyROS...")

clientName = "PyROS"
if thisClusterId is not None:
    clientName += ":" + str(thisClusterId)

client = mqtt.Client(clientName)

client.on_connect = onConnect
client.on_message = onMessage

_connect_mqtt()

important("Started PyROS.")

startupServices()

lastCheckedAgents = time.time()

while not do_exit:
    try:
        for it in range(0, 10):
            time.sleep(0.009)
            client.loop(0.001)
        now = time.time()
        if now - lastCheckedAgents > AGENTS_CHECK_TIMEOUT:
            lastCheckedAgents = now
            testForAgents(now)

    except SystemExit:
        do_exit = True
    except Exception as e:
        important("ERROR: Got exception in main loop; " + str(e))

important("PyROS stopped.")
