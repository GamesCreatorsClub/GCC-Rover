
import os
import socket

_SPI_CPHA = 0x01
_SPI_CPOL = 0x02

# _SPI_MODE_0 = 0
# _SPI_MODE_1 = SPI_CPHA
# _SPI_MODE_2 = SPI_CPOL
# _SPI_MODE_3 = SPI_CPOL | SPI_CPHA
# _SPI_MODES = [_SPI_MODE_0, _SPI_MODE_1, _SPI_MODE_2, _SPI_MODE_3]

_SPI_CS_HIGH = 0x04
_SPI_LSB_FIRST = 0x08
_SPI_3WIRE = 0x10
_SPI_LOOP = 0x20
_SPI_NO_CS = 0x40
_SPI_READY = 0x80


class SpiDev:

    _socket = None

    _bits_per_word = 0
    # cshigh = False
    # loop = None
    # lsbfirst = False
    _max_speed_hz = 0
    _mode = 0
    # threewire = False

    def __init__(self):

        port = 8789
        ip = os.environ["RASPBERRY_IP"]
        if "RASPBERRY_PORT" in os.environ:
            port = int(os.environ["RASPBERRY_PORT"])

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((ip, port))

    def __del__(self):
        if self._socket is not None:
            try:
                self._socket.close()
            except Exception as e:
                pass

    def open(self, bus, device):
        b = bytearray()
        b.append(ord("o"))
        b.append(bus)
        b.append(device)
        self._socket.send(b)

    def xfer(self, data, speed_hz=0, delay_usec=0, bits_per_word=8):
        b = bytearray()
        b.append(ord("x"))
        b.append(len(data) & 255)
        b.append(len(data) >> 8 & 255)
        for d in data:
            b.append(d)
        self._socket.send(b)

        rec = self._socket.recv(len(data))

        resp = []
        for bb in rec:
            resp.append(bb)

        return resp

    def xfer2(self, data, speed_hz=0, delay_usec=0, bits_per_word=8):
        pass

    def close(self):
        self._mode = 0;
        self._bits_per_word = 0;
        self._max_speed_hz = 0;
        b = bytearray()
        b.append(ord("c"))
        self._socket.send(b)

    def readbytes(self, n):
        pass

    def writebytes(self, data):
        pass

    @property
    def cshigh(self):
        return self._mode & _SPI_CS_HIGH != 0

    @cshigh.setter
    def cshigh(self, cshigh):
        if cshigh:
            self._mode = self._mode | _SPI_CS_HIGH
        else:
            self._mode = self._mode & ~_SPI_CS_HIGH

    @property
    def lsbfirst(self):
        return self._mode & _SPI_LSB_FIRST != 0

    @cshigh.setter
    def lsbfirst(self, lsbfirst):
        if lsbfirst:
            self._mode = self._mode | _SPI_LSB_FIRST
        else:
            self._mode = self._mode & ~_SPI_LSB_FIRST

    @property
    def threewire(self):
        return self._mode & _SPI_3WIRE != 0

    @threewire.setter
    def threewire(self, threewire):
        if threewire:
            self._mode = self._mode | _SPI_3WIRE
        else:
            self._mode = self._mode & ~_SPI_3WIRE

    @property
    def loop(self):
        return self._mode & _SPI_3WIRE != 0

    @loop.setter
    def loop(self, loop):
        if loop:
            self._mode = self._mode | _SPI_LOOP
        else:
            self._mode = self._mode & ~_SPI_LOOP

    @property
    def bits_per_word(self):
        return self._bits_per_word

    @bits_per_word.setter
    def bits_per_word(self, bits_per_word):
        if bits_per_word < 8 or bits_per_word > 16:
            raise ValueError("invalid bits_per_word (8 to 16)")
        self._bits_per_word = bits_per_word

    @property
    def max_speed_hz(self):
        return self.max_speed_hz

    @max_speed_hz.setter
    def bits_per_word(self, max_speed_hz):
        self.max_speed_hz

    @property
    def mode(self):
        return self._mode & (_SPI_CPHA | _SPI_CPOL)

    @mode.setter
    def loop(self, mode):
        self._mode = (self._mode & ~(_SPI_CPHA | _SPI_CPOL)) | mode


if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 8789))
    s.listen(1)


    def startListen():
        import threading

        def session(con):
            while True:
                # print("Waiting to command")
                cmd = ord(con.recv(1))
                if cmd == ord("c"):
                    print("Close")
                elif cmd == ord("o"):
                    bus = ord(con.recv(1))
                    device = ord(con.recv(1))
                    print("Opening " + str(bus) + "." + str(device))
                elif cmd == ord("x"):
                    l = ord(con.recv(1))
                    h = ord(con.recv(1))
                    size = l + h << 8
                    print("Receiving " + str(size) +" bytes")
                    data = con.recv(size)
                    print("Received " + str(data))
                    con.send(data)
                else:
                    print("Unknown command " + str(cmd))

        def listen():
            while True:
                con, addr = s.accept()
                t = threading.Thread(target=session, args=[con])
                t.daemon = True
                t.start()

        thread = threading.Thread(target=listen)
        thread.daemon = True
        thread.start()

    try:
        startListen()

        os.environ["RASPBERRY_IP"] = "127.0.0.1"

        spi = SpiDev()
        print("opening spi")
        spi.open(1, 2)
        print("sending data")
        spi.xfer(b"Hello")
        print("closing")
        spi.close()
    finally:
        s.close()
        s.detach()