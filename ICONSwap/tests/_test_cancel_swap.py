# -*- coding: utf-8 -*-

# Copyright 2019 ICONation
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


class TestICONSwap(IconIntegrateTestBase):
    TEST_HTTP_ENDPOINT_URI_V3 = "http://127.0.0.1:9000/api/v3"
    SCORE_PROJECT = os.path.abspath(os.path.join(DIR_PATH, '..'))

    _PARTICIPATION_COST = 1 * 10**18

    def setUp(self):
        super().setUp()

        self.icon_service = None
        # if you want to send request to network, uncomment next line and set self.TEST_HTTP_ENDPOINT_URI_V3
        # self.icon_service = IconService(HTTPProvider(self.TEST_HTTP_ENDPOINT_URI_V3))

        # install SCORE
        self._score_address = self._deploy_score()['scoreAddress']
        self._operator = self._test1
        self._user = self._wallet_array[0]
        self._attacker = self._wallet_array[1]

        for wallet in self._wallet_array:
            icx_transfer_call(
                super(), self._test1, wallet.get_address(), 100 * 10**18, self.icon_service)

        self._operator_balance = get_icx_balance(super(), address=self._operator.get_address(), icon_service=self.icon_service)
        self._user_balance = get_icx_balance(super(), address=self._user.get_address(), icon_service=self.icon_service)

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

    def _create_swap_icx(self):
        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="create_swap",
            params={
                'contract1': 'cx0000000000000000000000000000000000000000',
                'amount1': 100,
                'contract2': 'cx0000000000000000000000000000000000000000',
                'amount2': 200
            },
            icon_service=self.icon_service
        )

        indexed = result['eventLogs'][0]['indexed']
        self.assertEqual(indexed[0], 'SwapCreatedEvent(int,int,int)')
        swapid = int(indexed[1], 16)
        o1id, o2id = map(lambda x: int(x, 16), result['eventLogs'][0]['data'])
        return swapid, o1id, o2id

    def _fulfill_icx_order(self, _from, orderid, amount):
        result = transaction_call_success(
            super(),
            from_=_from,
            to_=self._score_address,
            method="fulfill_icx_order",
            params={'orderid': orderid},
            value=amount,
            icon_service=self.icon_service
        )

    # ===============================================================
    def test_cancel_swap_ok(self):
        swapid, o1id, o2id = self._create_swap_icx()
        self._fulfill_icx_order(self._operator, o1id, 100)
        self._fulfill_icx_order(self._user, o2id, 200)

        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="cancel_swap",
            params={"swapid": swapid},
            icon_service=self.icon_service
        )

        # Check refund
        operator_balance = get_icx_balance(super(), address=self._operator.get_address(), icon_service=self.icon_service)
        user_balance = get_icx_balance(super(), address=self._user.get_address(), icon_service=self.icon_service)

        # OK
        self.assertEqual(operator_balance, self._operator_balance)
        self.assertEqual(user_balance, self._user_balance)

    def test_cancel_swap_ok2(self):
        swapid, o1id, o2id = self._create_swap_icx()
        self._fulfill_icx_order(self._user, o2id, 200)

        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="cancel_swap",
            params={"swapid": swapid},
            icon_service=self.icon_service
        )

        # Check refund
        operator_balance = get_icx_balance(super(), address=self._operator.get_address(), icon_service=self.icon_service)
        user_balance = get_icx_balance(super(), address=self._user.get_address(), icon_service=self.icon_service)

        # OK
        self.assertEqual(operator_balance, self._operator_balance)
        self.assertEqual(user_balance, self._user_balance)

    def test_cancel_swap_ok3(self):
        swapid, o1id, o2id = self._create_swap_icx()
        self._fulfill_icx_order(self._operator, o1id, 100)

        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="cancel_swap",
            params={"swapid": swapid},
            icon_service=self.icon_service
        )

        # Check refund
        operator_balance = get_icx_balance(super(), address=self._operator.get_address(), icon_service=self.icon_service)
        user_balance = get_icx_balance(super(), address=self._user.get_address(), icon_service=self.icon_service)

        # OK
        self.assertEqual(operator_balance, self._operator_balance)
        self.assertEqual(user_balance, self._user_balance)

    def test_cancel_swap_ok4(self):
        swapid, o1id, o2id = self._create_swap_icx()

        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="cancel_swap",
            params={"swapid": swapid},
            icon_service=self.icon_service
        )

        # Check refund
        operator_balance = get_icx_balance(super(), address=self._operator.get_address(), icon_service=self.icon_service)
        user_balance = get_icx_balance(super(), address=self._user.get_address(), icon_service=self.icon_service)

        # OK
        self.assertEqual(operator_balance, self._operator_balance)
        self.assertEqual(user_balance, self._user_balance)

    def test_cancel_swap_not_operator(self):
        swapid, o1id, o2id = self._create_swap_icx()
        self._fulfill_icx_order(self._operator, o1id, 100)
        self._fulfill_icx_order(self._user, o2id, 200)

        # OK
        result = transaction_call_error(
            super(),
            from_=self._user,
            to_=self._score_address,
            method="cancel_swap",
            params={"swapid": swapid},
            icon_service=self.icon_service
        )
        self.assertEqual(result['failure']['message'], 'InvalidSwapAuthor()')

    def test_cancel_swap_attacker(self):
        swapid, o1id, o2id = self._create_swap_icx()
        self._fulfill_icx_order(self._operator, o1id, 100)
        self._fulfill_icx_order(self._user, o2id, 200)

        # OK
        result = transaction_call_error(
            super(),
            from_=self._attacker,
            to_=self._score_address,
            method="cancel_swap",
            params={"swapid": swapid},
            icon_service=self.icon_service
        )
        self.assertEqual(result['failure']['message'], 'InvalidSwapAuthor()')
