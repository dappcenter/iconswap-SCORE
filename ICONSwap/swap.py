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
        item._timestamp.set(timestamp)
        item._maker_address.set(maker_address)
        item._status.set(SwapStatus.PENDING)
        item._transaction.set('')
        SwapComposite(db).add(uid)

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
    _TIMESTAMP = 'SWAP_TIMESTAMP'
    _TRANSACTION = 'SWAP_TRANSACTION'

    # ================================================
    #  Initialization
    # ================================================
    def __init__(self, db: IconScoreDatabase, uid: int) -> None:
        self._maker_order_id = VarDB(f'{Swap._MAKER_ORDER_ID}_{uid}', db, value_type=int)
        self._taker_order_id = VarDB(f'{Swap._TAKER_ORDER_ID}_{uid}', db, value_type=int)
        self._maker_address = VarDB(f'{Swap._MAKER_ADDRESS}_{uid}', db, value_type=Address)
        self._status = VarDB(f'{Swap._STATUS}_{uid}', db, value_type=int)
        self._timestamp = VarDB(f'{Swap._TIMESTAMP}_{uid}', db, value_type=int)
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

    def get_orders(self) -> tuple:
        return (self._maker_order_id.get(), self._taker_order_id.get())

    def serialize(self) -> dict:
        return {
            'maker_order_id': self._maker_order_id.get(),
            'taker_order_id': self._taker_order_id.get(),
            'status': Utils.enum_names(SwapStatus)[self._status.get()],
            'timestamp': self._timestamp.get(),
            'maker_address': self._maker_address.get(),
            'transaction': self._transaction.get() or ''
        }

    def delete(self) -> None:
        self._maker_order_id.remove()
        self._taker_order_id.remove()
        self._status.remove()
        self._timestamp.remove()
        self._maker_address.remove()
        self._transaction.remove()


class SwapComposite(Composite):
    _NAME = 'SWAP_COMPOSITE'

    def __init__(self, db: IconScoreDatabase):
        super().__init__(db, SwapComposite._NAME, int)

    @staticmethod
    def pending(swap: Swap) -> bool:
        return swap._status.get() == SwapStatus.PENDING

    @staticmethod
    def open_orders_by_address(swap: Swap, address: Address) -> bool:
        return swap._status.get() == SwapStatus.PENDING and swap._maker_address.get() == address

    @staticmethod
    def open_orders(swap: Swap) -> bool:
        return swap._status.get() == SwapStatus.PENDING
