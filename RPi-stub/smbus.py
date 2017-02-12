

class SMBus:
    def __init__(self, busNo):
        raise NotImplemented()

    def write_byte(self, i2cAddress, byte):
        raise NotImplemented()

    def write_byte_data(self, i2cAddress, localAddress, data):
        raise NotImplemented()

    def read_byte(self, i2cAddress):
        raise NotImplemented()
