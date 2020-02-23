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
from .consts import *
from .composite import *
from .factory import *

# ================================================
#  Exception
# ================================================


class InvalidOrderContent(Exception):
    pass


class InvalidOrderStatus(Exception):
    pass


class InvalidOrderProvider(Exception):
    pass


class InvalidOrderId(Exception):
    pass


class InvalidOrderAmount(Exception):
    pass


class InvalidOrderContract(Exception):
    pass


class OrderFactory(Factory):
    _NAME = 'ORDER_FACTORY'

    @staticmethod
    def create(db: IconScoreDatabase,
               contract: Address,
               amount: int) -> int:

        uid = Factory.get_uid(db, OrderFactory._NAME)
        item = Order(db, uid)
        item._contract.set(contract)
        item._amount.set(amount)
        item._status.set(OrderStatus.EMPTY)
        OrderComposite(db).add(uid)

        return uid


class OrderComposite(Composite):
    _NAME = 'ORDER_COMPOSITE'

    def __init__(self, db: IconScoreDatabase):
        super().__init__(db, OrderComposite._NAME, int)

class OrderStatus:
    EMPTY = 0
    FILLED = 1
    CANCELLED = 2
    SUCCESS = 3

class Order(object):
    # ================================================
    #  DB Variables
    # ================================================
    _CONTRACT = 'ORDER_CONTRACT'
    _AMOUNT = 'ORDER_AMOUNT'
    _PROVIDER = 'ORDER_PROVIDER'
    _STATUS = 'ORDER_STATUS'

    # ================================================
    #  Initialization
    # ================================================
    def __init__(self, db: IconScoreDatabase, uid: int) -> None:
        self._contract = VarDB(f'{Order._CONTRACT}_{uid}', db, value_type=Address)
        self._amount = VarDB(f'{Order._AMOUNT}_{uid}', db, value_type=int)
        self._provider = VarDB(f'{Order._PROVIDER}_{uid}', db, value_type=Address)
        self._status = VarDB(f'{Order._STATUS}_{uid}', db, value_type=int)

    # ================================================
    #  Private Methods
    # ================================================

    # ================================================
    #  Checks
    # ================================================
    def check_status(self, status: int) -> None:
        Logger.warning('\n   === check_status(%d) => %d' % (status, self._status.get()), TAG)
        if self._status.get() != status:
            raise InvalidOrderStatus

    def check_content(self, contract: Address, amount: int) -> None:
        if (self._contract.get() != contract or self._amount.get() != amount):
            raise InvalidOrderContent

    def check_provider(self, provider: Address) -> None:
        if self._provider.get() != provider:
            raise InvalidOrderProvider(self._provider.get(), provider)

    # ================================================
    #  Public Methods
    # ================================================
    def set_status(self, status: int) -> None:
        self._status.set(status)

    def contract(self) -> Address:
        return self._contract.get()

    def provider(self) -> Address:
        return self._provider.get()

    def amount(self) -> int:
        return self._amount.get()

    def status(self) -> int:
        return self._status.get()

    def fill(self, provider: Address) -> None:
        self._provider.set(provider)
        self._status.set(OrderStatus.FILLED)

    def empty(self) -> None:
        self._provider.remove()
        self._status.set(OrderStatus.EMPTY)

    def serialize(self) -> dict:
        return {
            'contract': self._contract.get(),
            'amount': self._amount.get(),
            'status': Utils.enum_names(OrderStatus)[self._status.get()],
            'provider': self._provider.get()
        }

    def delete(self) -> None:
        self._contract.remove()
        self._amount.remove()
        self._status.remove()
        self._provider.remove()
