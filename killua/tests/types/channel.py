from __future__ import annotations

from typing import TYPE_CHECKING, List, Union
from functools import partial

from .message import TestingMessage as Message
from .guild import TestingGuild as Guild
from .testing_results import ResultData

from discord import Guild, TextChannel, ui

if TYPE_CHECKING:
    from discord.types.channel import PermissionOverwrite, CategoryChannel

from .utils import get_random_discord_id


class TestingTextChannel:
    """A class imulating a discord text channel"""

    __class__ = TextChannel

    def __init__(self, guild: Guild, permissions: List[dict] = [], **kwargs):
        self.guild: Guild = guild
        self.name: str = kwargs.pop("name", "test")
        self.id: int = kwargs.pop("id", get_random_discord_id())
        self.guild_i: int = kwargs.pop("guild_id", get_random_discord_id())
        self.position: int = kwargs.pop("position", 1)
        self.permission_overwrites: List[PermissionOverwrite] = (
            self.__handle_permissions(permissions)
        )
        self.nsfw: bool = kwargs.pop("nsfw", False)
        self.parent: Union[CategoryChannel, None] = kwargs.pop("parent", None)
        self.type: int = kwargs.pop("type", 0)
        self._has_permission: int = kwargs.pop("has_permission", True)

        self.history_return: List[Message] = []

    def __handle_permissions(self, permissions) -> None:
        """Handles permissions"""
        if len(permissions) == 0:
            return []

        if isinstance(permissions[0]):
            for perm in permissions:
                perm = PermissionOverwrite(perm)  # lgtm [py/multiple-definition]

        return permissions

    async def history(
        self, limit: int = None, before: Message = None, after: Message = None
    ) -> List[Message]:
        """Gets the history of the channel"""
        for message in self.history_return[:limit]:
            yield message

    async def send(self, content: str, *args, **kwargs) -> None:
        """Sends a message"""
        message = Message(
            author=self.me, channel=self.channel, content=content, *args, **kwargs
        )
        self.result = ResultData(message=message)
        self.ctx.current_view: Union[ui.View, None] = kwargs.pop("view", None)

        if self.ctx.current_view:
            if self.ctx.timeout_view:
                await self.ctx.current_view.on_timeout()
                self.ctx.current_view.stop()
            else:
                self.ctx.current_view.wait = partial(self.ctx.respond_to_view, self.ctx)
        return message

    def permissions_for(self, member: Guild.Member) -> ui.Permissions:
        """Gets the permissions for a member"""
        return self._has_permission
