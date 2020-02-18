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
from .checks import *
from .utils import *
from .version import *
from .swap import *
from .order import *
from .whitelist import *
from .irc2_interface import *
from .consts import *


class ICONSwap(IconScoreBase):
    """ ICONSwap SCORE Base implementation """

    # ================================================
    #  Event Logs
    # ================================================
    @eventlog(indexed=1)
    def SwapCreatedEvent(self, swapid: int, o1id: int, o2id: int) -> None:
        pass

    @eventlog(indexed=1)
    def SwapSuccessEvent(self, swapid: int) -> None:
        pass

    @eventlog(indexed=1)
    def SwapCancelledEvent(self, swapid: int) -> None:
        pass

    @eventlog(indexed=1)
    def OrderFilledEvent(self, orderid: int) -> None:
        pass

    @eventlog(indexed=1)
    def OrderTransferedEvent(self, orderid: int, contract: Address, amount: int, provider: Address) -> None:
        pass

    @eventlog(indexed=1)
    def OrderRefundedEvent(self, orderid: int) -> None:
        pass

    # ================================================
    #  Initialization
    # ================================================
    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

    def on_install(self) -> None:
        super().on_install()
        Version.set(self.db, VERSION)

    def on_update(self) -> None:
        super().on_update()
        Version.set(self.db, VERSION)

    # ================================================
    #  Internal methods
    # ================================================
    def _transfer_order(self, order: Order, dest: Address) -> None:
        if self._is_icx(order):
            self.icx.transfer(dest, order.amount())
        else:
            irc2 = self.create_interface_score(order.contract(), IRC2Interface)
            irc2.transfer(dest, order.amount())

    def _refund_order(self, order: Order) -> None:
        Logger.warning('\n   === _refund_order(%d => %s)' % (order.amount(), order.provider()))
        self._transfer_order(order, order.provider())
        order.empty()

    def _is_icx(self, order: Order) -> bool:
        return order.contract() == ZERO_SCORE_ADDRESS

    def _fulfill_order(self, uid: int, contract: Address, amount: int, provider: Address) -> None:
        """
            uid: The order UID
            contract: The token governance contract address.
                      For ICX, it should be ZERO_SCORE_ADDRESS.
                      It needs to match the order or it will fail.
            amount: The amount of token traded.
                    It needs to match exactly the order amount or it will fail.
            provider: The address of the account providing the funds. If an error occurs
                      or if the trade is cancelled, the funds will be sent back to this address
        """
        Logger.warning('\n   === fulfill_order(%d, %s, %d, %s)' % (uid, str(contract), amount, str(provider)), TAG)
        OrderComposite(self.db).check_exists(uid)
        order = Order(self.db, uid)
        order.check_status(OrderStatus.EMPTY)
        order.check_content(contract, amount)
        order.fill(provider)
        self.OrderFilledEvent(uid)

    # ================================================
    #  Checks
    # ================================================
    def _check_orders_provider(self, o1: Order, o2: Order, provider: Address) -> None:
        """ Check if emitter is one of the provider """
        if o1.provider() != provider and o2.provider() != provider:
            raise InvalidOrderProvider

    def _check_amount(self, amount: int) -> None:
        if amount == 0:
            raise InvalidOrderAmount

    def _check_contract(self, address: Address) -> None:
        if not address.is_contract:
            raise InvalidOrderContract
        Whitelist(self.db).check_exists(address)

    # ================================================
    #  External methods
    # ================================================
    @catch_error
    @external
    def create_swap(self, contract1: Address, amount1: int, contract2: Address, amount2: int) -> None:
        Logger.warning('\n   === create_swap(%s, %d, %s, %d)' % (str(contract1), amount1, str(contract2), amount2), TAG)
    
        self._check_contract(contract1)
        self._check_contract(contract2)
        self._check_amount(amount1)
        self._check_amount(amount2)

        # Create orders
        uid1 = OrderFactory.create(self.db, contract1, amount1)
        uid2 = OrderFactory.create(self.db, contract2, amount2)
        swap = SwapFactory.create(self.db, uid1, uid2, self.now(), self.msg.sender)
        self.SwapCreatedEvent(swap, uid1, uid2)

    @catch_error
    @external
    def cancel_swap(self, swapid: int) -> None:
        Logger.warning('\n   === cancel_swap(%d)' % swapid)
        SwapComposite(self.db).check_exists(swapid)

        # Must be pending
        swap = Swap(self.db, swapid)
        swap.check_status(SwapStatus.PENDING)

        # Only the swap author can cancel it
        swap.check_author(self.msg.sender)

        # Get the orders associated with the swap
        oid1, oid2 = swap.get_orders()
        o1 = Order(self.db, oid1)
        o2 = Order(self.db, oid2)

        # Refund if filled
        if o1.status() == OrderStatus.FILLED:
            self._refund_order(o1)
            self.OrderRefundedEvent(oid1)

        if o2.status() == OrderStatus.FILLED:
            self._refund_order(o2)
            self.OrderRefundedEvent(oid2)

        # Set the swap status as unavailable
        swap.set_status(SwapStatus.CANCELLED)
        o1.set_status(OrderStatus.CANCELLED)
        o2.set_status(OrderStatus.CANCELLED)
        self.SwapCancelledEvent(swapid)

    @catch_error
    @external
    def refund_order(self, orderid: int) -> None:
        Logger.warning('\n   === refund_order(%d)' % orderid)
        OrderComposite(self.db).check_exists(orderid)

        # Must be filled
        order = Order(self.db, orderid)
        order.check_status(OrderStatus.FILLED)

        # Caller must be provider
        order.check_provider(self.msg.sender)

        # OK
        self._refund_order(order)
        self.OrderRefundedEvent(orderid)

    @catch_error
    @external
    def do_swap(self, swapid: int) -> None:
        Logger.warning('\n   === do_swap(%d)' % swapid, TAG)

        SwapComposite(self.db).check_exists(swapid)
        swap = Swap(self.db, swapid)

        # Check if the swap is pending
        swap.check_status(SwapStatus.PENDING)

        # Check if the orders are filled
        oid1, oid2 = swap.get_orders()
        o1 = Order(self.db, oid1)
        o1.check_status(OrderStatus.FILLED)
        o2 = Order(self.db, oid2)
        o2.check_status(OrderStatus.FILLED)

        # Check if emitter is one of the provider
        self._check_orders_provider(o1, o2, self.msg.sender)

        # OK: trade the tokens
        self._transfer_order(o1, o2.provider())
        self.OrderTransferedEvent(oid1, o1.contract(), o1.amount(), o2.provider())
        self._transfer_order(o2, o1.provider())
        self.OrderTransferedEvent(oid2, o2.contract(), o2.amount(), o1.provider())

        swap.set_status(SwapStatus.SUCCESS)
        o1.set_status(OrderStatus.SUCCESS)
        o2.set_status(OrderStatus.SUCCESS)
        self.SwapSuccessEvent(swapid)

    @catch_error
    @external
    def tokenFallback(self, _from: Address, _value: int, _data: bytes) -> None:
        Logger.warning('\n   === tokenFallback(%s, %d)' % (str(_from), _value), TAG)
        if _data is None or _data == b'None':
            raise InvalidOrderId

        uid = int.from_bytes(_data, 'big')
        self._fulfill_order(uid, self.msg.sender, _value, _from)

    @catch_error
    @external
    @payable
    def fulfill_icx_order(self, orderid: int) -> None:
        Logger.warning('\n   === fulfill_icx_order(%d)' % orderid, TAG)
        provider = self.msg.sender
        amount = self.msg.value
        self._fulfill_order(orderid, ZERO_SCORE_ADDRESS, amount, provider)

    @catch_error
    @external(readonly=True)
    def get_swap(self, swapid: int) -> dict:
        return Swap(self.db, swapid).serialize()

    @catch_error
    @external(readonly=True)
    def get_order(self, orderid: int) -> dict:
        return Order(self.db, orderid).serialize()

    @catch_error
    @external(readonly=True)
    def get_whitelist(self) -> list:
        return Whitelist(self.db).serialize()

    # ================================================
    #  Operator methods
    # ================================================
    @catch_error
    @external
    @only_owner
    def add_whitelist(self, contract: Address):
        Whitelist(self.db).add(contract)

    @catch_error
    @external
    @only_owner
    def remove_whitelist(self, contract: Address):
        Whitelist(self.db).remove(contract)
