

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

    def _cancel_swap_error(self, _from, swap_id):
        return transaction_call_error(
            super(),
            from_=_from,
            to_=self._score_address,
            method="cancel_swap",
            params={"swap_id": swap_id},
            icon_service=self.icon_service
        )

    # ===============================================================
    def test_cancel_swap_icx_irc2_ok(self):
        swap_id, maker_id, taker_id = self._create_icx_irc2_swap(100, 200)

        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="cancel_swap",
            params={"swap_id": swap_id},
            icon_service=self.icon_service
        )

        # Check refund
        operator_balance = get_icx_balance(super(), address=self._operator.get_address(), icon_service=self.icon_service)
        user_balance = get_icx_balance(super(), address=self._user.get_address(), icon_service=self.icon_service)

        # OK
        self.assertEqual(operator_balance, self._operator_icx_balance)
        self.assertEqual(user_balance, self._user_icx_balance)

    def test_cancel_swap_icx_irc2_private_ok(self):
        swap_id, maker_id, taker_id = self._create_icx_irc2_swap(100, 200, self._user.get_address())

        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="cancel_swap",
            params={"swap_id": swap_id},
            icon_service=self.icon_service
        )

        # Check refund
        operator_balance = get_icx_balance(super(), address=self._operator.get_address(), icon_service=self.icon_service)
        user_balance = get_icx_balance(super(), address=self._user.get_address(), icon_service=self.icon_service)

        # OK
        self.assertEqual(operator_balance, self._operator_icx_balance)
        self.assertEqual(user_balance, self._user_icx_balance)

    def test_cancel_swap_irc2_icx_ok(self):
        swap_id, maker_id, taker_id = self._create_irc2_icx_swap(100, 200)

        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="cancel_swap",
            params={"swap_id": swap_id},
            icon_service=self.icon_service
        )

        # Check refund
        operator_balance = get_icx_balance(super(), address=self._operator.get_address(), icon_service=self.icon_service)
        user_balance = get_icx_balance(super(), address=self._user.get_address(), icon_service=self.icon_service)

        # OK
        self.assertEqual(operator_balance, self._operator_icx_balance)
        self.assertEqual(user_balance, self._user_icx_balance)

    def test_cancel_swap_irc2_icx_private_ok(self):
        swap_id, maker_id, taker_id = self._create_irc2_icx_swap(100, 200, self._user.get_address())

        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="cancel_swap",
            params={"swap_id": swap_id},
            icon_service=self.icon_service
        )

        # Check refund
        operator_balance = get_icx_balance(super(), address=self._operator.get_address(), icon_service=self.icon_service)
        user_balance = get_icx_balance(super(), address=self._user.get_address(), icon_service=self.icon_service)

        # OK
        self.assertEqual(operator_balance, self._operator_icx_balance)
        self.assertEqual(user_balance, self._user_icx_balance)

    def test_cancel_swap_irc2_irc2_ok(self):
        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(100, 200)

        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="cancel_swap",
            params={"swap_id": swap_id},
            icon_service=self.icon_service
        )

        # Check refund
        operator_balance = get_irc2_balance(super(), self._operator.get_address(), self._irc2_address, self.icon_service)
        user_balance = get_irc2_balance(super(), self._user.get_address(), self._irc2_address, self.icon_service)

        # OK
        self.assertEqual(operator_balance, self._operator_irc2_balance)
        self.assertEqual(user_balance, self._user_irc2_balance)

    def test_cancel_swap_irc2_irc2_private_ok(self):
        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(100, 200, self._user.get_address())

        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="cancel_swap",
            params={"swap_id": swap_id},
            icon_service=self.icon_service
        )

        # Check refund
        operator_balance = get_irc2_balance(super(), self._operator.get_address(), self._irc2_address, self.icon_service)
        user_balance = get_irc2_balance(super(), self._user.get_address(), self._irc2_address, self.icon_service)

        # OK
        self.assertEqual(operator_balance, self._operator_irc2_balance)
        self.assertEqual(user_balance, self._user_irc2_balance)

    def test_cancel_icx_irc2_swap_already_swapped(self):
        swap_id, maker_id, taker_id = self._create_icx_irc2_swap(100, 200)
        self._fill_irc2_order_success(self._user, self._irc2_address, swap_id, 200)

        # Error: already swapped
        result = self._cancel_swap_error(self._operator, swap_id)
        self.assertEqual(result['failure']['message'], f"InvalidSwapStatus('SWAP_{swap_id}', 'SUCCESS', 'PENDING')")

    def test_cancel_icx_irc2_private_swap_already_swapped(self):
        swap_id, maker_id, taker_id = self._create_icx_irc2_swap(100, 200)
        self._fill_irc2_order_success(self._user, self._irc2_address, swap_id, 200)

        # Error: already swapped
        result = self._cancel_swap_error(self._operator, swap_id)
        self.assertEqual(result['failure']['message'], f"InvalidSwapStatus('SWAP_{swap_id}', 'SUCCESS', 'PENDING')")

    def test_cancel_irc2_icx_swap_already_swapped(self):
        swap_id, maker_id, taker_id = self._create_irc2_icx_swap(100, 200)
        self._fill_icx_order_success(self._user, swap_id, 200)

        # Error: already swapped
        result = self._cancel_swap_error(self._operator, swap_id)
        self.assertEqual(result['failure']['message'], f"InvalidSwapStatus('SWAP_{swap_id}', 'SUCCESS', 'PENDING')")

    def test_cancel_irc2_irc2_swap_already_swapped(self):
        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(100, 200)
        self._fill_irc2_order_success(self._user, self._irc2_address_2, swap_id, 200)

        # Error: already swapped
        result = self._cancel_swap_error(self._operator, swap_id)
        self.assertEqual(result['failure']['message'], f"InvalidSwapStatus('SWAP_{swap_id}', 'SUCCESS', 'PENDING')")

    def test_cancel_private_swap_taker(self):
        swap_id, maker_id, taker_id = self._create_icx_irc2_swap(100, 200, self._user.get_address())
        result = self._cancel_swap_error(self._user, swap_id)
        self.assertEqual(result['failure']['message'], f'InvalidOrderProvider({self._operator.get_address()})')

    def test_cancel_swap_attacker(self):
        swap_id, maker_id, taker_id = self._create_icx_irc2_swap(100, 200)
        result = self._cancel_swap_error(self._attacker, swap_id)
        self.assertEqual(result['failure']['message'], f'InvalidOrderProvider({self._operator.get_address()})')

    def test_cancel_after_swap_success(self):
        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(100, 200)
        self._fill_irc2_order_success(self._user, self._irc2_address_2, swap_id, 200)
        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(100, 200)
        self._fill_irc2_order_success(self._user, self._irc2_address_2, swap_id, 200)
        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(100, 200)
        self._fill_irc2_order_success(self._user, self._irc2_address_2, swap_id, 200)

        # Update balance
        self._operator_irc2_balance = get_irc2_balance(super(), address=self._operator.get_address(), token=self._irc2_address, icon_service=self.icon_service)
        self._user_irc2_balance = get_irc2_balance(super(), address=self._user.get_address(), token=self._irc2_address, icon_service=self.icon_service)

        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(100, 200)
        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="cancel_swap",
            params={"swap_id": swap_id},
            icon_service=self.icon_service
        )

        # Check refund
        operator_balance = get_irc2_balance(super(), self._operator.get_address(), self._irc2_address, self.icon_service)
        user_balance = get_irc2_balance(super(), self._user.get_address(), self._irc2_address, self.icon_service)

        # OK
        self.assertEqual(operator_balance, self._operator_irc2_balance)
        self.assertEqual(user_balance, self._user_irc2_balance)

    def test_cancel_after_swap_private_success(self):
        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(100, 200, self._user.get_address())
        self._fill_irc2_order_success(self._user, self._irc2_address_2, swap_id, 200)
        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(100, 200, self._user.get_address())
        self._fill_irc2_order_success(self._user, self._irc2_address_2, swap_id, 200)
        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(100, 200)
        self._fill_irc2_order_success(self._user, self._irc2_address_2, swap_id, 200)
        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(100, 200)
        self._fill_irc2_order_success(self._user, self._irc2_address_2, swap_id, 200)

        # Update balance
        self._operator_irc2_balance = get_irc2_balance(super(), address=self._operator.get_address(), token=self._irc2_address, icon_service=self.icon_service)
        self._user_irc2_balance = get_irc2_balance(super(), address=self._user.get_address(), token=self._irc2_address, icon_service=self.icon_service)

        swap_id, maker_id, taker_id = self._create_irc2_irc2_swap(100, 200)
        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="cancel_swap",
            params={"swap_id": swap_id},
            icon_service=self.icon_service
        )

        # Check refund
        operator_balance = get_irc2_balance(super(), self._operator.get_address(), self._irc2_address, self.icon_service)
        user_balance = get_irc2_balance(super(), self._user.get_address(), self._irc2_address, self.icon_service)

        # OK
        self.assertEqual(operator_balance, self._operator_irc2_balance)
        self.assertEqual(user_balance, self._user_irc2_balance)
