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
from .consts import *
from ..scorelib.utils import *
from ..scorelib.set import *


class AccountPendingSwapDB(SetDB):
    _NAME = 'ACCOUNT_PENDING_SWAP_DB'

    def __init__(self, db: IconScoreDatabase, address: Address):
        name = str(address) + '_' + AccountPendingSwapDB._NAME
        super().__init__(name, db, int)


class AccountFilledSwapDB(SetDB):
    _NAME = 'ACCOUNT_FILLED_SWAP_DB'

    def __init__(self, db: IconScoreDatabase, address: Address):
        name = str(address) + '_' + AccountFilledSwapDB._NAME
        super().__init__(name, db, int)
