

from iconservice import *
from ..scorelib.set import *


class InvalidWhitelistContract(Exception):
    pass


class Whitelist(SetDB):

    _NAME = 'WHITELIST'

    def __init__(self, db: IconScoreDatabase):
        super().__init__(Whitelist._NAME, db, Address)

    def add(self, token: Address) -> None:
        if not token.is_contract:
            raise InvalidWhitelistContract(self._NAME, token)
        super().add(token)
