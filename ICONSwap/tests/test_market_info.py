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

from iconsdk.builder.transaction_builder import DeployTransactionBuilder
from iconsdk.builder.call_builder import CallBuilder
from iconsdk.icon_service import IconService
from iconsdk.libs.in_memory_zip import gen_deploy_data_content
from iconsdk.providers.http_provider import HTTPProvider
from iconsdk.signed_transaction import SignedTransaction

from tbears.libs.icon_integrate_test import IconIntegrateTestBase, SCORE_INSTALL_ADDRESS
from ICONSwap.tests.utils import *

DIR_PATH = os.path.abspath(os.path.dirname(__file__))
ICX_CONTRACT = 'cx0000000000000000000000000000000000000000'


class TestICONSwap(IconIntegrateTestBase):
    TEST_HTTP_ENDPOINT_URI_V3 = "http://127.0.0.1:9000/api/v3"
    SCORE_PROJECT = os.path.abspath(os.path.join(DIR_PATH, '..'))
    IRC2_PROJECT = os.path.abspath(os.path.join(DIR_PATH, './irc2'))

    def setUp(self):
        super().setUp()

        self.icon_service = None
        # if you want to send request to network, uncomment next line and set self.TEST_HTTP_ENDPOINT_URI_V3
        # self.icon_service = IconService(HTTPProvider(self.TEST_HTTP_ENDPOINT_URI_V3))

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

    def _deploy_score(self, project, to: str = SCORE_INSTALL_ADDRESS) -> dict:
        # Generates an instance of transaction for deploying SCORE.
        transaction = DeployTransactionBuilder() \
            .from_(self._test1.get_address()) \
            .to(to) \
            .step_limit(100_000_000_000) \
            .nid(3) \
            .nonce(100) \
            .content_type("application/zip") \
            .content(gen_deploy_data_content(project)) \
            .build()

        # Returns the signed transaction object having a signature
        signed_transaction = SignedTransaction(transaction, self._test1)

        # process the transaction in local
        result = self.process_transaction(
            signed_transaction, self.icon_service)

        self.assertTrue('status' in result)
        self.assertEqual(1, result['status'])
        self.assertTrue('scoreAddress' in result)

        return result

    def _deploy_irc2(self, project, to: str = SCORE_INSTALL_ADDRESS) -> dict:
        # Generates an instance of transaction for deploying SCORE.
        transaction = DeployTransactionBuilder() \
            .params({
                "_initialSupply": 0x100000000000,
                "_decimals": 18,
                "_name": 'StandardToken',
                "_symbol": 'ST',
            }) \
            .from_(self._operator.get_address()) \
            .to(to) \
            .step_limit(100_000_000_000) \
            .nid(3) \
            .nonce(100) \
            .content_type("application/zip") \
            .content(gen_deploy_data_content(project)) \
            .build()

        # Returns the signed transaction object having a signature
        signed_transaction = SignedTransaction(transaction, self._operator)

        # process the transaction in local
        result = self.process_transaction(
            signed_transaction, self.icon_service)

        self.assertTrue('status' in result)
        self.assertEqual(1, result['status'])
        self.assertTrue('scoreAddress' in result)

        return result

    def _add_whitelist(self, contract):
        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="add_whitelist",
            params={'contract': contract},
            icon_service=self.icon_service
        )

    def _create_icx_irc2_swap(self, a1, a2):
        self._add_whitelist(ICX_CONTRACT)
        self._add_whitelist(self._irc2_address)
        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="create_icx_swap",
            params={
                'taker_contract': self._irc2_address,
                'taker_amount': a2
            },
            value=a1,
            icon_service=self.icon_service
        )

        indexed = result['eventLogs'][0]['indexed']
        self.assertEqual(indexed[0], 'SwapCreatedEvent(int,int,int)')
        swap_id = int(indexed[1], 16)
        maker_id, taker_id = map(lambda x: int(x, 16), result['eventLogs'][0]['data'])
        return swap_id, maker_id, taker_id

    def _fill_irc2_order(self, call, _from, to_, swap_id, amount):
        return call(
            super(),
            from_=_from,
            to_=to_,
            method="transfer",
            params={
                '_to': self._score_address,
                '_value': amount,
                '_data': json.dumps({
                    "action": "fill_irc2_order",
                    "swap_id": hex(swap_id)
                }).encode('utf-8')},
            icon_service=self.icon_service
        )

    def _fill_irc2_order_success(self, _from, to_, swap_id, amount):
        return self._fill_irc2_order(transaction_call_success, _from, to_, swap_id, amount)

    def _fill_irc2_order_error(self, _from, to_, swap_id, amount):
        return self._fill_irc2_order(transaction_call_error, _from, to_, swap_id, amount)

    def _create_irc2_icx_swap(self, a1, a2):
        self._add_whitelist(ICX_CONTRACT)
        self._add_whitelist(self._irc2_address)
        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._irc2_address,
            method="transfer",
            params={
                '_to': self._score_address,
                '_value': a1,
                '_data': json.dumps({
                    "action": "create_irc2_swap",
                    "taker_contract": ICX_CONTRACT,
                    "taker_amount": hex(a2),
                }).encode('utf-8')},
            icon_service=self.icon_service
        )

        indexed = result['eventLogs'][0]['indexed']
        self.assertEqual(indexed[0], 'SwapCreatedEvent(int,int,int)')
        swap_id = int(indexed[1], 16)
        maker_id, taker_id = map(lambda x: int(x, 16), result['eventLogs'][0]['data'])
        return swap_id, maker_id, taker_id

    # ===============================================================
    def test_market_info_ok(self):
        # 2 ICX = 3 IRC2 (1 ICX = 1.5 IRC2)
        swap_id_200icx_300irc2 = self._create_icx_irc2_swap(200, 300)[0]
        # 1 ICX = 2 IRC2
        swap_id_10icx_20irc2 = self._create_icx_irc2_swap(10, 20)[0]
        # 1 ICX = 2 IRC2
        swap_id_100icx_200irc2 = self._create_icx_irc2_swap(100, 200)[0]
        # 1 IRC2 = 2 ICX (1 ICX = 0.5 IRC2)
        swap_id_10irc2_20icx = self._create_irc2_icx_swap(10, 20)[0]
        # 1 IRC2 = 2 ICX (1 ICX = 0.5 IRC2)
        swap_id_20irc2_30icx = self._create_irc2_icx_swap(20, 30)[0]

        market_info = icx_call(
            super(),
            from_=self._operator.get_address(),
            to_=self._score_address,
            method="get_market_info",
            params={"offset": 0},
            icon_service=self.icon_service
        )

        print(market_info)

        market_sellers = icx_call(
            super(),
            from_=self._operator.get_address(),
            to_=self._score_address,
            method="get_market_sellers_pending_swaps",
            params={"pair": market_info['pairs'][0]['name'], "offset": 0},
            icon_service=self.icon_service
        )

        print("SELLERS =======================")
        print(json.dumps(market_sellers, indent=4))
        self.assertEqual(market_sellers[0]['maker']['amount'], 200)
        self.assertEqual(market_sellers[0]['taker']['amount'], 300)
        self.assertEqual(market_sellers[1]['maker']['amount'], 100)
        self.assertEqual(market_sellers[1]['taker']['amount'], 200)
        self.assertEqual(market_sellers[2]['maker']['amount'], 10)
        self.assertEqual(market_sellers[2]['taker']['amount'], 20)

        market_buyers = icx_call(
            super(),
            from_=self._operator.get_address(),
            to_=self._score_address,
            method="get_market_buyers_pending_swaps",
            params={"pair": market_info['pairs'][0]['name'], "offset": 0},
            icon_service=self.icon_service
        )

        print("BUYERS =======================")
        print(json.dumps(market_buyers, indent=4))
        self.assertEqual(market_buyers[0]['maker']['amount'], 10)
        self.assertEqual(market_buyers[0]['taker']['amount'], 20)
        self.assertEqual(market_buyers[1]['maker']['amount'], 20)
        self.assertEqual(market_buyers[1]['taker']['amount'], 30)

        self._fill_irc2_order_success(self._user, self._irc2_address, swap_id_10icx_20irc2, 20)
        self._fill_irc2_order_success(self._user, self._irc2_address, swap_id_100icx_200irc2, 200)

        filled_swaps = icx_call(
            super(),
            from_=self._operator.get_address(),
            to_=self._score_address,
            method="get_market_filled_swaps",
            params={"pair": market_info['pairs'][0]['name'], "offset": 0},
            icon_service=self.icon_service
        )

        print(json.dumps(filled_swaps, indent=4))
