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

    def setUp(self):
        super().setUp()

        self.icon_service = None
        # if you want to send request to network, uncomment next line and set self.TEST_HTTP_ENDPOINT_URI_V3
        # self.icon_service = IconService(HTTPProvider(self.TEST_HTTP_ENDPOINT_URI_V3))

        # install SCORE
        self._score_address = self._deploy_score()['scoreAddress']
        self._operator = self._test1
        self._user = self._wallet_array[0]

        for wallet in self._wallet_array:
            icx_transfer_call(
                super(), self._test1, wallet.get_address(), 100 * 10**18, self.icon_service)

    def _deploy_score(self, to: str = SCORE_INSTALL_ADDRESS) -> dict:
        # Generates an instance of transaction for deploying SCORE.
        transaction = DeployTransactionBuilder() \
            .from_(self._test1.get_address()) \
            .to(to) \
            .step_limit(100_000_000_000) \
            .nid(3) \
            .nonce(100) \
            .content_type("application/zip") \
            .content(gen_deploy_data_content(self.SCORE_PROJECT)) \
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

    def _create_icx_swap(self):
        self._add_whitelist(ICX_CONTRACT)
        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="create_icx_swap",
            params={
                'taker_contract': ICX_CONTRACT,
                'taker_amount': 200
            },
            value=100,
            icon_service=self.icon_service
        )

        indexed = result['eventLogs'][0]['indexed']
        self.assertEqual(indexed[0], 'SwapCreatedEvent(int,int,int)')
        swap_id = int(indexed[1], 16)
        maker_id, taker_id = map(lambda x: int(x, 16), result['eventLogs'][0]['data'])
        return swap_id, maker_id, taker_id

    def _cancel_swap(self, swap_id: int):
        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="cancel_swap",
            params={'swap_id': swap_id},
            icon_service=self.icon_service
        )

    def _fill_icx_order(self, _from, swap_id, amount):
        return transaction_call_success(
            super(),
            from_=_from,
            to_=self._score_address,
            method="fill_icx_order",
            params={'swap_id': swap_id},
            value=amount,
            icon_service=self.icon_service
        )

    # ===============================================================
    def test_fill_icx_order_ok(self):
        swap_id, maker_id, taker_id = self._create_icx_swap()
        # OK
        self._fill_icx_order(self._user, swap_id, 200)

    def test_fill_icx_order_wrong_amount(self):
        swap_id, maker_id, taker_id = self._create_icx_swap()

        # Wrong ICX amount
        result = transaction_call_error(
            super(),
            from_=self._user,
            to_=self._score_address,
            method="fill_icx_order",
            params={'swap_id': swap_id},
            value=123,
            icon_service=self.icon_service
        )
        self.assertEqual(result['failure']['message'], 'InvalidOrderContent()')

        # No ICX
        result = transaction_call_error(
            super(),
            from_=self._user,
            to_=self._score_address,
            method="fill_icx_order",
            params={'swap_id': swap_id},
            icon_service=self.icon_service
        )
        self.assertEqual(result['failure']['message'], 'InvalidOrderContent()')

    def test_fill_icx_order_wrong_id(self):
        swap_id, maker_id, taker_id = self._create_icx_swap()

        # Wrong ID
        result = transaction_call_error(
            super(),
            from_=self._user,
            to_=self._score_address,
            method="fill_icx_order",
            params={'swap_id': 123},
            value=200,
            icon_service=self.icon_service
        )
        self.assertEqual(result['failure']['message'], "ItemDoesntExist('SWAP_COMPOSITE', '123')")

    def test_fill_icx_order_already_filled(self):
        swap_id, maker_id, taker_id = self._create_icx_swap()
        # OK
        self._fill_icx_order(self._user, swap_id, 200)

        # Swap already filled
        result = transaction_call_error(
            super(),
            from_=self._user,
            to_=self._score_address,
            method="fill_icx_order",
            params={'swap_id': swap_id},
            value=200,
            icon_service=self.icon_service
        )
        self.assertEqual(result['failure']['message'], 'InvalidSwapStatus()')

    def test_fill_icx_order_cancelled(self):
        swap_id, maker_id, taker_id = self._create_icx_swap()
        self._cancel_swap(swap_id)

        # Swap already cancelled
        result = transaction_call_error(
            super(),
            from_=self._user,
            to_=self._score_address,
            method="fill_icx_order",
            params={'swap_id': swap_id},
            value=200,
            icon_service=self.icon_service
        )
        self.assertEqual(result['failure']['message'], 'InvalidSwapStatus()')
