from iconsdk.builder.transaction_builder import DeployTransactionBuilder
from tbears.libs.icon_integrate_test import IconIntegrateTestBase, SCORE_INSTALL_ADDRESS
from iconsdk.libs.in_memory_zip import gen_deploy_data_content
from iconsdk.signed_transaction import SignedTransaction
from ICONSwap.tests.utils import *
import json

ICX_CONTRACT = 'cx0000000000000000000000000000000000000000'


class ICONSwapTests(IconIntegrateTestBase):

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

    def _create_icx_irc2_swap(self, a1, a2, taker_address=None):
        self._add_whitelist(ICX_CONTRACT)
        self._add_whitelist(self._irc2_address)

        params = {
            'taker_contract': self._irc2_address,
            'taker_amount': a2
        }
        if (taker_address):
            params['taker_address'] = taker_address

        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._score_address,
            method="create_icx_swap",
            params=params,
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

    def _create_irc2_icx_swap(self, a1, a2, taker_address=None):
        self._add_whitelist(ICX_CONTRACT)
        self._add_whitelist(self._irc2_address)

        data_params = {
            "action": "create_irc2_swap",
            "taker_contract": ICX_CONTRACT,
            "taker_amount": hex(a2),
        }
        if (taker_address):
            data_params['taker_address'] = taker_address

        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._irc2_address,
            method="transfer",
            params={
                '_to': self._score_address,
                '_value': a1,
                '_data': json.dumps(data_params).encode('utf-8')},
            icon_service=self.icon_service
        )

        indexed = result['eventLogs'][0]['indexed']
        self.assertEqual(indexed[0], 'SwapCreatedEvent(int,int,int)')
        swap_id = int(indexed[1], 16)
        maker_id, taker_id = map(lambda x: int(x, 16), result['eventLogs'][0]['data'])
        return swap_id, maker_id, taker_id

    def _create_irc2_irc2_swap(self, a1, a2, taker_address=None):
        self._add_whitelist(self._irc2_address)
        self._add_whitelist(self._irc2_address_2)

        data_params = {
            "action": "create_irc2_swap",
            "taker_contract": self._irc2_address_2,
            "taker_amount": hex(a2),
        }
        if (taker_address):
            data_params['taker_address'] = taker_address

        # OK
        result = transaction_call_success(
            super(),
            from_=self._operator,
            to_=self._irc2_address,
            method="transfer",
            params={
                '_to': self._score_address,
                '_value': a1,
                '_data': json.dumps(data_params).encode('utf-8')},
            icon_service=self.icon_service
        )

        indexed = result['eventLogs'][0]['indexed']
        self.assertEqual(indexed[0], 'SwapCreatedEvent(int,int,int)')
        swap_id = int(indexed[1], 16)
        maker_id, taker_id = map(lambda x: int(x, 16), result['eventLogs'][0]['data'])
        return swap_id, maker_id, taker_id

    def _fill_icx_order(self, call, _from, swap_id, amount):
        return call(
            super(),
            from_=_from,
            to_=self._score_address,
            method="fill_icx_order",
            params={'swap_id': swap_id},
            value=amount,
            icon_service=self.icon_service
        )

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

    def _fill_icx_order_success(self, _from, swap_id, amount):
        return self._fill_icx_order(transaction_call_success, _from, swap_id, amount)

    def _fill_icx_order_error(self, _from, swap_id, amount):
        return self._fill_icx_order(transaction_call_error, _from, swap_id, amount)
