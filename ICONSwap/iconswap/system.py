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
from ..scorelib.set import *


class SystemSwapDB(SetDB):
    _NAME = 'SYSTEM_SWAP_DB'

    def __init__(self, db: IconScoreDatabase):
        super().__init__(SystemSwapDB._NAME, db, int)


class SystemOrderDB(SetDB):
    _NAME = 'SYSTEM_ORDER_DB'

    def __init__(self, db: IconScoreDatabase):
        super().__init__(SystemOrderDB._NAME, db, int)
