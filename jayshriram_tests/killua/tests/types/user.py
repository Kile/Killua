from discord import User

from random import randint

from .asset import Asset
from .utils import get_random_discord_id, random_name

class TestingUser:
    """A class imulating a discord user"""
    __class__ = User

    def __init__(self, **kwargs):
        self.id = kwargs.pop("id", get_random_discord_id())
        self.name = kwargs.pop("name", random_name())
        self.username = kwargs.pop("username", random_name())
        self.discriminator = kwargs.pop("discriminator", self.__random_discriminator())
        self.avatar = Asset(kwargs.pop("avatar")) if "avatar" in kwargs else Asset()
        self.bot = kwargs.pop("bot", False)
        self.premium_type = kwargs.pop("premium_type", 0)
    
    @property
    def mention(self) -> str:
        return "<@{}>".format(self.id)

    def __eq__(self, other: "TestingUser") -> bool:
        return self.id == other.id

    def __random_discriminator(self) -> str:
        """Creates a random discriminator"""
        return str(randint(0, 9)) + str(randint(0, 9)) + str(randint(0, 9)) + str(randint(0, 9))