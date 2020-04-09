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
from .version import *
from .consts import *
from .maintenance import *
from .iconswap.system import *
from .iconswap.market import *
from .iconswap.account import *
from .iconswap.swap import *
from .iconswap.order import *
from .iconswap.whitelist import *
from .interfaces.irc2 import *


class InvalidTokenFallbackParams(Exception):
    pass


class ICONSwap(IconScoreBase):
    """ ICONSwap SCORE Base implementation """

    _NAME = 'ICONSwap'

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
        SCOREMaintenance(self.db).disable()
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

    def _get_market_last_filled_swap(self, pair: str) -> Swap:
        filled_swaps = MarketFilledSwapDB(tuple(pair.split('/')), self.db).select(0)
        if filled_swaps:
            return Swap(filled_swaps[0][1], self.db)

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
        SystemSwapDB(self.db).check_exists(swap_id)
        swap = Swap(swap_id, self.db)

        # Check if the swap is pending
        swap.check_status(SwapStatus.PENDING)

        # Check if maker order is filled
        maker, taker = swap.get_orders()
        maker.check_status(OrderStatus.FILLED)

        # Check if taker order is empty
        taker.check_status(OrderStatus.EMPTY)

        # Check taker order content
        taker.check_content(taker_contract, taker_amount)

        # --- OK from here

        # Fill the order
        taker.fill(taker_address)

        # Trigger events
        self.OrderFilledEvent(taker.id())

        # Both orders are filled : do the swap
        self._do_swap(swap_id)

    def _do_swap(self, swap_id: int) -> None:
        # Check if swap exists
        SystemSwapDB(self.db).check_exists(swap_id)
        swap = Swap(swap_id, self.db)

        # Check if the swap is pending
        swap.check_status(SwapStatus.PENDING)

        # Check if the orders are filled
        maker, taker = swap.get_orders()
        maker.check_status(OrderStatus.FILLED)
        taker.check_status(OrderStatus.FILLED)

        # --- OK from here
        pair = (maker.contract(), taker.contract())

        # Trade the tokens
        self._transfer_order(maker, taker.provider())
        self._transfer_order(taker, maker.provider())
        self.OrderTransferedEvent(maker.id(), maker.contract(), maker.amount(), taker.provider())
        self.OrderTransferedEvent(taker.id(), taker.contract(), taker.amount(), maker.provider())

        # Set the swap as successful
        swap.set_status(SwapStatus.SUCCESS)
        swap.set_transaction(self.tx.hash.hex())
        swap.set_timestamp_swap(self.now())

        # Remove the swap from the pending lists
        AccountPendingSwapDB(maker.provider(), self.db).remove(swap_id)
        MarketPendingSwapDB(pair, self.db).remove(swap_id)

        # Add the swap to filled lists
        AccountFilledSwapDB(maker.provider(), self.db).add(swap_id)
        AccountFilledSwapDB(taker.provider(), self.db).add(swap_id)
        MarketFilledSwapDB(pair, self.db).prepend(swap_id)

        # Set the orders as successful
        maker.set_status(OrderStatus.SUCCESS)
        taker.set_status(OrderStatus.SUCCESS)

        # Trigger events
        self.SwapSuccessEvent(swap_id)

    def _create_swap(self,
                     maker_contract: Address,
                     maker_amount: int,
                     taker_contract: Address,
                     taker_amount: int,
                     maker_address: Address) -> None:
        # Input checks
        self._check_contract(maker_contract)
        self._check_contract(taker_contract)
        self._check_different_contract(maker_contract, taker_contract)
        self._check_amount(maker_amount)
        self._check_amount(taker_amount)

        # --- OK from here
        pair = (maker_contract, taker_contract)

        # Create orders and swap
        order_factory = OrderFactory(self.db)
        maker_id = order_factory.create(maker_contract, maker_amount)
        taker_id = order_factory.create(taker_contract, taker_amount)
        swap_id = SwapFactory(self.db).create(maker_id, taker_id, self.now(), maker_address)

        # Add to DB
        system_order_db = SystemOrderDB(self.db)
        system_order_db.add(maker_id)
        system_order_db.add(taker_id)

        MarketPendingSwapDB(pair, self.db).add(swap_id)

        SystemSwapDB(self.db).add(swap_id)
        AccountPendingSwapDB(maker_address, self.db).add(swap_id)

        # Create the market pair if it didn't exist yet
        market_pairs_db = MarketPairsDB(self.db)
        if not pair in market_pairs_db:
            # The max pairs count here is combination(whitelist_count, 2) (nCr, r=2)
            # It should be fine as long as the number of tokens is < 50 (1225 iterations)
            market_pairs_db.add(pair)

        # Funds have been sent for maker
        maker = Order(maker_id, self.db)
        maker.fill(maker_address)

        # Trigger events
        self.SwapCreatedEvent(swap_id, maker_id, taker_id)
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
    @check_maintenance
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
    @check_maintenance
    @external
    @payable
    def create_icx_swap(self, taker_contract: Address, taker_amount: int) -> None:
        maker_address = self.msg.sender
        maker_amount = self.msg.value
        self._create_swap(ZERO_SCORE_ADDRESS, maker_amount, taker_contract, taker_amount, maker_address)

    def _cancel_swap(self, swap: Swap) -> None:
        # Swap must be pending
        swap.check_status(SwapStatus.PENDING)

        # -- OK from here
        # Get the orders associated with the swap
        maker, taker = swap.get_orders()
        pair = (maker.contract(), taker.contract())
        maker_address = maker.provider()

        # Refund if filled
        if maker.status() == OrderStatus.FILLED:
            self._refund_order(maker)
            self.OrderRefundedEvent(maker.id())

        if taker.status() == OrderStatus.FILLED:
            self._refund_order(taker)
            self.OrderRefundedEvent(taker.id())

        # Set the swap status as unavailable
        swap.set_status(SwapStatus.CANCELLED)
        swap.set_transaction(self.tx.hash.hex())

        # Remove swap from lists
        AccountPendingSwapDB(maker_address, self.db).remove(swap.id())
        MarketPendingSwapDB(pair, self.db).remove(swap.id())

        # Set the orders as unavailable
        maker.set_status(OrderStatus.CANCELLED)
        taker.set_status(OrderStatus.CANCELLED)
        self.SwapCancelledEvent(swap.id())

    @catch_error
    @check_maintenance
    @external
    def cancel_swap(self, swap_id: int) -> None:
        # Check if swap exists
        SystemSwapDB(self.db).check_exists(swap_id)
        swap = Swap(swap_id, self.db)

        # Only the maker can cancel the swap
        swap.check_maker_address(self.msg.sender)

        self._cancel_swap(swap)

    @catch_error
    @check_maintenance
    @external
    @payable
    def fill_icx_order(self, swap_id: int) -> None:
        taker_amount = self.msg.value
        taker_address = self.msg.sender
        self._fill_swap(swap_id, ZERO_SCORE_ADDRESS, taker_amount, taker_address)

    @catch_error
    @external(readonly=True)
    def get_market_info(self, offset: int) -> dict:

        tokens = {}
        pairs = []

        # Fill the tokens cache info
        for pair in MarketPairsDB(self.db).select(offset):
            pairs.append({"name": pair})
            spots = pair.split('/')

            for spot in spots:
                if spot in tokens:
                    # Already in the cache
                    continue

                if spot == str(ZERO_SCORE_ADDRESS):
                    tokens[spot] = {
                        "name": "ICX",
                        "symbol": "ICX",
                        "decimals": 18
                    }
                else:
                    address = Address.from_string(spot)
                    irc2 = self.create_interface_score(address, IRC2Interface)
                    tokens[spot] = {
                        "name": irc2.name(),
                        "symbol": irc2.symbol(),
                        "decimals": irc2.decimals()
                    }

        # build the pairs info
        for pair in pairs:
            pair_tuple = tuple(pair['name'].split('/'))
            pair['swaps_pending_count'] = len(MarketPendingSwapDB(pair_tuple, self.db))
            last_swap = self._get_market_last_filled_swap(pair['name'])
            if last_swap:
                # most recent swap
                orders = last_swap.get_orders()
                if MarketPairsDB.is_buyer(pair_tuple, orders[0]):
                    pair['last_price'] = last_swap.get_inverted_price()
                else:
                    pair['last_price'] = last_swap.get_price()
            else:
                pair['last_price'] = float(0)

        return {
            "pairs": pairs,
            "tokens": tokens
        }

    @catch_error
    @external(readonly=True)
    def get_market_buyers_pending_swaps(self, pair: str, offset: int) -> list:
        pending_swaps = MarketPendingSwapDB(tuple(pair.split('/')), self.db)
        return [
            Swap(swap_id, self.db).serialize()
            for _, swap_id in pending_swaps.buyers().select(offset)
        ]

    @catch_error
    @external(readonly=True)
    def get_market_sellers_pending_swaps(self, pair: str, offset: int) -> list:
        pending_swaps = MarketPendingSwapDB(tuple(pair.split('/')), self.db)
        return [
            Swap(swap_id, self.db).serialize()
            for _, swap_id in pending_swaps.sellers().select(offset)
        ]

    @catch_error
    @external(readonly=True)
    def get_market_last_filled_swap(self, pair: str) -> dict:
        last_swap = self._get_market_last_filled_swap(pair)
        return last_swap.serialize() if last_swap else {}

    @catch_error
    @external(readonly=True)
    def get_market_filled_swaps(self, pair: str, offset: int) -> list:
        filled_swaps = MarketFilledSwapDB(tuple(pair.split('/')), self.db)
        return [
            Swap(swap_id, self.db).serialize()
            for _, swap_id in filled_swaps.select(offset)
        ]

    @catch_error
    @external(readonly=True)
    def get_account_pending_swaps(self, address: Address, offset: int) -> list:
        pending_swaps = AccountPendingSwapDB(address, self.db)
        return [
            Swap(swap_id, self.db).serialize()
            for swap_id in pending_swaps.select(offset)
        ]

    @catch_error
    @external(readonly=True)
    def get_account_filled_swaps(self, address: Address, offset: int) -> list:
        filled_swaps = AccountFilledSwapDB(address, self.db)
        return [
            Swap(swap_id, self.db).serialize()
            for swap_id in filled_swaps.select(offset)
        ]

    @catch_error
    @external(readonly=True)
    def get_swap(self, swap_id: int) -> dict:
        SystemSwapDB(self.db).check_exists(swap_id)
        return Swap(swap_id, self.db).serialize()

    @catch_error
    @external(readonly=True)
    def get_order(self, order_id: int) -> dict:
        SystemOrderDB(self.db).check_exists(order_id)
        return Order(order_id, self.db).serialize()

    @catch_error
    @external(readonly=True)
    def get_whitelist(self, offset: int) -> list:
        whitelist = Whitelist(self.db).select(offset)
        return [contract for contract in whitelist]

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

    @catch_error
    @external
    @only_owner
    def cancel_swap_admin(self, swap_id: int) -> None:
        # Check if swap exists
        SystemSwapDB(self.db).check_exists(swap_id)
        swap = Swap(swap_id, self.db)
        self._cancel_swap(swap)

    @catch_error
    @external
    @only_owner
    def set_maintenance_mode(self, mode: int) -> None:
        if (mode == SCOREMaintenanceMode.MAINTENANCE_ENABLED
                or mode == SCOREMaintenanceMode.MAINTENANCE_DISABLED):
            self._maintenance_mode.set(mode)
