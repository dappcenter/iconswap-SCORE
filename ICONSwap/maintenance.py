

from iconservice import *
from .checks import *


class SCOREInMaintenanceException(Exception):
    pass


class SCOREMaintenanceMode:
    DISABLED = 0
    ENABLED = 1


class SCOREMaintenance:
    _NAME = 'SCORE_MAINTENANCE'

    def __init__(self, db: IconScoreDatabase):
        self._name = SCOREMaintenance._NAME
        self._maintenance_mode = VarDB(f'{self._name}_MAINTENANCE_MODE', db, value_type=int)
        self._db = db

    def enable(self) -> None:
        self._maintenance_mode.set(SCOREMaintenanceMode.ENABLED)

    def disable(self) -> None:
        self._maintenance_mode.set(SCOREMaintenanceMode.DISABLED)

    def is_enabled(self) -> bool:
        return self._maintenance_mode.get() == SCOREMaintenanceMode.ENABLED

    def is_disabled(self) -> bool:
        return self._maintenance_mode.get() == SCOREMaintenanceMode.DISABLED


def check_maintenance(func):
    if not isfunction(func):
        raise NotAFunctionError

    @wraps(func)
    def __wrapper(self: object, *args, **kwargs):
        if SCOREMaintenance(self.db).is_enabled():
            raise SCOREInMaintenanceException

        return func(self, *args, **kwargs)
    return __wrapper
