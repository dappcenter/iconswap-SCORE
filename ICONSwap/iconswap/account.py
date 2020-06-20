

from iconservice import *
from .consts import *
from .market import *
from ..scorelib.utils import *
from ..scorelib.linked_list import *


class AccountPendingSwapDB(UIDLinkedListDB):
    _NAME = 'ACCOUNT_PENDING_SWAP_DB'

    def __init__(self, address: Address, db: IconScoreDatabase):
        name = f'{str(address)}_{AccountPendingSwapDB._NAME}'
        super().__init__(name, db)
        self._name = name


class AccountFilledSwapDB(UIDLinkedListDB):
    _NAME = 'ACCOUNT_FILLED_SWAP_DB'

    def __init__(self, address: Address, db: IconScoreDatabase):
        name = f'{str(address)}_{AccountFilledSwapDB._NAME}'
        super().__init__(name, db)
        self._name = name


class AccountPairPendingSwapDB(UIDLinkedListDB):
    _NAME = 'ACCOUNT_PAIR_PENDING_SWAP_DB'

    def __init__(self, address: Address, pair: tuple, db: IconScoreDatabase):
        pair_name = MarketPairsDB.get_pair_name(pair)
        name = f'{str(address)}_{pair_name}_{AccountPairPendingSwapDB._NAME}'
        super().__init__(name, db)
        self._name = name


class AccountPairFilledSwapDB(UIDLinkedListDB):
    _NAME = 'ACCOUNT_PAIR_FILLED_SWAP_DB'

    def __init__(self, address: Address, pair: tuple, db: IconScoreDatabase):
        pair_name = MarketPairsDB.get_pair_name(pair)
        name = f'{str(address)}_{pair_name}_{AccountPairFilledSwapDB._NAME}'
        super().__init__(name, db)
        self._name = name
