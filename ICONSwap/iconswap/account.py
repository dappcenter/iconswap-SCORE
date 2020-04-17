# -*- coding: utf-8 -*-

# Copyright 2020 ICONation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from iconservice import *
from .consts import *
from .market import *
from ..scorelib.utils import *
from ..scorelib.linked_list import *


class AccountPendingSwapDB(UIDLinkedListDB):
    _NAME = 'ACCOUNT_PENDING_SWAP_DB'

    def __init__(self, address: Address, db: IconScoreDatabase):
        name = f'{str(address)}_{AccountPendingSwapDB._NAME}'
        super().__init__(name, db, int)
        self._name = name


class AccountFilledSwapDB(UIDLinkedListDB):
    _NAME = 'ACCOUNT_FILLED_SWAP_DB'

    def __init__(self, address: Address, db: IconScoreDatabase):
        name = f'{str(address)}_{AccountFilledSwapDB._NAME}'
        super().__init__(name, db, int)
        self._name = name


class AccountPairPendingSwapDB(UIDLinkedListDB):
    _NAME = 'ACCOUNT_PAIR_PENDING_SWAP_DB'

    def __init__(self, address: Address, pair: tuple, db: IconScoreDatabase):
        pair_name = MarketPairsDB.get_pair_name(pair)
        name = f'{str(address)}_{pair_name}_{AccountPairPendingSwapDB._NAME}'
        super().__init__(name, db, int)
        self._name = name


class AccountPairFilledSwapDB(UIDLinkedListDB):
    _NAME = 'ACCOUNT_PAIR_FILLED_SWAP_DB'

    def __init__(self, address: Address, pair: tuple, db: IconScoreDatabase):
        pair_name = MarketPairsDB.get_pair_name(pair)
        name = f'{str(address)}_{pair_name}_{AccountPairFilledSwapDB._NAME}'
        super().__init__(name, db, int)
        self._name = name
