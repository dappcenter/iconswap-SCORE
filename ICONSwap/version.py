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


class Version(object):

    # ================================================
    #  DB Variables
    # ================================================
    _NAME = 'VERSION'

    # ================================================
    #  Private Methods
    # ================================================
    def __init__(self, db: IconScoreDatabase):
        self._name = Version._NAME
        self._version = VarDB(self._name, db, value_type=str)
        self._db = db

    @staticmethod
    def _as_tuple(version: str) -> tuple:
        parts = []
        for part in version.split('.'):
            parts.append(int(part))
        return tuple(parts)

    # ================================================
    #  Public Methods
    # ================================================
    def update(self, version: str) -> None:
        self._version.set(version)

    def get(self) -> str:
        return self._version.get()

    def is_less_than_target_version(self, target: str) -> bool:
        return Version._as_tuple(self.get()) < Version._as_tuple(target)

    def __delete__(self) -> None:
        self._version.remove()
