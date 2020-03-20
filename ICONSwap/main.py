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
                      or if the trade isn't pending anymore, the funds will be sent back to this address
        """
        # Check if swap exists
        AllSwapComposite(self.db).check_exists(swap_id)
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
        # Check if swap exists
        AllSwapComposite(self.db).check_exists(swap_id)
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

        # Set the swap as successful
        swap.set_status(SwapStatus.SUCCESS)
        swap.set_transaction(self.tx.hash.hex())
        swap.set_timestamp_swap(self.now())
        # Remove the swap from the pending list to the filled list
        PendingSwapAccountComposite(self.db, maker.provider()).remove(swap_id)
        FilledSwapAccountComposite(self.db, maker.provider()).add(swap_id)
        FilledSwapAccountComposite(self.db, taker.provider()).add(swap_id)
        # Set the orders as successful
        maker.set_status(OrderStatus.SUCCESS)
        taker.set_status(OrderStatus.SUCCESS)
        self.SwapSuccessEvent(swap_id)

    def _create_swap(self,
                     maker_contract: Address,
                     maker_amount: int,
                     taker_contract: Address,
                     taker_amount: int,
                     maker_address: Address) -> None:
        self._check_contract(maker_contract)
        self._check_contract(taker_contract)
        self._check_different_contract(maker_contract, taker_contract)
        self._check_amount(maker_amount)
        self._check_amount(taker_amount)

        # Create orders
        maker_id = OrderFactory.create(self.db, maker_contract, maker_amount)
        taker_id = OrderFactory.create(self.db, taker_contract, taker_amount)
        swap_id = SwapFactory.create(self.db, maker_id, taker_id, self.now(), maker_address)
        self.SwapCreatedEvent(swap_id, maker_id, taker_id)

        # Funds has been sent for maker
        maker = Order(self.db, maker_id)
        maker.fill(maker_address)
        self.OrderFilledEvent(maker_id)

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

    def _check_different_contract(self, contract1: Address, contract2: Address) -> None:
        if contract1 == contract2:
            raise InvalidOrderContract

    # ================================================
    #  External methods
    # ================================================
    @payable
    def fallback(self):
        revert("ICONSwap contract doesn't accept direct ICX transfers")

    @catch_error
    @external
    def tokenFallback(self, _from: Address, _value: int, _data: bytes) -> None:
        """
            Create or fill a swap based on a IRC2 token

            :param Address _from: 
                When creating a swap, the maker address;
                When filling a swap, the taker address
            :param int _value:
                The amount of token sent to the swap
            :param bytes _data:
                A UTF-8 encoded JSON string. It needs to follow the structure below:

               Create IRC2 Swap:
                {
                    "action": "create_irc2_swap", 
                    "taker_contract": The taker token contract address being traded with the current token
                    "taker_amount": The amount of taker token required (hex encoded)
                }

                Fill IRC2 Taker Order:
                {
                    "action": "fill_irc2_order",
                    "swap_id": The Swap ID being filled (hex encoded)
                }
        """
        if _data is None or _data == b'None':
            raise InvalidTokenFallbackParams

        params = json_loads(_data.decode('utf-8'))

        if params['action'] == 'create_irc2_swap':
            maker_contract = self.msg.sender
            maker_amount = _value
            maker_address = _from
            taker_contract = Address.from_string(params['taker_contract'])
            taker_amount = int(params['taker_amount'], 16)
            self._create_swap(maker_contract, maker_amount, taker_contract, taker_amount, maker_address)

        elif params['action'] == 'fill_irc2_order':
            taker_contract = self.msg.sender
            taker_amount = _value
            taker_address = _from
            swap_id = int(params['swap_id'], 16)
            self._fill_swap(swap_id, taker_contract, taker_amount, taker_address)

        else:
            raise InvalidTokenFallbackParams

    @catch_error
    @external
    @payable
    def create_icx_swap(self, taker_contract: Address, taker_amount: int) -> None:
        maker_address = self.msg.sender
        maker_amount = self.msg.value
        self._create_swap(ZERO_SCORE_ADDRESS, maker_amount, taker_contract, taker_amount, maker_address)

    @catch_error
    @external
    def cancel_swap(self, swap_id: int) -> None:
        # Check if swap exists
        AllSwapComposite(self.db).check_exists(swap_id)
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
        PendingSwapAccountComposite(self.db, swap.maker_address()).remove(swap_id)

        # Set the orders as unavailable
        maker.set_status(OrderStatus.CANCELLED)
        taker.set_status(OrderStatus.CANCELLED)
        self.SwapCancelledEvent(swap_id)

    @catch_error
    @external
    @payable
    def fill_icx_order(self, swap_id: int) -> None:
        taker_amount = self.msg.value
        taker_address = self.msg.sender
        self._fill_swap(swap_id, ZERO_SCORE_ADDRESS, taker_amount, taker_address)

    @catch_error
    @external(readonly=True)
    def get_swap(self, swap_id: int) -> dict:
        AllSwapComposite(self.db).check_exists(swap_id)
        return Swap(self.db, swap_id).serialize()

    @catch_error
    @external(readonly=True)
    def get_order(self, order_id: int) -> dict:
        OrderComposite(self.db).check_exists(order_id)
        return Order(self.db, order_id).serialize()

    @catch_error
    @external(readonly=True)
    def get_pending_orders_by_address(self, address: Address, offset: int) -> dict:
        return PendingSwapAccountComposite(self.db, address).serialize(self.db, offset, Swap)

    @catch_error
    @external(readonly=True)
    def get_filled_orders_by_address(self, address: Address, offset: int) -> dict:
        return FilledSwapAccountComposite(self.db, address).serialize(self.db, offset, Swap)

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
    def add_whitelist(self, contract: Address) -> None:
        Whitelist(self.db).add(contract)

    @catch_error
    @external
    @only_owner
    def remove_whitelist(self, contract: Address) -> None:
        Whitelist(self.db).remove(contract)
