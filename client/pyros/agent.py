
returncodes = {}

def init(client, filename, id = None):
    # print("Connected to Rover " + str(client))
    if id == None:
        if filename.endswith(".py"):
            id = filename[ : len(filename) - 3]
        else:
            id = filename
        id = id.replace("/", "-")

    file = open(filename)
    fileContent = file.read()
    file.close()

    returncodes[id] = None

    client.subscribe("exec/" + str(id) + "/out", 0)
    client.subscribe("exec/" + str(id) + "/status", 0)
    client.publish("exec/" + str(id), "stop")
    client.publish("exec/" + str(id) + "/process", fileContent)
    client.publish("exec/" + str(id), "restart")


def process(client, msg):
    global returncode

    payload = str(msg.payload, 'utf-8')

    if msg.topic.startswith("exec/"):
        if msg.topic.endswith("/out"):
            if len(payload) > 0:
                id = msg.topic[5 : len(msg.topic) - 4]
                if payload.endswith("\n"):
                    print(id + ": " + payload, end="")
                else:
                    print(id + ": " + payload)
            return True
        elif msg.topic.endswith("/status"):
            id = msg.topic[5: len(msg.topic) - 7]
            if payload == "stored":
                client.publish("exec/" + str(id), "start")
            elif payload.startswith("exit"):
                if len(payload) > 5:
                    returncodes[id] = payload[5:]
                else:
                    returncodes[id] = "-1"

            return True

    return False


def stopAgent(id):
    pass

def returncode(id):
    return returncodes[id]
