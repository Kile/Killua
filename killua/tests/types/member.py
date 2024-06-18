from discord import Member

from discord.types.snowflake import Snowflake

from random import randint
from typing import List, Union
from datetime import datetime

from .utils import get_random_discord_id, random_date
from .user import TestingUser as User


class TestingMember(User):
    """A class imulating a discord member"""

    __class__ = Member

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.roles: list = kwargs.pop("roles", self.__random_roles())
        self.joined_at: str = kwargs.pop("joined_at", str(random_date()))
        self.deaf: bool = kwargs.pop("deaf", False)
        self.muted: bool = kwargs.pop("muted", False)
        self.nick: str = kwargs.pop("nick", None)
        self.communication_disabled_until: str = kwargs.pop(
            "communication_disabled_until", ""
        )
        self.premium_since: Union[datetime, None] = kwargs.pop("premium_since", None)

    @property
    def display_name(self) -> str:
        return self.nick or self.username

    def __random_roles(self) -> List[Snowflake]:
        """Creates a random list of roles a user has"""
        return [get_random_discord_id() for _ in range(randint(0, 10))]
