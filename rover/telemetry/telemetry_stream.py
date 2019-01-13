#
# Copyright 2019 Games Creators Club
#
# MIT License
#

import struct

STREAM_ID_BYTE = 0
STREAM_ID_WORD = 1
STREAM_SIZE_BYTE = 0
STREAM_SIZE_WORD = 2
STREAM_SIZE_LONG = 4

TYPE_BYTE = 'b'
TYPE_WORD = 'w'
TYPE_INT = 'i'
TYPE_LONG = 'l'
TYPE_FLOAT = 'f'
TYPE_DOUBLE = 'd'
TYPE_STRING = 's'
TYPE_BYTES = 'a'


class TelemetryStreamField:
    def __init__(self, name, field_type, size):
        self.name = name
        self.field_type = field_type
        self.field_size = size

    def size(self, value):
        return self.field_size

    def _store(self, buffer, ptr, value):
        return ptr + self.field_size

    def packFormat(self):
        return None

    def toJSON(self):
        return "\"type\" : \"" + self.field_type + "\""

    def __eq__(self, other):
        if isinstance(other, TelemetryStreamField):
            return self.name == other.name and self.field_type == other.field_type
        return False


class TelemetryStreamByteField(TelemetryStreamField):
    def __init__(self, name, signed=False):
        super(TelemetryStreamByteField, self).__init__(name, TYPE_BYTE, 1)
        self.signed = signed

    def _store(self, buffer, ptr, value):
        if self.signed:
            buffer[ptr] = struct.pack('b', value)
        else:
            buffer[ptr] = struct.pack('B', value)
        return ptr + self.field_size

    def packFormat(self):
        return 'b' if self.signed else 'B'

    def toJSON(self):
        return super(TelemetryStreamByteField, self).toJSON() + ", \"signed\" : " + str(self.signed).lower()

    def __eq__(self, other):
        if isinstance(other, TelemetryStreamByteField):
            return super(TelemetryStreamByteField, self).__eq__(other) and self.signed == other.signed
        return False


class TelemetryStreamWordField(TelemetryStreamField):
    def __init__(self, name, signed=False):
        super(TelemetryStreamWordField, self).__init__(name, TYPE_WORD, 2)
        self.signed = signed

    def _store(self, buffer, ptr, value):
        if self.signed:
            buffer[ptr:ptr+2] = struct.pack('h', value)
        else:
            buffer[ptr:ptr+2] = struct.pack('H', value)
        return ptr + self.field_size

    def packFormat(self):
        return 'h' if self.signed else 'H'

    def toJSON(self):
        return super(TelemetryStreamWordField, self).toJSON() + ", \"signed\" : " + str(self.signed).lower()

    def __eq__(self, other):
        if isinstance(other, TelemetryStreamWordField):
            return super(TelemetryStreamWordField, self).__eq__(other) and self.signed == other.signed
        return False


class TelemetryStreamIntField(TelemetryStreamField):
    def __init__(self, name, signed=False):
        super(TelemetryStreamIntField, self).__init__(name, TYPE_INT, 4)
        self.signed = signed

    def _store(self, buffer, ptr, value):
        if self.signed:
            buffer[ptr:ptr+4] = struct.pack('i', value)
        else:
            buffer[ptr:ptr+4] = struct.pack('I', value)
        return ptr + self.field_size

    def packFormat(self):
        return 'i' if self.signed else 'I'

    def toJSON(self):
        return super(TelemetryStreamIntField, self).toJSON() + ", \"signed\" : " + str(self.signed).lower()

    def __eq__(self, other):
        if isinstance(other, TelemetryStreamIntField):
            return super(TelemetryStreamIntField, self).__eq__(other) and self.signed == other.signed
        return False


class TelemetryStreamLongField(TelemetryStreamField):
    def __init__(self, name, signed=False):
        super(TelemetryStreamLongField, self).__init__(name, TYPE_LONG, 8)
        self.signed = signed

    def _store(self, buffer, ptr, value):
        if self.signed:
            buffer[ptr:ptr+8] = struct.pack('q', value)
        else:
            buffer[ptr:ptr+8] = struct.pack('Q', value)
        return ptr + self.field_size

    def packFormat(self):
        return 'q' if self.signed else 'Q'

    def toJSON(self):
        return super(TelemetryStreamLongField, self).toJSON() + ", \"signed\" : " + str(self.signed).lower()

    def __eq__(self, other):
        if isinstance(other, TelemetryStreamLongField):
            return super(TelemetryStreamLongField, self).__eq__(other) and self.signed == other.signed
        return False


