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
        irc2_transfer(super(), from_=self._operator, token=self._irc2_address_2, to_=self._user.get_address(), value=0x1000000, icon_service=self.icon_service)
        self._operator_irc2_balance = get_irc2_balance(super(), address=self._operator.get_address(), token=self._irc2_address, icon_service=self.icon_service)
        self._user_irc2_balance = get_irc2_balance(super(), address=self._user.get_address(), token=self._irc2_address, icon_service=self.icon_service)

    # ===============================================================
    def test_add_whitelist_ok(self):
        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="add_whitelist",
            params={'contract': ICX_CONTRACT},
            icon_service=self.icon_service
        )

        whitelist = icx_call(
            super(),
            from_=self._operator.get_address(),
            to_=self._score_address,
            method="get_whitelist",
            params={"offset": 0},
            icon_service=self.icon_service
        )

        self.assertTrue(len(whitelist) == 1)
        self.assertTrue(whitelist[0] == Address.from_string(ICX_CONTRACT))

    def test_add_whitelist_double_add(self):
        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="add_whitelist",
            params={'contract': ICX_CONTRACT},
            icon_service=self.icon_service
        )
        # Already added
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="add_whitelist",
            params={'contract': ICX_CONTRACT},
            icon_service=self.icon_service
        )
        whitelist = icx_call(
            super(),
            from_=self._operator.get_address(),
            to_=self._score_address,
            method="get_whitelist",
            params={"offset": 0},
            icon_service=self.icon_service
        )
        self.assertTrue(len(whitelist) == 1)
        self.assertTrue(whitelist[0] == Address.from_string(ICX_CONTRACT))

    def test_add_whitelist_not_contract(self):
        # OK
        result = transaction_call_error(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="add_whitelist",
            params={'contract': 'hx0000000000000000000000000000000000000000'},
            icon_service=self.icon_service
        )
        self.assertEqual(result['failure']['message'], "InvalidWhitelistContract('WHITELIST', hx0000000000000000000000000000000000000000)")

    def test_add_whitelist_not_operator(self):
        # OK
        result = transaction_call_error(
            super(),
            from_=self._attacker,
            to_=self._score_address,
            method="add_whitelist",
            params={'contract': ICX_CONTRACT},
            icon_service=self.icon_service
        )
        self.assertEqual(result['failure']['message'], f"SenderNotScoreOwnerError({self._operator.get_address()})")
