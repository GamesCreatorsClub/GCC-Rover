import socket
import fcntl
import struct
import threading
import time

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('', 0xd15c))

interfacesToTest = [ "eth0", "eth1", "wlan0", "wlan1" ]

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', bytes(ifname[:15], 'utf-8'))
    )[20:24])


def receive():
    # s.setblocking(0)
    while True:
        data, addr = s.recvfrom(1024)

        try:
            p = str(data, 'utf-8')

            if p.startswith("Q#"):
                send("A#IP=" + ipAddress)
                print("Debug: got request " + p)
            # else:
            #     print("Unknown packet " + p)
        except:
            pass


def send(n):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.sendto(bytes('this is testing ' + str(n), 'utf-8'), ('255.255.255.255', 0xd15c))


thread = threading.Thread(target=receive, args=())
thread.daemon = True
thread.start()

# get_ip_address('eth0')
get_ip_address('lo0')
send(1)
time.sleep(1)
send(3)
time.sleep(1)
time.sleep(1)