class TelemetryStreamFloatField(TelemetryStreamField):
    def __init__(self, name):
        super(TelemetryStreamFloatField, self).__init__(name, TYPE_FLOAT, 4)

    def _store(self, buffer, ptr, value):
        buffer[ptr:ptr+4] = struct.pack('f', value)
        return ptr + self.field_size

    def packFormat(self):
        return 'f'


class TelemetryStreamDoubleField(TelemetryStreamField):
    def __init__(self, name):
        super(TelemetryStreamDoubleField, self).__init__(name, TYPE_DOUBLE, 8)

    def _store(self, buffer, ptr, value):
        buffer[ptr:ptr+8] = struct.pack('d', value)
        return ptr + self.field_size

    def packFormat(self):
        return 'd'


class TelemetryStreamStringField(TelemetryStreamField):
    def __init__(self, name, size):
        super(TelemetryStreamStringField, self).__init__(name, TYPE_STRING, size)

    def _store(self, buffer, ptr, value):
        length = len(value)
        buffer[ptr:ptr+self.field_size] = struct.pack(str(self.field_size) + 'd', value)
        return ptr + self.field_size

    def packFormat(self):
        return str(self.field_size) + 'p'

    def toJSON(self):
        return super(TelemetryStreamStringField, self).toJSON() + ", \"size\" : " + self.field_size

    def __eq__(self, other):
        if isinstance(other, TelemetryStreamStringField):
            return super(TelemetryStreamStringField, self).__eq__(other) and self.field_size == other.field_size
        return False


class TelemetryStreamBytesField(TelemetryStreamField):
    def __init__(self, name, size):
        super(TelemetryStreamBytesField, self).__init__(name, TYPE_BYTES, size)

    def _store(self, buffer, ptr, value):
        length = len(value)
        buffer[ptr:ptr+self.field_size] = value
        return ptr + self.field_size

    def packFormat(self):
        return str(self.field_size) + 's'

    def toJSON(self):
        return super(TelemetryStreamBytesField, self).toJSON() + ", \"size\" : " + self.field_size

    def __eq__(self, other):
        if isinstance(other, TelemetryStreamBytesField):
            return super(TelemetryStreamBytesField, self).__eq__(other) and self.field_size == other.field_size
        return False


