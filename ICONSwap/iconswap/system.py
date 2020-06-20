

from iconservice import *
from ..scorelib.set import *


class SystemSwapDB(SetDB):
    _NAME = 'SYSTEM_SWAP_DB'

    def __init__(self, db: IconScoreDatabase):
        super().__init__(SystemSwapDB._NAME, db, int)


class SystemOrderDB(SetDB):
    _NAME = 'SYSTEM_ORDER_DB'

    def __init__(self, db: IconScoreDatabase):
        super().__init__(SystemOrderDB._NAME, db, int)
