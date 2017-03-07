

class SMBus:
    def __init__(self, busNo):
        raise NotImplemented()

    def write_byte(self, i2cAddress, byte):
        raise NotImplemented()

    def write_byte_data(self, i2cAddress, localAddress, data):
        raise NotImplemented()

    def write_block_data(self, i2cAddress, localAddress, dataArray):
        raise NotImplemented()

    #
    # def write_i2c_block_data(self, i2cAddress, localAddress, count, data):
    #     raise NotImplemented()

    def read_byte(self, i2cAddress):
        raise NotImplemented()

    def read_byte_data(self, i2cAddress, localAddress):
        raise NotImplemented()

    def read_block_data(self, i2cAddress, localAddress):
        raise NotImplemented()

    #
    # def read_i2c_block_data(self, i2cAddress, localAddress, count):
    #     raise NotImplemented()
