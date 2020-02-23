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


class InvalidSwapAuthor(Exception):
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
               uid1: int,
               uid2: int,
               timestamp: int,
               author: Address) -> int:

        uid = Factory.get_uid(db, 'SWAP')
        item = Swap(db, uid)
        item._order1.set(uid1)
        item._order2.set(uid2)
        item._timestamp.set(timestamp)
        item._author.set(author)
        item._status.set(SwapStatus.PENDING)
        item._transaction.set('')
        SwapComposite(db).add(uid)

        return uid


class SwapComposite(Composite):
    _NAME = 'SWAP_COMPOSITE'

    def __init__(self, db: IconScoreDatabase):
        super().__init__(db, SwapComposite._NAME, int)


class SwapStatus:
    PENDING = 0
    CANCELLED = 1
    SUCCESS = 2


class Swap(object):
    # ================================================
    #  DB Variables
    # ================================================
    _ORDER1 = 'SWAP_ORDER1'
    _ORDER2 = 'SWAP_ORDER2'
    _STATUS = 'SWAP_STATUS'
    _TIMESTAMP = 'SWAP_TIMESTAMP'
    _AUTHOR = 'SWAP_AUTHOR'
    _TRANSACTION = 'SWAP_TRANSACTION'

    # ================================================
    #  Initialization
    # ================================================
    def __init__(self, db: IconScoreDatabase, uid: int) -> None:
        self._order1 = VarDB(f'{Swap._ORDER1}_{uid}', db, value_type=int)
        self._order2 = VarDB(f'{Swap._ORDER2}_{uid}', db, value_type=int)
        self._status = VarDB(f'{Swap._STATUS}_{uid}', db, value_type=int)
        self._timestamp = VarDB(f'{Swap._TIMESTAMP}_{uid}', db, value_type=int)
        self._author = VarDB(f'{Swap._AUTHOR}_{uid}', db, value_type=Address)
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

    def check_author(self, author: Address) -> None:
        if self._author.get() != author:
            raise InvalidSwapAuthor

    # ================================================
    #  Public Methods
    # ================================================
    def set_status(self, status: int) -> None:
        self._status.set(status)
    
    def set_transaction(self, transaction: str) -> None:
        self._transaction.set(transaction)

    def get_orders(self) -> tuple:
        return (self._order1.get(), self._order2.get())

    def serialize(self) -> dict:
        return {
            'order1': self._order1.get(),
            'order2': self._order2.get(),
            'status': Utils.enum_names(SwapStatus)[self._status.get()],
            'timestamp': self._timestamp.get(),
            'author': self._author.get(),
            'transaction': self._transaction.get()
        }

    def delete(self) -> None:
        self._order1.remove()
        self._order2.remove()
        self._status.remove()
        self._timestamp.remove()
        self._author.remove()
        self._transaction.remove()
