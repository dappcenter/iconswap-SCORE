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

from iconservice import *
from .iterable_dict_db import *


class ItemAlreadyExists(Exception):
    pass


class ItemDoesntExist(Exception):
    pass


class Composite:
    # ================================================
    #  DB Variables
    # ================================================
    _ITEMS = 'COMPOSITE_ITEMS'

    # ================================================
    #  Checks
    # ================================================
    def check_doesnt_exist(self, item) -> None:
        if self.exists(item):
            raise ItemAlreadyExists(self._name, str(item))

    def check_exists(self, item) -> None:
        if not self.exists(item):
            raise ItemDoesntExist(self._name, str(item))

    # ================================================
    #  Public Methods
    # ================================================
    def __init__(self, db: IconScoreDatabase, name: str, value_type: type):
        self._name = name
        self._idb = IterableDictDB(f'{name}_{Composite._ITEMS}', db, value_type=value_type)

    def items(self):
        return self._idb.items()

    def exists(self, item) -> bool:
        return (item in self._idb)

    def add(self, item) -> None:
        self.check_doesnt_exist(item)
        self._idb[item] = item

    def remove(self, item) -> None:
        self.check_exists(item)
        del self._idb[item]
