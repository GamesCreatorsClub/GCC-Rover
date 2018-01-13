import socket
import fcntl
import struct
import threading
import time
import netifaces




# print(ifacenames)

broadcasts = []

ifacenames = netifaces.interfaces()
for ifname in ifacenames:
    addrs = netifaces.ifaddresses(ifname)
    # print(ifname + " => " + str(addrs))

    for d in addrs:
        for dx in addrs[d]:
            if "broadcast" in dx:
                broadcasts.append(dx["broadcast"])


# print("Broadcasts " + str(broadcasts))

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('', 0xd15d))


def receive():
    while True:
        data, addr = s.recvfrom(1024)

        try:
            p = str(data, 'utf-8')

            print("Got " + p)
        except:
            pass


def send(packet):
    for broadcast in broadcasts:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        bs = bytes(packet, 'utf-8')
        s.sendto(bs, (broadcast, 0xd15c))


thread = threading.Thread(target=receive, args=())
thread.daemon = True
thread.start()

time.sleep(1)
send("Q#IP=255.255.255.255;PORT=53597")
time.sleep(5)
