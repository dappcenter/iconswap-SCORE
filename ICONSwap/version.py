

from iconservice import *
from .consts import *


class Version(object):

    # ================================================
    #  DB Variables
    # ================================================
    _NAME = 'VERSION'

    # ================================================
    #  Private Methods
    # ================================================
    def __init__(self, db: IconScoreDatabase):
        self._name = Version._NAME
        self._version = VarDB(self._name, db, value_type=str)
        self._db = db

    @staticmethod
    def _as_tuple(version: str) -> tuple:
        parts = []
        for part in version.split('.'):
            parts.append(int(part))
        return tuple(parts)

    # ================================================
    #  Public Methods
    # ================================================
    def update(self, version: str) -> None:
        self._version.set(version)

    def get(self) -> str:
        return self._version.get()

    def is_less_than_target_version(self, target: str) -> bool:
        return Version._as_tuple(self.get()) < Version._as_tuple(target)

    def __delete__(self) -> None:
        self._version.remove()
