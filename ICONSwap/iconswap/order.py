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
from ..scorelib.id_factory import *
from ..scorelib.utils import *

EMPTY_ORDER_PROVIDER = Address.from_string("hx0000000000000000000000000000000000000000")

# ================================================
#  Exception
# ================================================


class InvalidOrderContent(Exception):
    pass


class InvalidOrderStatus(Exception):
    pass


class InvalidOrderProvider(Exception):
    pass


class InvalidOrderAmount(Exception):
    pass


class InvalidOrderContract(Exception):
    pass


class OrderFactory(IdFactory):

    _NAME = 'ORDER_FACTORY'

    def __init__(self, db: IconScoreDatabase):
        name = OrderFactory._NAME
        super().__init__(name, db)
        self._name = name
        self._db = db

    def create(self, contract: Address,
               amount: int,
               provider: Address = EMPTY_ORDER_PROVIDER) -> int:

        order_id = self.get_uid()
        order = Order(order_id, self._db)
        order._contract.set(contract)
        order._amount.set(amount)
        order._status.set(OrderStatus.EMPTY)
        order._provider.set(provider)
        return order_id


class OrderStatus:
    EMPTY = 0
    FILLED = 1
    CANCELLED = 2
    SUCCESS = 3


class Order(object):

    _NAME = 'ORDER'

    # ================================================
    #  Initialization
    # ================================================
    def __init__(self, uid: int, db: IconScoreDatabase):
        self._name = Order._NAME
        self._contract = VarDB(f'{self._name}_CONTRACT_{uid}', db, value_type=Address)
        self._amount = VarDB(f'{self._name}_AMOUNT_{uid}', db, value_type=int)
        self._provider = VarDB(f'{self._name}_PROVIDER_{uid}', db, value_type=Address)
        self._status = VarDB(f'{self._name}_STATUS_{uid}', db, value_type=int)
        self._uid = uid
        self._db = db

    # ================================================
    #  Checks
    # ================================================
    def check_status(self, status: int) -> None:
        if self._status.get() != status:
            raise InvalidOrderStatus(
                f'{self._name}_{self._uid}',
                Utils.enum_names(OrderStatus)[self._status.get()],
                Utils.enum_names(OrderStatus)[status])

    def check_content(self, contract: Address, amount: int) -> None:
        if (self._contract.get() != contract or self._amount.get() < amount or amount <= 0):
            raise InvalidOrderContent(self._contract.get(), self._amount.get())

    def check_provider(self, provider: Address) -> None:
        order_provider = self._provider.get()
        if order_provider != EMPTY_ORDER_PROVIDER and order_provider != provider:
            raise InvalidOrderProvider(self._provider.get())

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

    def id(self) -> int:
        return self._uid

    def status(self) -> int:
        return self._status.get()

    def fill(self, provider: Address) -> None:
        self._provider.set(provider)
        self._status.set(OrderStatus.FILLED)

    def partial_fill(self, amount: int) -> None:
        self._amount.set(self._amount.get() - amount)

    def empty(self) -> None:
        self._provider.set(EMPTY_ORDER_PROVIDER)
        self._status.set(OrderStatus.EMPTY)

    def serialize(self) -> dict:
        return {
            'id': self._uid,
            'contract': str(self._contract.get()),
            'amount': self._amount.get(),
            'status': Utils.enum_names(OrderStatus)[self._status.get()],
            'provider': str(self._provider.get())
        }

    def __delete__(self) -> None:
        self._contract.remove()
        self._amount.remove()
        self._status.remove()
        self._provider.remove()
