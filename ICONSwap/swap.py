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
from .utils import *
from .order import *
from .consts import *
from .composite import *
from .factory import *

# ================================================
#  Exception
# ================================================


class InvalidSwapStatus(Exception):
    pass


class InvalidMakerAddress(Exception):
    pass


class InvalidSwapProvider(Exception):
    pass


class SwapDoesntExist(Exception):
    pass


class SwapFactory(Factory):
    # ================================================
    #  Methods
    # ================================================
    @staticmethod
    def create(db: IconScoreDatabase,
               maker_order_id: int,
               taker_order_id: int,
               timestamp: int,
               maker_address: Address) -> int:

        uid = Factory.get_uid(db, 'SWAP')
        item = Swap(db, uid)
        item._maker_order_id.set(maker_order_id)
        item._taker_order_id.set(taker_order_id)
        item._timestamp_create.set(timestamp)
        item._timestamp_swap.set(0)
        item._maker_address.set(maker_address)
        item._status.set(SwapStatus.PENDING)
        item._transaction.set('')
        AllSwapComposite(db).add(uid)
        PendingSwapAccountComposite(db, maker_address).add(uid)

        return uid


class SwapStatus:
    PENDING = 0
    CANCELLED = 1
    SUCCESS = 2


class Swap(object):
    # ================================================
    #  DB Variables
    # ================================================
    _MAKER_ORDER_ID = 'SWAP_MAKER_ORDER_ID'
    _TAKER_ORDER_ID = 'SWAP_TAKER_ORDER_ID'
    _MAKER_ADDRESS = 'SWAP_MAKER_ADDRESS'
    _STATUS = 'SWAP_STATUS'
    _TIMESTAMP_CREATE = 'SWAP_TIMESTAMP_CREATE'
    _TIMESTAMP_SWAP = 'SWAP_TIMESTAMP_SWAP'
    _TRANSACTION = 'SWAP_TRANSACTION'

    # ================================================
    #  Initialization
    # ================================================
    def __init__(self, db: IconScoreDatabase, uid: int) -> None:
        self._maker_order_id = VarDB(f'{Swap._MAKER_ORDER_ID}_{uid}', db, value_type=int)
        self._taker_order_id = VarDB(f'{Swap._TAKER_ORDER_ID}_{uid}', db, value_type=int)
        self._maker_address = VarDB(f'{Swap._MAKER_ADDRESS}_{uid}', db, value_type=Address)
        self._status = VarDB(f'{Swap._STATUS}_{uid}', db, value_type=int)
        self._timestamp_create = VarDB(f'{Swap._TIMESTAMP_CREATE}_{uid}', db, value_type=int)
        self._timestamp_swap = VarDB(f'{Swap._TIMESTAMP_SWAP}_{uid}', db, value_type=int)
        self._transaction = VarDB(f'{Swap._TRANSACTION}_{uid}', db, value_type=str)

    # ================================================
    #  Private Methods
    # ================================================

    # ================================================
    #  Checks
    # ================================================
    def check_status(self, status: int) -> None:
        if self._status.get() != status:
            raise InvalidSwapStatus

    def check_maker_address(self, maker_address: Address) -> None:
        if self._maker_address.get() != maker_address:
            raise InvalidMakerAddress

    # ================================================
    #  Public Methods
    # ================================================
    def set_status(self, status: int) -> None:
        self._status.set(status)

    def set_transaction(self, transaction: str) -> None:
        self._transaction.set(transaction)
    
    def set_timestamp_swap(self, time: int) -> None:
        self._timestamp_swap.set(time)

    def get_orders(self) -> tuple:
        return (self._maker_order_id.get(), self._taker_order_id.get())

    def maker_address(self) -> Address:
        return self._maker_address.get()

    def serialize(self) -> dict:
        return {
            'maker_order_id': self._maker_order_id.get(),
            'taker_order_id': self._taker_order_id.get(),
            'status': Utils.enum_names(SwapStatus)[self._status.get()],
            'timestamp_create': self._timestamp_create.get(),
            'timestamp_swap': self._timestamp_swap.get(),
            'maker_address': self._maker_address.get(),
            'transaction': self._transaction.get()
        }

    def delete(self) -> None:
        self._maker_order_id.remove()
        self._taker_order_id.remove()
        self._status.remove()
        self._timestamp_create.remove()
        self._timestamp_swap.remove()
        self._maker_address.remove()
        self._transaction.remove()


class AllSwapComposite(Composite):
    _NAME = 'ALL_SWAP_COMPOSITE'

    def __init__(self, db: IconScoreDatabase):
        super().__init__(db, AllSwapComposite._NAME, int)

class PendingSwapAccountComposite(Composite):
    _NAME = 'PENDING_SWAP_ACCOUNT_COMPOSITE'

    def __init__(self, db: IconScoreDatabase, address: Address):
        super().__init__(db, str(address) + '_' + PendingSwapAccountComposite._NAME, int)

class FilledSwapAccountComposite(Composite):
    _NAME = 'FILLED_SWAP_ACCOUNT_COMPOSITE'

    def __init__(self, db: IconScoreDatabase, address: Address):
        super().__init__(db, str(address) + '_' + FilledSwapAccountComposite._NAME, int)
