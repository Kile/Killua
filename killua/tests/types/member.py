from discord import Member, Guild
from discord.types.user import User as UserPayload
from discord.types.member import MemberWithUser as MemberWithUserPayload
from discord.types.snowflake import Snowflake
from discord.state import ConnectionState

from random import randint
from typing import List

from .utils import get_random_discord_id, random_date, random_name

class TestingMember(Member):

    def __init__(self, guild: Guild, **kwargs):
        payload = self.__get_payload(**kwargs)
        ConnectionState.__init__ = self.__nothing # This is too complicated to construct with no benefit of it being instantiated correctly
        state = ConnectionState()
        state._users = {}
        super().__init__(state=state, data=payload, guild=guild)

    def __nothing(self) -> None:
        ...

    def __random_username(self) -> str:
        """Creates a random username. It is not really important that it makes sense"""

    def __random_discriminator(self) -> str:
        """Creates a random discriminator"""
        return str(randint(0, 9)) + str(randint(0, 9)) + str(randint(0, 9)) + str(randint(0, 9))

    def __random_roles(self) -> List[Snowflake]:
        """Creates a random list of roles a user has"""
        return [get_random_discord_id() for _ in range(randint(0, 10))]

    def __get_payload(self, **kwargs) -> MemberWithUserPayload:
        """Creates the payload for a user"""
        if "user" in kwargs:
            return MemberWithUserPayload({
                "user": kwargs.pop("user")._to_minimal_user_json(),
                "roles": kwargs.pop("roles", self.__random_roles()),
                "joined_at": kwargs.pop("joined_at", str(random_date())),
                "deaf": kwargs.pop("deaf", False),
                "muted": kwargs.pop("muted", False),
                "communication_disabled_until": kwargs.pop("communication_disabled_until", ""),
                "premium_since": kwargs.pop("premium_since", None)
            })
        else:
            return MemberWithUserPayload({
                "user": UserPayload({
                        "id": kwargs.pop("id", get_random_discord_id()),
                        "username": kwargs.pop("username", random_name()),
                        "discriminator": kwargs.pop("discriminator", self.__random_discriminator()),
                        "avatar": kwargs.pop("avatar", None),
                        "bot": kwargs.pop("bot", False),
                        "premium_type": kwargs.pop("premium_type", 0)
                }),
                "roles": kwargs.pop("roles", self.__random_roles()),
                "joined_at": kwargs.pop("joined_at", str(random_date())),
                "deaf": kwargs.pop("deaf", False),
                "muted": kwargs.pop("muted", False),
                "communication_disabled_until": kwargs.pop("communication_disabled_until", ""),
                "premium_since": kwargs.pop("premium_since", None)
            })