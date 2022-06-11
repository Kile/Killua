from discord import User
from discord.types.user import User as UserPayload
from discord.state import ConnectionState

from random import randint

from .utils import get_random_discord_id, random_name

class TestingUser(User):

    def __init__(self, **kwargs):
        payload = self.__get_payload(**kwargs)
        ConnectionState.__init__ = self.__nothing # This is too complicated to construct with no benefit of it being instantiated correctly
        super().__init__(state=ConnectionState(), data=payload)

    def __nothing(self) -> None:
        ...

    def __random_discriminator(self) -> str:
        """Creates a random discriminator"""
        return str(randint(0, 9)) + str(randint(0, 9)) + str(randint(0, 9)) + str(randint(0, 9))

    def __get_payload(self, **kwargs) -> UserPayload:
        """Creates the payload for a user"""
        return UserPayload({
            "id": kwargs.pop("id", get_random_discord_id()),
            "username": kwargs.pop("username", random_name()),
            "discriminator": kwargs.pop("discriminator", self.__random_discriminator()),
            "avatar": kwargs.pop("avatar", None),
            "bot": kwargs.pop("bot", False),
            "premium_type": kwargs.pop("premium_type", 0)
        })