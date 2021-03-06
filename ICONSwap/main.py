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


class InvalidCallParameters(Exception):
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
    def SwapCleanupEvent(self, swap_id: int) -> None:
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

    @eventlog
    def ShowException(self, exception: str):
        pass

    # ================================================
    #  Initialization
    # ================================================
    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._iconbet_wages = VarDB(f'{ICONSwap._NAME}_ICONBET_WAGES', db, value_type=Address)

    def on_install(self) -> None:
        super().on_install()
        SCOREMaintenance(self.db).disable()
        Version(self.db).update(VERSION)
        self._iconbet_wages.set(ICONBET_WAGES_ADDRESS)

    def on_update(self) -> None:
        super().on_update()

        version = Version(self.db)

        if version.is_less_than_target_version('0.4.0'):
            self._migrate_v0_4_0()

        if version.is_less_than_target_version('0.4.1'):
            self._migrate_v0_4_1()

        if version.is_less_than_target_version('0.4.2'):
            self._migrate_v0_4_2()

        version.update(VERSION)

    # ================================================
    #  Migration methods
    # ================================================
    def _migrate_v0_4_0(self) -> None:
        # 'None' taker order provider field needs to be updated to EMPTY_ORDER_PROVIDER
        for swap_id in SystemSwapDB(self.db):
            swap = Swap(swap_id, self.db)
            maker, taker = swap.get_orders()
            if taker.provider() == None and taker.status() in [OrderStatus.EMPTY, OrderStatus.CANCELLED]:
                taker._provider.set(EMPTY_ORDER_PROVIDER)

    def _migrate_v0_4_1(self) -> None:
        # Market sellers should be reversed for all markets
        for pair in MarketPairsDB(self.db):
            pair = pair.split('/')
            # Get the list of selling pending swaps
            pendings = list(MarketPendingSwapDB(pair, self.db).sellers())

            # Clear the DB
            MarketPendingSwapDB(pair, self.db).sellers().clear()

            # Add them again to the DB in the correct order
            for old_swap in pendings:
                MarketPendingSwapDB(pair, self.db).add(old_swap)

    def _migrate_v0_4_2(self) -> None:
        self._iconbet_wages.set(ICONBET_WAGES_ADDRESS)

    # ================================================
    #  Internal methods
    # ================================================
    def _transfer_order(self, order: Order, dest: Address) -> None:
        return self._transfer_funds(order.contract(), order.amount(), dest)

    def _transfer_funds(self, contract: Address, amount: int, dest: Address) -> None:
        if self._is_contract_icx(contract):
            self.icx.transfer(dest, amount)
        else:
            irc2 = self.create_interface_score(contract, IRC2Interface)
            irc2.transfer(dest, amount)

    def _get_market_last_filled_swap(self, pair: tuple) -> Swap:
        filled_swaps = MarketFilledSwapDB(pair, self.db).select(0)
        if filled_swaps:
            return Swap(filled_swaps[0], self.db)

    def _refund_order(self, order: Order) -> None:
        self._transfer_order(order, order.provider())
        order.empty()

    def _is_icx(self, order: Order) -> bool:
        return self._is_contract_icx(order.contract())

    def _is_contract_icx(self, contract: Address) -> bool:
        return contract == ZERO_SCORE_ADDRESS

    def _is_cleanable(self, maker_contract: Address, maker_amount: int) -> bool:
        if self._is_contract_icx(maker_contract):
            maker_decimals = ICX_TOKEN_DECIMALS
        else:
            maker_decimals = self.create_interface_score(maker_contract, IRC2Interface).decimals()

        return 0 < maker_amount < (10**maker_decimals)

    def _is_order_cleanable(self, order: Order) -> bool:
        return self._is_cleanable(order.contract(), order.amount())

    def _cleanup_swap(self, swap: Swap) -> None:
        maker, taker = swap.get_orders()

        # Low swap amount, cancel the swap back to the maker
        if (self._is_order_cleanable(maker) or self._is_order_cleanable(taker)):
            Logger.warning(f"LOW SWAP, CANCEL : {swap.serialize()}")
            self._cancel_swap(swap)
            self.SwapCleanupEvent(swap.id())

    def _do_partial_fill_swap(self, swap: Swap, taker_partial_amount: int, taker_address: Address) -> None:
        maker, taker = swap.get_orders()

        # Split the swaps
        maker_partial_amount = (taker_partial_amount * maker.amount()) // taker.amount()

        # Create a partial swap and fill it
        partial_swap = self._create_swap(maker.contract(),
                                         maker_partial_amount,
                                         taker.contract(),
                                         taker_partial_amount,
                                         maker.provider(),
                                         taker_address)
        if partial_swap:
            self._do_full_fill_swap(partial_swap, taker_address)
            # Adjust the amount of the remaining existing swap
            maker.partial_fill(maker_partial_amount)
            taker.partial_fill(taker_partial_amount)

        # Cleanup decimals if needed
        self._cleanup_swap(swap)

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

        # Check if taker address is correct, if filled
        taker.check_provider(taker_address)

        # Check taker order content
        taker.check_content(taker_contract, taker_amount)

        # --- OK from here
        if taker_amount < taker.amount():
            self._do_partial_fill_swap(swap, taker_amount, taker_address)
        else:
            self._do_full_fill_swap(swap, taker_address)

    def _do_full_fill_swap(self, swap: Swap, taker_address: Address) -> None:
        # Swap needs to be checked for private *before* the taker order is filled
        is_private_swap = swap.is_private()
        maker, taker = swap.get_orders()

        # Fill the taker order
        taker.fill(taker_address)
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
        AccountPendingSwapDB(maker.provider(), self.db).remove(swap.id())
        AccountPairPendingSwapDB(maker.provider(), pair, self.db).remove(swap.id())
        if not is_private_swap:
            MarketPendingSwapDB(pair, self.db).remove(swap.id())

        # Add the swap to filled lists
        AccountFilledSwapDB(maker.provider(), self.db).prepend(swap.id())
        AccountFilledSwapDB(taker.provider(), self.db).prepend(swap.id())
        AccountPairFilledSwapDB(maker.provider(), pair, self.db).prepend(swap.id())
        AccountPairFilledSwapDB(taker.provider(), pair, self.db).prepend(swap.id())
        if not is_private_swap:
            MarketFilledSwapDB(pair, self.db).prepend(swap.id())

        # Set the orders as successful
        maker.set_status(OrderStatus.SUCCESS)
        taker.set_status(OrderStatus.SUCCESS)

        # Trigger events
        self.OrderFilledEvent(taker.id())
        self.SwapSuccessEvent(swap.id())

    def _create_swap(self,
                     maker_contract: Address,
                     maker_amount: int,
                     taker_contract: Address,
                     taker_amount: int,
                     maker_address: Address,
                     taker_address: Address) -> Swap:
        # Input checks
        self._check_contract(maker_contract)
        self._check_contract(taker_contract)
        self._check_different_contract(maker_contract, taker_contract)
        self._check_amount(maker_amount)
        self._check_amount(taker_amount)

        # Not enough for creating a swap, send back the funds to the maker
        if self._is_cleanable(maker_contract, maker_amount) or \
           self._is_cleanable(taker_contract, taker_amount):
            self._transfer_funds(maker_contract, maker_amount, maker_address)
            return None

        # --- OK from here
        pair = (maker_contract, taker_contract)

        # Create orders and swap
        order_factory = OrderFactory(self.db)
        maker_id = order_factory.create(maker_contract, maker_amount)
        taker_id = order_factory.create(taker_contract, taker_amount, taker_address)
        swap_id = SwapFactory(self.db).create(maker_id, taker_id, self.now(), maker_address)
        swap = Swap(swap_id, self.db)

        # Add to DBs
        system_order_db = SystemOrderDB(self.db)
        system_order_db.add(maker_id)
        system_order_db.add(taker_id)
        SystemSwapDB(self.db).add(swap_id)

        if not swap.is_private():
            # Market is only for public swaps
            MarketPendingSwapDB(pair, self.db).add(swap_id)

            # Create the market pair if it didn't exist yet
            market_pairs_db = MarketPairsDB(self.db)
            if not pair in market_pairs_db:
                # The max pairs count here is combination(whitelist_count, 2) (nCr, r=2)
                # It should be fine as long as the number of tokens is < 50 (1225 iterations)
                market_pairs_db.add(pair)

        AccountPendingSwapDB(maker_address, self.db).prepend(swap_id)
        AccountPairPendingSwapDB(maker_address, pair, self.db).prepend(swap_id)

        # Funds have been sent for maker
        maker = Order(maker_id, self.db)
        maker.fill(maker_address)

        # Trigger events
        self.SwapCreatedEvent(swap_id, maker_id, taker_id)
        self.OrderFilledEvent(maker_id)

        return swap

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
        AccountPairPendingSwapDB(maker_address, pair, self.db).remove(swap.id())

        if not swap.is_private():
            # Market is only for public swaps
            MarketPendingSwapDB(pair, self.db).remove(swap.id())

        # Set the orders as unavailable
        maker.set_status(OrderStatus.CANCELLED)
        taker.set_status(OrderStatus.CANCELLED)
        self.SwapCancelledEvent(swap.id())

    def _market_create_limit_irc2_order(self, _value: int, _from: Address, params: dict) -> None:
        taker_amount = int(params['taker_amount'], 16)
        taker_contract = Address.from_string(params['taker_contract'])
        maker_contract = self.msg.sender
        maker_amount = _value
        maker_address = _from
        self._market_create_limit_order(taker_contract, taker_amount, maker_contract, maker_amount, maker_address)

    def _create_irc2_swap(self, _value: int, _from: Address, params: dict) -> None:
        maker_contract = self.msg.sender
        maker_amount = _value
        maker_address = _from
        taker_contract = Address.from_string(params['taker_contract'])
        taker_amount = int(params['taker_amount'], 16)
        taker_address = Address.from_string(params['taker_address']) if 'taker_address' in params else EMPTY_ORDER_PROVIDER
        self._create_swap(maker_contract, maker_amount, taker_contract, taker_amount, maker_address, taker_address)

    def _fill_irc2_order(self, _value: int, _from: Address, params: dict) -> None:
        taker_contract = self.msg.sender
        taker_amount = _value
        taker_address = _from
        swap_id = int(params['swap_id'], 16)
        self._fill_swap(swap_id, taker_contract, taker_amount, taker_address)

    # ================================================
    #  Checks
    # ================================================
    def _check_amount(self, amount: int) -> None:
        if amount <= 0:
            raise InvalidOrderAmount(amount)

    def _check_contract(self, address: Address) -> None:
        if not address.is_contract:
            raise InvalidOrderContract
        Whitelist(self.db).check_exists(address)

    def _check_different_contract(self, contract1: Address, contract2: Address) -> None:
        if contract1 == contract2:
            raise InvalidOrderContract(contract1, contract2)

    # ================================================
    #  External methods
    # ================================================
    @payable
    def fallback(self):
        src = self.msg.sender
        amount = self.msg.value

        # Redirect ICX from TAP holding to operator
        if (self.msg.sender == self._iconbet_wages.get()):
            self.icx.transfer(self.owner, amount)
        else:
            # Refund without revert in order to prevent caller's SCORE fail
            self.icx.transfer(src, amount)

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
            raise InvalidCallParameters('tokenFallback', 'data')

        params = json_loads(_data.decode('utf-8'))

        if params['action'] == 'create_irc2_swap':
            self._create_irc2_swap(_value, _from, params)
        elif params['action'] == 'fill_irc2_order':
            self._fill_irc2_order(_value, _from, params)
        elif params['action'] == 'market_create_limit_irc2_order':
            self._market_create_limit_irc2_order(_value, _from, params)
        else:
            raise InvalidCallParameters('tokenFallback', 'action')

    def _cleanup_decimals_ex(self, contract: Address, amount: int) -> tuple:

        decimals = ICX_TOKEN_DECIMALS if self._is_contract_icx(contract) \
            else self.create_interface_score(contract, IRC2Interface).decimals()

        divisor = 10**(decimals - SWAP_MAX_DECIMALS)
        rounded_amount = amount // divisor
        float_amount = amount / divisor

        if rounded_amount != float_amount:
            exceeded = amount - (rounded_amount * divisor)
            amount -= exceeded
            return (amount, exceeded)

        return (amount, 0)

    def _cleanup_decimals(self,
                          maker_contract: Address,
                          maker_amount: int,
                          taker_contract: Address,
                          taker_amount: int,
                          maker_address: Address) -> tuple:

        maker_amount, maker_exceed = self._cleanup_decimals_ex(maker_contract, maker_amount)
        taker_amount, taker_exceed = self._cleanup_decimals_ex(taker_contract, taker_amount)

        # Refund maker if exceed
        if maker_exceed > 0:
            Logger.warning(f"Maker exceed {maker_exceed} {maker_contract}")
            # Send back the exceed decimals to the maker
            self._transfer_funds(maker_contract, maker_exceed, maker_address)

        return (maker_amount, taker_amount)

    def _market_create_limit_order(self,
                                   taker_contract: Address,
                                   taker_amount: int,
                                   maker_contract: Address,
                                   maker_amount: int,
                                   maker_address: Address) -> None:

        Logger.warning(f"===============================================================================")
        Logger.warning(f""" BEFORE :
            taker_contract={taker_contract}
            taker_amount={taker_amount}
            maker_contract={maker_contract}
            maker_amount={maker_amount}
            maker_address={maker_address}
        """)
        Logger.warning(f"===============================================================================")

        maker_amount, taker_amount = self._cleanup_decimals(maker_contract, maker_amount, taker_contract, taker_amount, maker_address)
        Logger.warning(f"===============================================================================")
        Logger.warning(f""" AFTER :
            taker_amount={taker_amount}
            maker_amount={maker_amount}
        """)
        Logger.warning(f"===============================================================================")

        pair = (maker_contract, taker_contract)
        pending_swaps = MarketPendingSwapDB(pair, self.db)

        # Convert the linked list as we're going it during iteration
        if MarketPairsDB.is_buyer(pair, maker_contract):
            Logger.warning("Buy Side")
            swaps = list(pending_swaps.sellers())
            limit_price = maker_amount / taker_amount

            def taker_price_fn(remaining: int, limit_price: float) -> int:
                return int(remaining // limit_price)

            def swap_price_fn(swap: Swap) -> float:
                return swap.get_inverted_price()

            def limit_fn(swap_price: int, limit_price: float) -> bool:
                return round(swap_price, SWAP_MAX_DECIMALS) > round(limit_price, SWAP_MAX_DECIMALS)

        else:
            Logger.warning("Sell Side")
            swaps = list(pending_swaps.buyers())
            limit_price = taker_amount / maker_amount

            def taker_price_fn(remaining: int, limit_price: float) -> int:
                return int(remaining * limit_price)

            def swap_price_fn(swap: Swap) -> float:
                return swap.get_price()

            def limit_fn(swap_price: int, limit_price: float) -> bool:
                return round(swap_price, SWAP_MAX_DECIMALS) < round(limit_price, SWAP_MAX_DECIMALS)

        # Browse the order book and fill as much swaps as possible,
        # begginning with the cheapest swaps first, until:
        #   1) there is no more user funds left, or
        #   2) the user limit price is reached, or
        #   3) the end of the order book is reached
        remaining = maker_amount
        for swap_id in swaps:
            swap = Swap(swap_id, self.db)
            maker, taker = swap.get_orders()
            swap_price = swap_price_fn(swap)
            Logger.warning(f"swap_price ={swap_price}")
            Logger.warning(f"limit_price={limit_price}")
            Logger.warning(f"CURSWAP={swap.serialize()}")

            if remaining <= 0:
                # 1) All funds have been spent on lower price swaps, stop
                Logger.warning(f"STOP COND 1 (remaining: {remaining})")
                break

            if limit_fn(swap_price, limit_price):
                Logger.warning(f"STOP COND 2 (limit price reached : Sw:{round(swap_price, 7)} / Lim:{round(limit_price, 7)})")
                # 2) User limit price is reached
                # Create a new swap at this price and stop
                taker_amount = taker_price_fn(remaining, limit_price)
                remaining, maker_exceed = self._cleanup_decimals_ex(maker_contract, remaining)
                taker_amount, taker_exceed = self._cleanup_decimals_ex(taker_contract, taker_amount)
                Logger.warning(f"------ \n Creating Swap : \n - {remaining / 10**ICX_TOKEN_DECIMALS} {maker_contract} for \n - {taker_amount / 10**ICX_TOKEN_DECIMALS} {taker_contract} \n - (P={limit_price})\n")
                self._transfer_funds(maker_contract, maker_exceed, maker_address)
                self._create_swap(maker_contract, remaining, taker_contract, taker_amount, maker_address, EMPTY_ORDER_PROVIDER)
                break

            filling = min(taker.amount(), remaining)
            Logger.warning(f"------ \n Filling Swap : \n - {filling / 10**ICX_TOKEN_DECIMALS} {maker_contract} for \n - {maker.amount() / 10**ICX_TOKEN_DECIMALS} {taker_contract} \n - (P={swap_price})\n")
            remaining -= taker.amount()
            self._fill_swap(swap_id, maker_contract, filling, EMPTY_ORDER_PROVIDER)

        else:
            # 3) End of the order book
            Logger.warning(f"STOP COND 3 (end of order book) (remaining={remaining})")
            taker_amount = taker_price_fn(remaining, limit_price)
            remaining, maker_exceed = self._cleanup_decimals_ex(maker_contract, remaining)
            taker_amount, taker_exceed = self._cleanup_decimals_ex(taker_contract, taker_amount)
            Logger.warning(f"------ \n Creating Swap : \n - {remaining / 10**ICX_TOKEN_DECIMALS} {maker_contract} for \n - {taker_amount / 10**ICX_TOKEN_DECIMALS} {taker_contract} \n - (P={limit_price})\n")
            self._transfer_funds(maker_contract, maker_exceed, maker_address)
            self._create_swap(maker_contract, remaining, taker_contract, taker_amount, maker_address, EMPTY_ORDER_PROVIDER)

        Logger.warning("STOP")

    @catch_error
    @check_maintenance
    @external
    @payable
    def market_create_limit_icx_order(self, taker_contract: Address, taker_amount: int) -> None:
        maker_address = self.msg.sender
        maker_amount = self.msg.value
        maker_contract = ZERO_SCORE_ADDRESS
        self._market_create_limit_order(taker_contract, taker_amount, maker_contract, maker_amount, maker_address)

    @catch_error
    @check_maintenance
    @external
    @payable
    def create_icx_swap(self, taker_contract: Address, taker_amount: int, taker_address: Address = EMPTY_ORDER_PROVIDER) -> None:
        maker_address = self.msg.sender
        maker_amount = self.msg.value
        self._create_swap(ZERO_SCORE_ADDRESS, maker_amount, taker_contract, taker_amount, maker_address, taker_address)

    @catch_error
    @check_maintenance
    @external
    def cancel_swap(self, swap_id: int) -> None:
        # Check if swap exists
        SystemSwapDB(self.db).check_exists(swap_id)
        swap = Swap(swap_id, self.db)

        # Only the maker can cancel the swap
        maker, taker = swap.get_orders()
        maker.check_provider(self.msg.sender)

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
                        "decimals": ICX_TOKEN_DECIMALS
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
            last_swap = self._get_market_last_filled_swap(pair_tuple)
            if last_swap:
                # most recent swap
                orders = last_swap.get_orders()
                if MarketPairsDB.is_buyer(pair_tuple, orders[0].contract()):
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
        pair = tuple(pair.split('/'))
        MarketPairsDB.check_valid_pair(pair)
        pending_swaps = MarketPendingSwapDB(pair, self.db)
        return [
            Swap(swap_id, self.db).serialize()
            for swap_id in pending_swaps.buyers().select(offset)
        ]

    @catch_error
    @external(readonly=True)
    def get_market_sellers_pending_swaps(self, pair: str, offset: int) -> list:
        pair = tuple(pair.split('/'))
        MarketPairsDB.check_valid_pair(pair)
        pending_swaps = MarketPendingSwapDB(pair, self.db)
        return [
            Swap(swap_id, self.db).serialize()
            for swap_id in pending_swaps.sellers().select(offset)
        ]

    @catch_error
    @external(readonly=True)
    def get_market_last_filled_swap(self, pair: str) -> dict:
        pair = tuple(pair.split('/'))
        MarketPairsDB.check_valid_pair(pair)
        last_swap = self._get_market_last_filled_swap(pair)
        return last_swap.serialize() if last_swap else {}

    @catch_error
    @external(readonly=True)
    def get_market_filled_swaps(self, pair: str, offset: int) -> list:
        pair = tuple(pair.split('/'))
        MarketPairsDB.check_valid_pair(pair)
        filled_swaps = MarketFilledSwapDB(pair, self.db)
        return [
            Swap(swap_id, self.db).serialize()
            for swap_id in filled_swaps.select(offset)
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
    def get_account_pair_pending_swaps(self, address: Address, pair: str, offset: int) -> list:
        pair = tuple(pair.split('/'))
        MarketPairsDB.check_valid_pair(pair)
        pending_swaps = AccountPairPendingSwapDB(address, pair, self.db)
        return [
            Swap(swap_id, self.db).serialize()
            for swap_id in pending_swaps.select(offset)
        ]

    @catch_error
    @external(readonly=True)
    def get_account_pair_filled_swaps(self, address: Address, pair: str, offset: int) -> list:
        pair = tuple(pair.split('/'))
        MarketPairsDB.check_valid_pair(pair)
        filled_swaps = AccountPairFilledSwapDB(address, pair, self.db)
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

    @catch_error
    @external(readonly=True)
    def maintenance_enabled(self) -> bool:
        return SCOREMaintenance(self.db).is_enabled()

    @catch_error
    @external(readonly=True)
    def version(self) -> str:
        return Version(self.db).get()

    @external(readonly=True)
    def name(self) -> str:
        return ICONSwap._NAME

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
        if mode == SCOREMaintenanceMode.ENABLED:
            SCOREMaintenance(self.db).enable()
        elif mode == SCOREMaintenanceMode.DISABLED:
            SCOREMaintenance(self.db).disable()

    @catch_error
    @external
    @only_owner
    def set_iconbet_wages(self, address: Address) -> None:
        self._iconbet_wages.set(address)
