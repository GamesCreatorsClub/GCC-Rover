
import pyros

_returncodes = {}


def init(client, filename, agentId=None):
    # print("Connected to Rover " + str(client))
    if agentId is None:
        if filename.endswith(".py"):
            agentId = filename[: len(filename) - 3]
        else:
            agentId = filename
            agentId = agentId.replace("/", "-")

    file = open(filename)
    fileContent = file.read()
    file.close()

    _returncodes[agentId] = None

    pyros.subscribe("exec/" + str(agentId) + "/out", process)
    pyros.subscribe("exec/" + str(agentId) + "/status", process)
    pyros.publish("exec/" + str(agentId), "stop")
    pyros.publish("exec/" + str(agentId) + "/process", fileContent)


def process(topic, message, groups):

    if topic.startswith("exec/"):
        if topic.endswith("/out"):
            if len(message) > 0:
                agentId = topic[5: len(topic) - 4]
                if message.endswith("\n"):
                    print(agentId + ": " + message, end="")
                else:
                    print(agentId + ": " + message)
            return True
        elif topic.endswith("/status"):
            agentId = topic[5: len(topic) - 7]
            if message == "stored":
                pyros.publish("exec/" + str(agentId), "restart")
            elif message.startswith("exit"):
                if len(message) > 5:
                    _returncodes[agentId] = message[5:]
                else:
                    _returncodes[agentId] = "-1"

            return True

    return False


def stopAgent(client, processId):
    pyros.publish("exec/" + processId, "stop")


def returncode(agentId):
    return _returncodes[agentId]
