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
from .swap import *
from ..interfaces.irc2 import *
from ..scorelib.linked_list import *
from ..scorelib.set import *


class InvalidMarketPair(Exception):
    pass


class _MarketSidePendingSwapDB(UIDLinkedListDB):
    """ _MarketSidePendingSwapDB is a linked list of swaps
        sorted by a given "compare" function
     """
    _NAME = '_MARKET_SIDE_PENDING_SWAP_DB'

    def __init__(self, var_key: str, db: IconScoreDatabase):
        name = var_key + _MarketSidePendingSwapDB._NAME
        super().__init__(name, db)
        self._name = name
        self._db = db

    def add(self, new_swap_id: int, compare) -> None:
        """ Iterate through swap list and insert it according to the price """
        # Find positionning in the list for the current item
        for cur_swap_id in self:
            if compare(new_swap_id, cur_swap_id):
                self.prepend_before(new_swap_id, cur_swap_id)
                break
        else:
            self.append(new_swap_id)


class _MarketBuyersPendingSwapDB(_MarketSidePendingSwapDB):
    """ _MarketBuyersPendingSwapDB is a linked list of swaps
        of buyers in a given market sorted by a descending price
     """
    _NAME = '_BUYERS'

    def __init__(self, var_key: str, db: IconScoreDatabase):
        name = var_key + _MarketBuyersPendingSwapDB._NAME
        super().__init__(name, db)
        self._name = name
        self._db = db

    def compare(self, new_swap_id: int, cur_swap_id: int) -> bool:
        new_swap_price = Swap(new_swap_id, self._db).get_price()
        cur_swap_price = Swap(cur_swap_id, self._db).get_price()
        return new_swap_price > cur_swap_price

    def add(self, new_swap_id: int) -> None:
        super().add(new_swap_id, self.compare)


class _MarketSellersPendingSwapDB(_MarketSidePendingSwapDB):
    """ _MarketSellersPendingSwapDB is a linked list of swaps
        of sellers in a given market sorted by a descending price
     """
    _NAME = '_SELLERS'

    def __init__(self, var_key: str, db: IconScoreDatabase):
        name = var_key + _MarketSellersPendingSwapDB._NAME
        super().__init__(name, db)
        self._name = name

    def compare(self, new_swap_id: int, cur_swap_id: int) -> bool:
        new_swap_price = Swap(new_swap_id, self._db).get_inverted_price()
        cur_swap_price = Swap(cur_swap_id, self._db).get_inverted_price()
        return new_swap_price < cur_swap_price

    def add(self, new_swap_id: int) -> None:
        super().add(new_swap_id, self.compare)


class MarketPendingSwapDB:
    """ MarketPendingSwapDB is two linked lists of swaps (buyers and sellers)
        sorted by their price
     """
    _NAME = '_MARKET_PENDING_SWAP_DB'

    def __init__(self, pair: tuple, db: IconScoreDatabase):
        self._name = MarketPairsDB.get_pair_name(pair) + MarketPendingSwapDB._NAME
        self._buyers = _MarketBuyersPendingSwapDB(self._name, db)
        self._sellers = _MarketSellersPendingSwapDB(self._name, db)
        self._pair = pair
        self._db = db

    def __len__(self) -> int:
        return len(self._buyers) + len(self._sellers)

    def buyers(self) -> _MarketBuyersPendingSwapDB:
        return self._buyers

    def sellers(self) -> _MarketSellersPendingSwapDB:
        return self._sellers

    def add(self, new_swap_id: int) -> None:
        swap = Swap(new_swap_id, self._db)
        maker, taker = swap.get_orders()
        pair = (maker.contract(), taker.contract())
        if MarketPairsDB.is_buyer(pair, maker):
            self._buyers.add(new_swap_id)
        else:
            self._sellers.add(new_swap_id)

    def remove(self, swap_id: int) -> None:
        swap = Swap(swap_id, self._db)
        maker, taker = swap.get_orders()
        pair = (maker.contract(), taker.contract())
        if MarketPairsDB.is_buyer(pair, maker):
            self._buyers.remove(swap_id)
        else:
            self._sellers.remove(swap_id)


class MarketFilledSwapDB(UIDLinkedListDB):
    _NAME = 'MARKET_FILLED_SWAP_DB'

    def __init__(self, pair: tuple, db: IconScoreDatabase):
        name = MarketPairsDB.get_pair_name(pair) + '_' + MarketFilledSwapDB._NAME
        super().__init__(name, db)
        self._name = name


class MarketPairsDB(SetDB):
    _NAME = 'MARKET_PAIRS_DB'

    def __init__(self, db: IconScoreDatabase):
        name = MarketPairsDB._NAME
        super().__init__(name, db, str)
        self._name = name

    @staticmethod
    def check_valid_pair(pair: tuple) -> None:
        if len(pair) != 2:
            raise InvalidMarketPair(pair)
        try:
            # Check if valid Address
            Address.from_string(pair[0])
            Address.from_string(pair[1])
        except:
            raise InvalidMarketPair(pair)

    @staticmethod
    def is_buyer(pair: tuple, order: Order) -> bool:
        contracts_alpha = sorted([str(pair[0]), str(pair[1])])
        return order.contract() == Address.from_string(contracts_alpha[1])

    @staticmethod
    def get_pair_name(pair: tuple) -> str:
        contracts_alpha = sorted([str(pair[0]), str(pair[1])])
        return contracts_alpha[0] + '/' + contracts_alpha[1]

    def add(self, pair: tuple) -> None:
        super().add(MarketPairsDB.get_pair_name(pair))

    def __contains__(self, pair: tuple) -> bool:
        return super().__contains__(MarketPairsDB.get_pair_name(pair))
