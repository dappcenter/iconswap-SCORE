

from iconservice import *
from .consts import *


class Utils():

    @staticmethod
    def enum_names(cls):
        return [i for i in cls.__dict__.keys() if i[:1] != '_']
