#################################################################################
# Copyright (c) 2018 Creative Sphere Limited.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License v2.0
# which accompanies this distribution, and is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
#  Contributors:
#    Creative Sphere - initial API and implementation
#
#################################################################################

import RPi.GPIO as GPIO
import spidev
import time


_CONFIG = 0x00
_EN_AA = 0x01
_EN_RXADDR = 0x02
_SETUP_AW = 0x03
_SETUP_RETR = 0x04
_RF_CH = 0x05
_RF_SETUP = 0x06
_STATUS = 0x07
_OBSERVE_TX = 0x08
_CD = 0x09
_RX_ADDR_P0 = 0x0a
_RX_ADDR_P1 = 0x0b
_RX_ADDR_P2 = 0x0c
_RX_ADDR_P3 = 0x0d
_RX_ADDR_P4 = 0x0e
_RX_ADDR_P5 = 0x0f
_TX_ADDR = 0x10
_RX_PW_P0 = 0x11
_RX_PW_P1 = 0x12
_RX_PW_P2 = 0x13
_RX_PW_P3 = 0x14
_RX_PW_P4 = 0x15
_RX_PW_P5 = 0x16
_FIFO__STATUS = 0x17
_DYNPD = 0x1C
_FEATURE = 0x1D

_R_RX_PAYLOAD = 0x61
_W_TX_PAYLOAD = 0xa0
_W_TX_PAYLOAD_NO_ACK = 0xB0

_FLUSH_TX = 0xe1
_FLUSH_RX = 0xe2

_RECEIVER = 1
_TRANSMITTER = 0

CE_GPIO = 25
CHANNEL = 1

_packetSize = 0
_spi = None


def delay10us():
    time.sleep(0.00001)


def delay20ms():
    time.sleep(0.02)


def delay2ms():
    time.sleep(0.002)


def delay100ms():
    time.sleep(0.1)


def _clearCE():
    GPIO.output(CE_GPIO, 0)


def _setCE():
    GPIO.output(CE_GPIO, 1)


def _writeCommand(address, v):
    _spi.xfer([0x20 | address, v])
    time.sleep(0.00002)


def setReadPipeAddress(pipeNumber, address):
    d = [0x20 | _RX_ADDR_P0 + pipeNumber, address[0], address[1], address[2], address[3], address[4]]
    _spi.xfer(d)
    time.sleep(0.00002)


def setWritePipeAddress(address):
    d = [0x20 | _TX_ADDR, address[0], address[1], address[2], address[3], address[4]]
    _spi.xfer(d)
    time.sleep(0.00002)


def getWritePipeAddress():
    d = [_RX_ADDR_P0, 0, 0, 0, 0, 0]
    d = _spi.xfer(d)
    delay10us()
    return d


def writeFlushTX():
    _spi.xfer([_FLUSH_TX])


def writeFlushRX():
    _spi.xfer([_FLUSH_RX])


def _clearInterrupts():
    _writeCommand(_STATUS, 0x71)


def _readRegister(address):
    r = _spi.xfer([address, 0])
    time.sleep(0.00002)
    return r[1]


def initNRF(spiBus, spiDevice, packetSize, address, channel):
    global _spi, _packetSize

    _packetSize = packetSize

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(CE_GPIO, GPIO.OUT)

    _spi = spidev.SpiDev()
    _spi.open(spiBus, spiDevice)
    _spi.max_speed_hz = 50000

    _clearCE()

    powerDown()
    _writeCommand(_EN_AA, 0x3f)       # _EN_AA_P0
    _writeCommand(_EN_RXADDR, 0x01)   # ERX_P0
    _writeCommand(_SETUP_AW, 0x03)    # 5 bytes
    _writeCommand(_SETUP_RETR, 0x2f)  # 15 retransmits | Wait 750 + 86us
    _writeCommand(_RF_CH, channel)    # channel 1 (MiLight 9, 40, 71 ?)
    _writeCommand(_RF_SETUP, 0x07)    # LNA_Gain | 0 dBm | 1 Mbps
    setReadPipeAddress(0, address)  # Pipe 0 read address
    setWritePipeAddress(address)    # Write address

    verifyAddress = getWritePipeAddress()
    for i in range(1, len(verifyAddress) - 1):
        if verifyAddress[i] != address[i - 1]:
            print("Failed to read stored write address at index " + str(i) + ", expected " + str(address) + " but got " + str(verifyAddress))
            sys.exit(-1)

    _writeCommand(_RX_PW_P0, packetSize)       # 8 bytes
    _clearInterrupts()
    writeFlushTX()
    _writeCommand(_CONFIG, 0x1e)            # PWR_UP | CRC0 | EN_CRC | MASK_MAX_RT | PTX
    delay20ms()


