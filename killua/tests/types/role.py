from discord import Role

from .utils import random_name
from .permissions import Permissions

from typing import Optional


class TestingRole:

    __class__ = Role

    def __init__(self, **kwargs):
        self.name: str = kwargs.pop("name", random_name())
        self._permissions: int = kwargs.pop("permissions", 0)
        self.position: int = kwargs.pop("position", 0)
        self._colour: int = kwargs.pop("colour", 0)
        self.hoist: bool = kwargs.pop("hoist", False)
        self._icon: Optional[str] = kwargs.pop("icon", None)
        self.unicorn_emoji: Optional[str] = kwargs.pop("unicorn_emoji", None)
        self.managed: bool = kwargs.pop("managed", False)
        self.mentionable: bool = kwargs.pop("mentionable", False)
        self.tags = kwargs.pop("tags", None)

    @property
    def permissions(self) -> int:
        return Permissions(self._permissions)
