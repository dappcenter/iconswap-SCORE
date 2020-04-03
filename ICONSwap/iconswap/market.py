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
from ..scorelib.iterable_dict import *


class PendingSwapMarketDB(SetDB):
    _NAME = 'PENDING_SWAP_MARKET_DB'

    def __init__(self, db: IconScoreDatabase, pair: tuple):
        name = MarketPairsDB.get_pair_name(pair) + '_' + PendingSwapMarketDB._NAME
        super().__init__(name, db, int)


class FilledSwapMarketDB(SetDB):
    _NAME = 'FILLED_SWAP_MARKET_DB'

    def __init__(self, db: IconScoreDatabase, pair: tuple):
        name = MarketPairsDB.get_pair_name(pair) + '_' + FilledSwapMarketDB._NAME
        super().__init__(name, db, int)


class MarketPairsDB(SetDB):
    _NAME = 'MARKET_PAIRS_DB'

    @staticmethod
    def get_pair_name(pair: tuple) -> str:
        contracts_alpha = sorted([str(pair[0]), str(pair[1])])
        return contracts_alpha[0] + '/' + contracts_alpha[1]

    def __init__(self, db: IconScoreDatabase):
        super().__init__(MarketPairsDB._NAME, db, str)

    def add(self, pair: tuple) -> None:
        super().add(MarketPairsDB.get_pair_name(pair))

    def __contains__(self, pair: tuple) -> bool:
        return super().__contains__(MarketPairsDB.get_pair_name(pair))