def powerUp():
    config = _readRegister(_CONFIG)
    config |= 2
    _writeCommand(_CONFIG, config)
    time.sleep(0.002)


def powerDown():
    _clearCE()
    time.sleep(0.02)
    config = _readRegister(_CONFIG)
    config &= 0xfd
    _writeCommand(_CONFIG, config)
    time.sleep(0.02)


def swithToTX():
    _clearCE()
    _writeCommand(_CONFIG, 0x1e)      # PWR_UP | CRC0 | EN_CRC | MASK_MAX_RT | PTX
    time.sleep(0.0002)


def swithToRX():
    _clearCE()
    _writeCommand(_CONFIG, 0x1f)      # PWR_UP | CRC0 | EN_CRC | MASK_MAX_RT | PRX
    time.sleep(0.0002)
    # time.sleep(0.02)


def reset():
    _writeCommand(_STATUS, 0x70)
    time.sleep(0.00002)


def sendString(data):
    sendString(_stringToBytes(data))


def sendData(buf):
    writeFlushTX()
    _clearInterrupts()

    d = [_W_TX_PAYLOAD]
    for v in buf:
        d.append(v)
    _spi.xfer(d)

    delay10us()
    _setCE()
    delay10us()  # 0.1ms = 20us
    _clearCE()

    now = time.time()
    while time.time() - now < 1:
        s = _readRegister(_STATUS) & 0x20
        if s > 0:
            return True

    return False


def _stringToBytes(s):
    b = bytearray()
    b.extend(map(ord, s))
    return b


def padToSize(buf, size):
    while len(buf) < size:
        buf.append(0)

    return buf


def startListening():
    # delay10us()
    # time.sleep(0.00002)
    _writeCommand(_CONFIG, _readRegister(_CONFIG) | 3)
    _writeCommand(_STATUS, 0x70)                         # RX_DR | TX_DS | MAX_RT
    writeFlushRX()
    writeFlushTX()
    _setCE()
    # delay20ms()
    time.sleep(0.0002)


def stopListening():
    _clearCE()


def receiveData(n):

    buf = [_R_RX_PAYLOAD]
    for _ in range(0, n):
        buf.append(0)
    buf = _spi.xfer(buf)
    del buf[0]

    return buf


def poolData(timeout):
    now = time.time()
    while time.time() - now < timeout:
        s = _readRegister(_STATUS) & 0x40
        if s > 0:
            _writeCommand(_STATUS, 0x40)
            return True

    return False


def sendAndReceive(data, timeout):

    def returnError(data):
        res = []
        for d in data:
            res.append(0)

        return res

    padToSize(data, _packetSize)

    swithToTX()

    done = False
    now = time.time()
    while not done and time.time() - now < timeout:
        done = sendData(data)
        if not done:
            print("NOT SENT!")
            delay20ms()
            writeFlushTX()
            delay20ms()

    if not done:
        return returnError(data)

    done = False
    while not done:
        swithToRX()
        startListening()
        if poolData(timeout):
            # stopListening()
            res = receiveData(_packetSize)
            stopListening()
            return res
        else:
            return returnError(data)

    return data


def close():
    _spi.close()


def _readOneByte(aa):
    r = _spi.xfer([aa, 0])
    print(_hexa(aa) + ":  " + _binary(r[1]))


def _read1Address(aa):
    r = _spi.xfer([aa, 0])
    print(_hexa(aa) + ":  " + _hexa(r[1]))


def _read5Address(aa):
    r = _spi.xfer([aa, 0, 0, 0, 0, 0])
    print(_hexa(aa) + ":  " + _hexa(r[1]) + " " + _hexa(r[2]) + " " + _hexa(r[3]) + " " + _hexa(r[4]) + " " + _hexa(r[5]))


def testChannel(c):
    _spi.xfer([0x20 | 0x05, c])
    time.sleep(0.01)
    r = _spi.xfer([0x09, 0])
    res = r[1] & 1
    print("Carrier detect at channel " + str(c) + " " + str(res == 1), end="   ")
    _readOneByte(0x05)
    time.sleep(0.01)


def print_STATUS():
    for a in range(0, 10):
        _readOneByte(a)

    _read5Address(0x0a)
    _read5Address(0x0b)

    for a in range(0x0c, 0x10):
        _read1Address(a)

    _read5Address(0x10)
    _readOneByte(0x11)
    _readOneByte(0x17)
    _readOneByte(0x1C)
    _readOneByte(0x1D)


def _binary(bb):
    r = bin(bb)
    r = r[2:]
    r = "00000000" + r
    r = r[len(r) - 8:]

    return r


def _hexa(aa):
    r = "0" + hex(aa)

    if len(r) > 2:
        r = r[1:]
    return r
