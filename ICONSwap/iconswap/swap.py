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
from .order import *
from ..scorelib.id_factory import *
from ..scorelib.utils import *

# ================================================
#  Exception
# ================================================


class InvalidSwapStatus(Exception):
    pass


class SwapFactory(IdFactory):

    _NAME = 'SWAP_FACTORY'

    def __init__(self, db: IconScoreDatabase):
        name = SwapFactory._NAME
        super().__init__(name, db)
        self._name = name
        self._db = db

    def create(self, maker_order_id: int,
               taker_order_id: int,
               timestamp: int,
               maker_address: Address) -> int:

        swap_id = self.get_uid()
        swap = Swap(swap_id, self._db)
        swap._maker_order_id.set(maker_order_id)
        swap._taker_order_id.set(taker_order_id)
        swap._timestamp_create.set(timestamp)
        swap._timestamp_swap.set(0)
        swap._status.set(SwapStatus.PENDING)

        return swap_id


class SwapStatus:
    PENDING = 0
    CANCELLED = 1
    SUCCESS = 2


class Swap(object):

    _NAME = 'SWAP'

    # ================================================
    #  Initialization
    # ================================================
    def __init__(self, uid: int, db: IconScoreDatabase):
        self._name = Swap._NAME
        self._maker_order_id = VarDB(f'{self._name}_MAKER_ORDER_ID_{uid}', db, value_type=int)
        self._taker_order_id = VarDB(f'{self._name}_TAKER_ORDER_ID_{uid}', db, value_type=int)
        self._status = VarDB(f'{self._name}_STATUS_{uid}', db, value_type=int)
        self._timestamp_create = VarDB(f'{self._name}_TIMESTAMP_CREATE_{uid}', db, value_type=int)
        self._timestamp_swap = VarDB(f'{self._name}_TIMESTAMP_SWAP_{uid}', db, value_type=int)
        self._transaction = VarDB(f'{self._name}_TRANSACTION_{uid}', db, value_type=str)
        self._uid = uid
        self._db = db

    # ================================================
    #  Checks
    # ================================================
    def check_status(self, status: int) -> None:
        if self._status.get() != status:
            raise InvalidSwapStatus

    def check_maker_address(self, maker_address: Address) -> None:
        maker_provider = Order(self._maker_order_id.get(), self._db).provider()
        if maker_provider != maker_address:
            raise InvalidOrderProvider(maker_provider, maker_address)

    # ================================================
    #  Public Methods
    # ================================================
    def id(self) -> int:
        return self._uid

    def set_status(self, status: int) -> None:
        self._status.set(status)

    def set_transaction(self, transaction: str) -> None:
        self._transaction.set(transaction)

    def set_timestamp_swap(self, time: int) -> None:
        self._timestamp_swap.set(time)

    def get_orders(self) -> tuple:
        maker = Order(self._maker_order_id.get(), self._db)
        taker = Order(self._taker_order_id.get(), self._db)
        return (maker, taker)

    def get_price(self) -> float:
        maker, taker = self.get_orders()
        return maker.amount() / taker.amount()

    def get_inverted_price(self) -> float:
        maker, taker = self.get_orders()
        return taker.amount() / maker.amount()

    def is_private(self) -> bool:
        maker, taker = self.get_orders()
        return taker.provider() != EMPTY_ORDER_PROVIDER

    def serialize(self) -> dict:
        maker, taker = self.get_orders()
        return {
            'id': self._uid,
            'maker': maker.serialize(),
            'taker': taker.serialize(),
            'status': Utils.enum_names(SwapStatus)[self._status.get()],
            'timestamp_create': self._timestamp_create.get(),
            'timestamp_swap': self._timestamp_swap.get(),
            'transaction': self._transaction.get()
        }

    def __delete__(self) -> None:
        maker, taker = self.get_orders()
        del maker
        del taker
        self._maker_order_id.remove()
        self._taker_order_id.remove()
        self._status.remove()
        self._timestamp_create.remove()
        self._timestamp_swap.remove()
        self._transaction.remove()
