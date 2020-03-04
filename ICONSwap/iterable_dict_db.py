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
from .utils import *


class IterableDictDB(object):
    """
    Utility class wrapping the state DB.
    IterableDictDB behaves like a DictDB, but supports iterator operation with an ArrayDB.
    By default, it does *not* maintain order when iterating.
    """

    def __init__(self, var_key: str, db: IconScoreDatabase, value_type: type, maintain_order=False):
        self._keys = ArrayDB(var_key + '_keys', db, value_type=value_type)
        self._values = DictDB(var_key + '_values', db, value_type=value_type)
        self._maintain_order = maintain_order

    def __iter__(self):
        for key in self._keys:
            yield key

    def __len__(self) -> int:
        return len(self._keys)

    def __setitem__(self, key, value) -> None:
        if key not in self._keys:
            self._keys.put(key)
        self._values[key] = value

    def __getitem__(self, key):
        return self._values[key]

    def __delitem__(self, key):
        del self._values[key]
        Utils.array_db_remove(self._keys, key, self._maintain_order)

    def items(self):
        for key in self._keys:
            yield key, self._values[key]

    def keys(self):
        for key in self._keys:
            yield key

    def values(self):
        for key in self._keys:
            yield self._values[key]
