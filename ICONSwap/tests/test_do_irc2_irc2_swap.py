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

import os
import json
from ICONSwap.tests.iconswap_utils import *

DIR_PATH = os.path.abspath(os.path.dirname(__file__))


class TestICONSwap(ICONSwapTests):
    TEST_HTTP_ENDPOINT_URI_V3 = "http://127.0.0.1:9000/api/v3"
    SCORE_PROJECT = os.path.abspath(os.path.join(DIR_PATH, '..'))
    IRC2_PROJECT = os.path.abspath(os.path.join(DIR_PATH, './irc2'))

    def setUp(self):
        super().setUp()

        self.icon_service = None

        # install SCORE
        self._score_address = self._deploy_score(self.SCORE_PROJECT)['scoreAddress']
        self._operator = self._test1
        self._user = self._wallet_array[0]
        self._attacker = self._wallet_array[1]

        for wallet in self._wallet_array:
            icx_transfer_call(
                super(), self._test1, wallet.get_address(), 100 * 10**18, self.icon_service)

        self._operator_icx_balance = get_icx_balance(super(), address=self._operator.get_address(), icon_service=self.icon_service)
        self._user_icx_balance = get_icx_balance(super(), address=self._user.get_address(), icon_service=self.icon_service)
        self._irc2_address = self._deploy_irc2(self.IRC2_PROJECT)['scoreAddress']
        self._irc2_address_2 = self._deploy_irc2(self.IRC2_PROJECT)['scoreAddress']

        irc2_transfer(super(), from_=self._operator, token=self._irc2_address, to_=self._user.get_address(), value=0x1000000, icon_service=self.icon_service)
        irc2_transfer(super(), from_=self._operator, token=self._irc2_address, to_=self._attacker.get_address(), value=0x1000000, icon_service=self.icon_service)
        irc2_transfer(super(), from_=self._operator, token=self._irc2_address_2, to_=self._user.get_address(), value=0x1000000, icon_service=self.icon_service)
        irc2_transfer(super(), from_=self._operator, token=self._irc2_address_2, to_=self._attacker.get_address(), value=0x1000000, icon_service=self.icon_service)
        self._operator_irc2_balance = get_irc2_balance(super(), address=self._operator.get_address(), token=self._irc2_address, icon_service=self.icon_service)
        self._user_irc2_balance = get_irc2_balance(super(), address=self._user.get_address(), token=self._irc2_address, icon_service=self.icon_service)
        self._operator_irc2_balance_2 = get_irc2_balance(super(), address=self._operator.get_address(), token=self._irc2_address_2, icon_service=self.icon_service)
        self._user_irc2_balance_2 = get_irc2_balance(super(), address=self._user.get_address(), token=self._irc2_address_2, icon_service=self.icon_service)

    # ===============================================================
    def test_do_irc2_irc2_swap_ok(self):
        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(100, 200)
        self._fill_irc2_order_success(self._user, self._irc2_address_2, swap_id, 200)

        # Check trade status
        operator_irc2_balance = get_irc2_balance(super(), address=self._operator.get_address(), token=self._irc2_address, icon_service=self.icon_service)
        user_irc2_balance = get_irc2_balance(super(), address=self._user.get_address(), token=self._irc2_address, icon_service=self.icon_service)
        operator_irc2_balance_2 = get_irc2_balance(super(), address=self._operator.get_address(), token=self._irc2_address_2, icon_service=self.icon_service)
        user_irc2_balance_2 = get_irc2_balance(super(), address=self._user.get_address(), token=self._irc2_address_2, icon_service=self.icon_service)

        # OK
        self.assertEqual(operator_irc2_balance, self._operator_irc2_balance - 100)
        self.assertEqual(operator_irc2_balance_2, self._operator_irc2_balance_2 + 200)

        self.assertEqual(user_irc2_balance, self._user_irc2_balance + 100)
        self.assertEqual(user_irc2_balance_2, self._user_irc2_balance_2 - 200)

    def test_do_irc2_irc2_swap_partial_ok(self):
        maker = 100
        taker = 200
        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(maker, taker)
        ratio = 1 / 3
        taker_ratio = int(taker * ratio)
        maker_ratio = int(maker * ratio)
        self._fill_irc2_order_success(self._user, self._irc2_address_2, swap_id, taker_ratio)

        # Check trade status
        operator_irc2_balance = get_irc2_balance(super(), address=self._operator.get_address(), token=self._irc2_address, icon_service=self.icon_service)
        user_irc2_balance = get_irc2_balance(super(), address=self._user.get_address(), token=self._irc2_address, icon_service=self.icon_service)
        operator_irc2_balance_2 = get_irc2_balance(super(), address=self._operator.get_address(), token=self._irc2_address_2, icon_service=self.icon_service)
        user_irc2_balance_2 = get_irc2_balance(super(), address=self._user.get_address(), token=self._irc2_address_2, icon_service=self.icon_service)

        # OK
        self.assertEqual(operator_irc2_balance, self._operator_irc2_balance - maker)
        self.assertEqual(operator_irc2_balance_2, self._operator_irc2_balance_2 + taker_ratio)
        self.assertEqual(user_irc2_balance, self._user_irc2_balance + maker_ratio)
        self.assertEqual(user_irc2_balance_2, self._user_irc2_balance_2 - taker_ratio)

    def test_do_irc2_irc2_swap_partial_and_cancel_ok(self):
        maker = 100
        taker = 200
        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(maker, taker)
        ratio = 1 / 3
        taker_ratio = int(taker * ratio)
        maker_ratio = int(maker * ratio)
        self._fill_irc2_order_success(self._user, self._irc2_address_2, swap_id, taker_ratio)
        self._cancel_swap(swap_id)

        # Check trade status
        operator_irc2_balance = get_irc2_balance(super(), address=self._operator.get_address(), token=self._irc2_address, icon_service=self.icon_service)
        user_irc2_balance = get_irc2_balance(super(), address=self._user.get_address(), token=self._irc2_address, icon_service=self.icon_service)
        operator_irc2_balance_2 = get_irc2_balance(super(), address=self._operator.get_address(), token=self._irc2_address_2, icon_service=self.icon_service)
        user_irc2_balance_2 = get_irc2_balance(super(), address=self._user.get_address(), token=self._irc2_address_2, icon_service=self.icon_service)

        # OK
        self.assertEqual(operator_irc2_balance, self._operator_irc2_balance - maker_ratio)
        self.assertEqual(operator_irc2_balance_2, self._operator_irc2_balance_2 + taker_ratio)
        self.assertEqual(user_irc2_balance, self._user_irc2_balance + maker_ratio)
        self.assertEqual(user_irc2_balance_2, self._user_irc2_balance_2 - taker_ratio)

    def test_do_irc2_irc2_swap_private_attacker(self):
        # Private swap is for user
        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(100, 200, self._user.get_address())
        # Attacker tries to fill it
        self._fill_irc2_order_error(self._attacker, self._irc2_address_2, swap_id, 200)
        # User tries to fill it
        self._fill_irc2_order_success(self._user, self._irc2_address_2, swap_id, 200)
