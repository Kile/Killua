from discord import User

from random import randint

from .asset import Asset
from .utils import get_random_discord_id, random_name
from .permissions import Permissions
from .role import TestingRole


class PublicFlags:
    """Minimal stand-in for discord.PublicUserFlags."""
    def __iter__(self):
        return iter([])


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
        self.banner = kwargs.pop("banner", None)
        self.public_flags = kwargs.pop("public_flags", PublicFlags())
        # Bot-style checks in guild commands (ban_members, view_audit_log, etc.)
        self.guild_permissions = kwargs.pop(
            "guild_permissions",
            Permissions(
                ban_members=True,
                kick_members=True,
                view_audit_log=True,
                moderate_members=True,
                administrator=True,
            ),
        )
        self.top_role = kwargs.pop("top_role", TestingRole(position=999))
        # RPS / trivia use `if not user.mutual_guilds` for non-bot opponents (discord.User)
        self.mutual_guilds = kwargs.pop("mutual_guilds", [object()])

    @property
    def display_name(self) -> str:
        return self.username

    @property
    def display_avatar(self) -> "Asset":
        return self.avatar

    @property
    def mention(self) -> str:
        return "<@{}>".format(self.id)

    def __eq__(self, other: "TestingUser") -> bool:
        if not hasattr(other, "id"):
            return NotImplemented
        return self.id == other.id

    def __str__(self) -> str:
        return self.username

    async def send(self, *args, **kwargs) -> None:
        pass

    def __random_discriminator(self) -> str:
        """Creates a random discriminator"""
        return (
            str(randint(0, 9))
            + str(randint(0, 9))
            + str(randint(0, 9))
            + str(randint(0, 9))
        )
