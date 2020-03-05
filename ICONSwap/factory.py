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


class Factory:
    # ================================================
    #  DB Variables
    # ================================================
    _UID = 'FACTORY_UID'

    # ================================================
    #  Private Methods
    # ================================================
    @staticmethod
    def _uid(db: IconScoreDatabase, factory: str) -> VarDB:
        return VarDB(f'{factory}_{Factory._UID}', db, value_type=int)

    # ================================================
    #  Public Methods
    # ================================================
    @staticmethod
    def get_uid(db: IconScoreDatabase, factory: str) -> int:
        uid = Factory._uid(db, factory)
        uid.set(uid.get() + 1)
        return uid.get()
