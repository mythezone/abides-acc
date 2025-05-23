from PyFlow.Core import PinBase
from PyFlow.Core.Common import *

class FakeTypeTEEUW(object):
    """docstring for FakeTypeTEEUW"""
    def __init__(self, value=None):
        super(FakeTypeTEEUW, self).__init__()
        self.value = value


class DemoPin(PinBase):
    """doc string for DemoPin"""
    def __init__(self, name, parent, direction, **kwargs):
        super(DemoPin, self).__init__(name, parent, direction, **kwargs)
        self.setDefaultValue(False)

    @staticmethod
    def IsValuePin():
        return True

    @staticmethod
    def supportedDataTypes():
        return ('DemoPin',)

    @staticmethod
    def pinDataTypeHint():
        return 'DemoPin', False

    @staticmethod
    def color():
        return (200, 200, 50, 255)

    @staticmethod
    def internalDataStructure():
        return FakeTypeTEEUW

    @staticmethod
    def processData(data):
        return DemoPin.internalDataStructure()(data)