class TelemetryStreamDefinition:

    def __init__(self, name):
        self.name = name
        self.stream_id = 0  # Not defined yet
        self.buildCallback = None
        self.fields = []
        self.fixed_length = 0
        self.pack_string = None
        self.header_byte = 0
        self.header_pack = None
        self.header = None

    def addByte(self, name, signed=False):
        self.fields.append(TelemetryStreamByteField(name, signed))
        return self

    def addWord(self, name, signed=False):
        self.fields.append(TelemetryStreamWordField(name, signed))
        return self

    def addInt(self, name, signed=False):
        self.fields.append(TelemetryStreamIntField(name, signed))
        return self

    def addLong(self, name, signed=False):
        self.fields.append(TelemetryStreamLongField(name, signed))
        return self

    def addFloat(self, name):
        self.fields.append(TelemetryStreamFloatField(name))
        return self

    def addDouble(self, name):
        self.fields.append(TelemetryStreamDoubleField(name))
        return self

    def addFixedString(self, name, size):
        self.fields.append(TelemetryStreamStringField(name, size))
        return self

    def addFixedBytes(self, name, size):
        self.fields.append(TelemetryStreamBytesField(name, size))
        return self

    def addVarLenString(self, name, size):
        raise NotImplemented("Not implemented yet")

    def addVarLenBytes(self, name, size):
        raise NotImplemented("Not implemented yet")

    def getFields(self):
        return self.fields

    def build(self, stream_id):
        self.stream_id = stream_id
        self.fixed_length = 0
        self.pack_string = ""
        for field in self.fields:
            if self.fixed_length is not None:
                field_len = field.field_size
                if field_len > 0:
                    self.fixed_length += field_len
                    self.pack_string += field.packFormat()
                else:
                    self.fixed_length = None
                    self.pack_string = None

        if self.pack_string is not None:
            self.pack_string = '<d' + self.pack_string
            self.fixed_length += 8

        if self.buildCallback is not None:
            self.buildCallback(self)

        self.header_pack = '<b'
        if self.stream_id < 256:
            self.header_byte = STREAM_ID_BYTE
            self.header_pack += 'b'
        else:
            self.header_byte = STREAM_ID_WORD
            self.header_pack += 'h'

        if self.fixed_length < 256:
            self.header_byte |= STREAM_SIZE_BYTE
            self.header_pack += 'b'
        elif self.fixed_length < 65536:
            self.header_byte |= STREAM_SIZE_WORD
            self.header_pack += 'h'
        else:
            self.header_byte |= STREAM_SIZE_LONG
            self.header_pack += 'i'

        self.header = struct.pack(self.header_pack, self.header_byte, self.stream_id, self.fixed_length)

    def extractTimestamp(self, record):
        return struct.unpack('<d', record[0:8])[0]

    def log(self, time_stamp, *args):
        if self.fixed_length is None:
            raise NotImplemented("Variable record size len is not yet implemented")

        if self.storage is None:
            raise NotImplemented("Stream storage is not set")

        record = struct.pack(self.pack_string, time_stamp, *args)
        self.storage.store(self, self, time_stamp, record)

    def retrieve(self, from_timestamp, to_timestmap):
        if self.storage is None:
            raise NotImplemented("Stream storage is not set")

        return self.storage.retrieve(self, from_timestamp, to_timestmap)

    def trim(self, stream, to_timestamp):
        if self.storage is None:
            raise NotImplemented("Stream storage is not set")

        self.storage.trim(self, to_timestamp)

    def getOldestTimestamp(self):
        if self.storage is None:
            raise NotImplemented("Stream storage is not set")

        return self.storage.getOldestTimestamp(self)

    def toJSON(self):
        return "{ \"id\" : " + str(self.stream_id) + ", \"name\" : \"" + self.name + "\", \"fields\" : { " + ", ".join(["\"" + field.name + "\" : { " + field.toJSON() + " }" for field in self.fields]) + " } }"


