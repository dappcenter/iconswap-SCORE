

from iconservice import *
from .bag import *


class SetDB(BagDB):
    """
    SetDB is an iterable collection of *unique* items.
    Order of retrieval is *optionally* significant (*not* significant by default)
    """

    _NAME = '_SETDB'

    def __init__(self, var_key: str, db: IconScoreDatabase, value_type: type, order=False):
        name = var_key + SetDB._NAME
        super().__init__(name, db, value_type, order)
        self._name = name
        self._db = db

    def add(self, item) -> None:
        """ Adds an element to the set 
            If it already exists, it *does not raise* any exception
        """
        if item not in self._items:
            super().add(item)

    def remove(self, item) -> None:
        """ This operation removes element x from the set.
            If element x does not exist, it raises a ItemNotFound.
        """
        if item not in self._items:
            raise ItemNotFound(self._name, str(item))
        super().remove(item)

    def discard(self, item) -> None:
        """ This operation also removes element x from the set.
            If element x does not exist, it *does not raise* a ItemNotFound.
        """
        if item in self._items:
            super().remove(item)

    def pop(self):
        """ Removes an element from the set and returns it """
        return self._items.pop()

    def union(self, other: set):
        """ Return a set containing the union of sets """
        return self._to_set().union(other)

    def update(self, *others) -> None:
        """ Update the set with the union of this set and others """
        self._to_set().update(others)

    def _to_set(self) -> set:
        result = set()
        for item in self:
            result.add(item)
        return result
