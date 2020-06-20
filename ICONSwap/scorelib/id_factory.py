

from iconservice import *


class IdFactory:
    """ IdFactory is able to generate unique identifiers for a collection of items. """

    _NAME = '_ID_FACTORY'

    def __init__(self, var_key: str, db: IconScoreDatabase):
        self._name = var_key + IdFactory._NAME
        self._uid = VarDB(f'{self._name}_uid', db, int)
        self._db = db

    def get_uid(self) -> int:
        # UID = 0 is forbidden in order to prevent conflict with uninitialized uid
        # Starts with UID 1
        self._uid.set(self._uid.get() + 1)
        return self._uid.get()
