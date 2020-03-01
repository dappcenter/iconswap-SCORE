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


class InvalidTokenFallbackParams(Exception):
    pass


class ICONSwap(IconScoreBase):
    """ ICONSwap SCORE Base implementation """

    # ================================================
    #  Event Logs
    # ================================================
    @eventlog(indexed=1)
    def SwapCreatedEvent(self, swap_id: int, maker_id: int, taker_id: int) -> None:
        pass

    @eventlog(indexed=1)
    def SwapSuccessEvent(self, swap_id: int) -> None:
        pass

    @eventlog(indexed=1)
    def SwapCancelledEvent(self, swap_id: int) -> None:
        pass

    @eventlog(indexed=1)
    def OrderFilledEvent(self, order_id: int) -> None:
        pass

    @eventlog(indexed=1)
    def OrderTransferedEvent(self, order_id: int, contract: Address, amount: int, provider: Address) -> None:
        pass

    @eventlog(indexed=1)
    def OrderRefundedEvent(self, order_id: int) -> None:
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

    def _fill_swap(self, swap_id: int, taker_contract: Address, taker_amount: int, taker_address: Address) -> None:
        """
            swap_id: The swap UID
            taker_contract: The token governance taker_contract address.
                      For ICX, it should be ZERO_SCORE_ADDRESS.
                      It needs to match the order or it will fail.
            taker_amount: The amount of token traded.
                    It needs to match exactly the taker order amount or it will fail.
            taker_address: The address of the account providing the funds. If an error occurs
                      or if the trade isn't opened anymore, the funds will be sent back to this address
        """
        Logger.warning('\n   === _fill_swap(%d, %s, %d, %s)' % (swap_id, taker_contract, taker_amount, taker_address), TAG)

        # Check if swap exists
        SwapComposite(self.db).check_exists(swap_id)
        swap = Swap(self.db, swap_id)

        # Check if the swap is pending
        swap.check_status(SwapStatus.PENDING)

        # Check if maker order is filled
        maker_id, taker_id = swap.get_orders()
        maker = Order(self.db, maker_id)
        taker = Order(self.db, taker_id)
        maker.check_status(OrderStatus.FILLED)

        # Check if taker order is empty
        taker = Order(self.db, taker_id)
        taker.check_status(OrderStatus.EMPTY)

        # Check taker order content
        taker.check_content(taker_contract, taker_amount)

        # OK!
        taker.fill(taker_address)
        self.OrderFilledEvent(taker_id)

        # Both orders are filled : do the swap
        self._do_swap(swap_id)

    def _do_swap(self, swap_id: int) -> None:
        Logger.warning('\n   === do_swap(%d)' % swap_id, TAG)

        # Check if swap exists
        SwapComposite(self.db).check_exists(swap_id)
        swap = Swap(self.db, swap_id)

        # Check if the swap is pending
        swap.check_status(SwapStatus.PENDING)

        # Check if the orders are filled
        maker_id, taker_id = swap.get_orders()
        maker = Order(self.db, maker_id)
        taker = Order(self.db, taker_id)
        maker.check_status(OrderStatus.FILLED)
        taker.check_status(OrderStatus.FILLED)

        # OK: trade the tokens
        self._transfer_order(maker, taker.provider())
        self._transfer_order(taker, maker.provider())
        self.OrderTransferedEvent(maker_id, maker.contract(), maker.amount(), taker.provider())
        self.OrderTransferedEvent(taker_id, taker.contract(), taker.amount(), maker.provider())

        swap.set_status(SwapStatus.SUCCESS)
        swap.set_transaction(self.tx.hash.hex())
        maker.set_status(OrderStatus.SUCCESS)
        taker.set_status(OrderStatus.SUCCESS)
        self.SwapSuccessEvent(swap_id)

    # ================================================
    #  Checks
    # ================================================
    def _check_amount(self, amount: int) -> None:
        if amount == 0:
            raise InvalidOrderAmount

    def _check_contract(self, address: Address) -> None:
        if not address.is_contract:
            raise InvalidOrderContract
        Whitelist(self.db).check_exists(address)

    def _create_swap(self,
                     maker_contract: Address,
                     maker_amount: int,
                     taker_contract: Address,
                     taker_amount: int,
                     maker_address: Address) -> None:
        Logger.warning('\n   === create_swap(%s, %d, %s, %d)' % (maker_contract, maker_amount, taker_contract, taker_amount), TAG)

        self._check_contract(maker_contract)
        self._check_contract(taker_contract)
        self._check_amount(maker_amount)
        self._check_amount(taker_amount)

        # Create orders
        maker_id = OrderFactory.create(self.db, maker_contract, maker_amount)
        taker_id = OrderFactory.create(self.db, taker_contract, taker_amount)
        swap_id = SwapFactory.create(self.db, maker_id, taker_id, self.now(), self.msg.sender)
        self.SwapCreatedEvent(swap_id, maker_id, taker_id)

        # Funds has been sent for maker
        maker = Order(self.db, maker_id)
        maker.fill(maker_address)
        self.OrderFilledEvent(maker_id)

    # ================================================
    #  External methods
    # ================================================
    @catch_error
    @external
    def tokenFallback(self, _from: Address, _value: int, _data: bytes) -> None:
        Logger.warning('\n   === tokenFallback(%s, %d)' % (str(_from), _value), TAG)

        if _data is None or _data == b'None':
            raise InvalidTokenFallbackParams

        params = json_loads(_data.decode('utf-8'))

        if params['action'] == 'create_irc2_swap':
            maker_contract = self.msg.sender
            maker_amount = _value
            maker_address = _from
            taker_contract = Address.from_string(params['taker_contract'])
            taker_amount = params['taker_amount']
            self._create_swap(maker_contract, maker_amount, taker_contract, taker_amount, maker_address)

        elif params['action'] == 'fill_irc2_order':
            taker_contract = self.msg.sender
            taker_amount = _value
            taker_address = _from
            swap_id = params['swap_id']
            self._fill_swap(swap_id, taker_contract, taker_amount, taker_address)

        else:
            raise InvalidTokenFallbackParams

    @catch_error
    @external
    @payable
    def create_icx_swap(self, taker_contract: Address, taker_amount: int) -> None:
        Logger.warning('\n   === create_icx_swap(%s, %d)' % (taker_contract, taker_amount), TAG)
        maker_address = self.msg.sender
        maker_amount = self.msg.value
        self._create_swap(ZERO_SCORE_ADDRESS, maker_amount, taker_contract, taker_amount, maker_address)

    @catch_error
    @external
    def cancel_swap(self, swap_id: int) -> None:
        Logger.warning('\n   === cancel_swap(%d)' % swap_id)

        # Check if swap exists
        SwapComposite(self.db).check_exists(swap_id)
        swap = Swap(self.db, swap_id)

        # Only the maker can cancel the swap
        swap.check_maker_address(self.msg.sender)

        # Swap must be pending
        swap.check_status(SwapStatus.PENDING)

        # Get the orders associated with the swap
        maker_id, taker_id = swap.get_orders()
        maker = Order(self.db, maker_id)
        taker = Order(self.db, taker_id)

        # Refund if filled
        if maker.status() == OrderStatus.FILLED:
            self._refund_order(maker)
            self.OrderRefundedEvent(maker_id)

        if taker.status() == OrderStatus.FILLED:
            self._refund_order(taker)
            self.OrderRefundedEvent(taker_id)

        # Set the swap status as unavailable
        swap.set_status(SwapStatus.CANCELLED)
        swap.set_transaction(self.tx.hash.hex())
        maker.set_status(OrderStatus.CANCELLED)
        taker.set_status(OrderStatus.CANCELLED)
        self.SwapCancelledEvent(swap_id)

    @catch_error
    @external
    @payable
    def fill_icx_order(self, swap_id: int) -> None:
        Logger.warning('\n   === fill_icx_order(%d)' % swap_id, TAG)
        taker_amount = self.msg.value
        taker_address = self.msg.sender
        self._fill_swap(swap_id, ZERO_SCORE_ADDRESS, taker_amount, taker_address)

    @catch_error
    @external(readonly=True)
    def get_swap(self, swap_id: int) -> dict:
        SwapComposite(self.db).check_exists(swap_id)
        return Swap(self.db, swap_id).serialize()

    @catch_error
    @external(readonly=True)
    def get_order(self, order_id: int) -> dict:
        OrderComposite(self.db).check_exists(order_id)
        return Order(self.db, order_id).serialize()

    @catch_error
    @external(readonly=True)
    def get_pending_swaps(self) -> dict:
        return SwapComposite(self.db).serialize(self.db, Swap, SwapComposite.pending)

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