def streamFromJSON(json):

    def constToObject(v):
        return False if v == 'false' else True

    def decodeString(v):
        return bytes(v, "utf-8").decode("unicode_escape")

    STATE_TOP = 1
    STATE_OBJECT = 2
    STATE_NAME = 3
    STATE_AFTER_NAME = 4
    STATE_BEFORE_VALUE = 5
    STATE_AFTER_VALUE = 6
    STATE_INT_VALUE = 7
    STATE_FLOAT_VALUE = 8
    STATE_STR_VALUE = 9
    STATE_CONST_VALUE = 10
    top = {}
    stack = [top]
    i = 0
    length = len(json)
    state = STATE_TOP
    name = ""
    value = None
    negative = 1
    while i < length:
        c = json[i]
        if state == STATE_TOP:
            if c == '{':
                state = STATE_OBJECT
            elif c == ' ':
                pass
            else:
                raise SyntaxError("Expected '{'; index=" + str(i))

        elif state == STATE_OBJECT:
            if c == '}':
                del stack[len(stack) - 1]
                state = STATE_AFTER_VALUE
            elif c == ' ':
                pass
            elif c == '"':
                state = STATE_NAME
                name = ""
            else:
                raise SyntaxError("Expected '{' or '\"'; index=" + str(i))

        elif state == STATE_NAME:
            if c == '"':
                state = STATE_AFTER_NAME
            else:
                name += c

        elif state == STATE_AFTER_NAME:
            if c == ' ':
                pass
            elif c == ':':
                state = STATE_BEFORE_VALUE
            else:
                raise SyntaxError("Expected ':'; index=" + str(i))

        elif state == STATE_BEFORE_VALUE:
            if c == '{':
                d = {}
                stack[len(stack) - 1][name] = d
                stack.append(d)
                state = STATE_OBJECT
            elif c == ' ':
                pass
            elif '0' <= c <= '9':
                negative = 1
                value = c
                state = STATE_INT_VALUE
            elif c == '-':
                negative = -1
                value = c
                state = STATE_INT_VALUE
            elif c == '.':
                negative = 1
                value = c
                state = STATE_FLOAT_VALUE
            elif c == '"':
                state = STATE_STR_VALUE
                value = ""
            elif 'A' <= c <= 'Z' or 'a' <= c <= 'z' or c == '_':
                state = STATE_CONST_VALUE
                value = c
            else:
                raise SyntaxError("Expected '\"', number or constant; index=" + str(i))

        elif state == STATE_INT_VALUE:
            if '0' <= c <= '9':
                value += c
            elif c == '.':
                state = STATE_FLOAT_VALUE
                value += c
            elif c == ' ':
                stack[len(stack) - 1][name] = int(value) * negative
                state = STATE_AFTER_VALUE
            elif c == ',':
                stack[len(stack) - 1][name] = int(value) * negative
                state = STATE_OBJECT
            elif c == '}':
                stack[len(stack) - 1][name] = int(value) * negative
                del stack[len(stack) - 1]
                state = STATE_AFTER_VALUE
            else:
                raise SyntaxError("Expected ',' or '}'; index=" + str(i))

        elif state == STATE_FLOAT_VALUE:
            if '0' <= c <= '9':
                value += c
            elif c == ' ':
                stack[len(stack) - 1][name] = float(value) * negative
                state = STATE_AFTER_VALUE
            elif c == ',':
                stack[len(stack) - 1][name] = float(value) * negative
                state = STATE_OBJECT
            elif c == '}':
                stack[len(stack) - 1][name] = float(value) * negative
                del stack[len(stack) - 1]
                state = STATE_AFTER_VALUE
            else:
                raise SyntaxError("Expected ',' or '}'; index=" + str(i))

        elif state == STATE_CONST_VALUE:
            if 'A' <= c <= 'Z' or 'a' <= c <= 'z' or c == '_':
                value += c
            elif c == ' ':
                stack[len(stack) - 1][name] = constToObject(value)
                state = STATE_AFTER_VALUE
            elif c == ',':
                stack[len(stack) - 1][name] = constToObject(value)
                state = STATE_OBJECT
            elif c == '}':
                stack[len(stack) - 1][name] = constToObject(value)
                del stack[len(stack) - 1]
                state = STATE_AFTER_VALUE
            else:
                raise SyntaxError("Expected ',' or '}'; index=" + str(i))

        elif state == STATE_STR_VALUE:
            if c == '"':
                stack[len(stack) - 1][name] = decodeString(value)
                state = STATE_AFTER_VALUE
            else:
                value += c

        elif state == STATE_AFTER_VALUE:
            if c == '}':
                del stack[len(stack) - 1]
                state = STATE_AFTER_VALUE
            elif c == ',':
                state = STATE_OBJECT
            elif c == ' ':
                pass
            else:
                raise SyntaxError("Expected '}' or ','; index=" + str(i))

        i += 1

    # after parsing
    # print("Got: " + str(top))
    if 'id' not in top:
        raise SyntaxError("Missing 'id' value")
    if 'name' not in top:
        raise SyntaxError("Missing 'name' value")
    if 'fields' not in top:
        raise SyntaxError("Missing 'fields' value")

    stream = TelemetryStreamDefinition(top['name'])
    stream.stream_id = int(top['id'])
    fields = top['fields']
    for fieldName in fields:
        field = fields[fieldName]
        if 'type' not in field:
            raise SyntaxError("Missing 'type' value for field " + str(fieldName))
        if field['type'] == TYPE_BYTE:
            stream.addByte(fieldName, field['signed'])
        elif field['type'] == TYPE_WORD:
            stream.addWord(fieldName, field['signed'])
        elif field['type'] == TYPE_INT:
            stream.addInt(fieldName, field['signed'])
        elif field['type'] == TYPE_LONG:
            stream.addLong(fieldName, field['signed'])
        elif field['type'] == TYPE_FLOAT:
            stream.addFloat(fieldName)
        elif field['type'] == TYPE_DOUBLE:
            stream.addDouble(fieldName)
        elif field['type'] == TYPE_STRING:
            stream.addFixedString(fieldName, field['size'])
        elif field['type'] == TYPE_BYTES:
            stream.addFixedBytes(fieldName, field['size'])

    return stream
