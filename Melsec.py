import time
from tango import AttrQuality, AttrWriteType, DispLevel, DevState, Attr, CmdArgType, UserDefaultAttrProp
from tango.server import Device, attribute, command, DeviceMeta
from tango.server import class_property, device_property
from tango.server import run
import os
import json
from threading import Thread
from threading import Lock
import datetime
from pymelsec import MelsecClient
from json import JSONDecodeError

class Melsec(Device, metaclass=DeviceMeta):
    host = device_property(dtype=str, default_value="127.0.0.1")
    port = device_property(dtype=int, default_value=5000)
    protocol_type = device_property(dtype=str, default_value="3E")
    plc_type = device_property(dtype=str, default_value="L")
    encoding = device_property(dtype=str, default_value="binary")
    init_dynamic_attributes = device_property(dtype=str, default_value="")
    client = None
    dynamic_attribute_symbols = {}

    @attribute
    def time(self):
        return time.time()

    @command(dtype_in=str)
    def add_dynamic_attribute(self, symbolName,
            variable_type_name="DevString", min_value="", max_value="",
            unit="", write_type_name="", label="", min_alarm="", max_alarm="",
            min_warning="", max_warning=""):
        if symbolName == "": return
        prop = UserDefaultAttrProp()
        variableType = self.stringValueToVarType(variable_type_name)
        writeType = self.stringValueToWriteType(write_type_name)
        if(min_value != "" and min_value != max_value): prop.set_min_value(min_value)
        if(max_value != "" and min_value != max_value): prop.set_max_value(max_value)
        if(unit != ""): prop.set_unit(unit)
        if(label != ""): prop.set_label(label)
        if(min_alarm != ""): prop.set_min_alarm(min_alarm)
        if(max_alarm != ""): prop.set_max_alarm(max_alarm)
        if(min_warning != ""): prop.set_min_warning(min_warning)
        if(max_warning != ""): prop.set_max_warning(max_warning)
        attr = Attr(symbolName, variableType, writeType)
        attr.set_default_properties(prop)
        self.add_attribute(attr, r_meth=self.read_dynamic_attr, w_meth=self.write_dynamic_attr)
        self.dynamic_attribute_symbols[symbolName] = symbolName
        print("Added dynamic attribute " + symbolName)

    def stringValueToVarType(self, variable_type_name) -> CmdArgType:
        if(variable_type_name == "DevBoolean"):
            return CmdArgType.DevBoolean
        if(variable_type_name == "DevLong"):
            return CmdArgType.DevLong
        if(variable_type_name == "DevDouble"):
            return CmdArgType.DevDouble
        if(variable_type_name == "DevFloat"):
            return CmdArgType.DevFloat
        if(variable_type_name == "DevString"):
            return CmdArgType.DevString
        if(variable_type_name == ""):
            return CmdArgType.DevString
        raise Exception("given variable_type '" + variable_type_name + "' unsupported, supported are: DevBoolean, DevLong, DevDouble, DevFloat, DevString")

    def stringValueToWriteType(self, write_type_name) -> AttrWriteType:
        if(write_type_name == "READ"):
            return AttrWriteType.READ
        if(write_type_name == "WRITE"):
            return AttrWriteType.WRITE
        if(write_type_name == "READ_WRITE"):
            return AttrWriteType.READ_WRITE
        if(write_type_name == "READ_WITH_WRITE"):
            return AttrWriteType.READ_WITH_WRITE
        if(write_type_name == ""):
            return AttrWriteType.READ_WRITE
        raise Exception("given write_type '" + write_type_name + "' unsupported, supported are: READ, WRITE, READ_WRITE, READ_WITH_WRITE")

    def read_dynamic_attr(self, attr):
        name = attr.get_name()
        symbol = self.dynamic_attribute_symbols[name]
        value = self.client.read(symbol)
        self.debug_stream("read value " + str(name) + ": " + str(value))
        attr.set_value(value)

    def write_dynamic_attr(self, attr):
        value = attr.get_write_value()
        name = attr.get_name()
        symbol = self.dynamic_attribute_symbols[name]
        self.client.write(symbol, value)

    def init_device(self):
        self.set_state(DevState.INIT)
        self.get_device_properties(self.get_device_class())
        self.info_stream("Connecting to " + str(self.host) + ":" + str(self.port) + ", protocol: " + self.protocol_type + ", plc type: " + self.plc_type + ", encoding: " + self.encoding)
        self.client = MelsecClient(protocol=self.protocol_type, plc_type=self.plc_type, encoding=self.encoding)
        self.client.connect(self.host, self.port)
        if self.init_dynamic_attributes != "":
            try:
                attributes = json.loads(self.init_dynamic_attributes)
                for attributeData in attributes:
                    self.add_dynamic_attribute(attributeData["name"],
                        attributeData.get("data_type", ""), attributeData.get("min_value", ""), attributeData.get("max_value", ""),
                        attributeData.get("unit", ""), attributeData.get("write_type", ""), attributeData.get("label", ""),
                        attributeData.get("min_alarm", ""), attributeData.get("max_alarm", ""),
                        attributeData.get("min_warning", ""), attributeData.get("max_warning", ""))
            except JSONDecodeError as e:
                raise e
        self.set_state(DevState.ON)

if __name__ == "__main__":
    deviceServerName = os.getenv("DEVICE_SERVER_NAME", "Melsec")
    run({deviceServerName: Melsec})
