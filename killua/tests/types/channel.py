from __future__ import annotations

from typing import TYPE_CHECKING, List
from asyncio import create_task

from .message import TestingMessage as Message
from .testing_results import ResultData

from discord import Guild, TextChannel
from discord.state import ConnectionState

if TYPE_CHECKING:
    from discord.types.channel import TextChannel as TextChannelPayload
    from discord.types.channel import  PermissionOverwrite

from .utils import get_random_discord_id

class TestingTextChannel(TextChannel):
    """A class imulating a discord text channel"""

    def __init__(self, guild: Guild, permissions: List[dict] = [], **kwargs):
        payload = self.__get_payload(permissions, guild_id=Guild.id, **kwargs)
        ConnectionState.__init__ = self.__nothing # This is too complicated to construct with no benefit of it being instantiated correctly
        state = ConnectionState()
        state.shard_count = 1
        super().__init__(state=state, guild=guild, data=payload)

    def __nothing(self) -> None:
        ...

    def __handle_permissions(self, permissions) -> None:
        """Handles permissions"""
        if len(permissions) == 0:
            return []

        if isinstance(permissions[0]):
            for perm in permissions:
                perm = PermissionOverwrite(perm)

        return permissions

    def __get_payload(self, permissions: List[dict], **kwargs) -> TextChannelPayload:
        """Creates a dummy text channel payload to be used as an argument to pass to the constructor of TextChannel"""
        
        return {
            "name": kwargs.pop("name",  "test"),
            "id": kwargs.pop("id", get_random_discord_id()), # TODO random generate id
            "guild_id": kwargs.pop("guild_id", get_random_discord_id()), # TODO random generate id
            "position": kwargs.pop("position", 1),
            "permission_overwrites": self.__handle_permissions(permissions),
            "nsfw": kwargs.pop("nsfw", False),
            "parent": kwargs.pop("parent", None) ,
            "type": kwargs.pop("type", 0) 
        }


    async def send(self, content: str, *args, **kwargs) -> None:
        """Sends a message"""
        message = Message(author=self.me, channel=self.channel, content=content, *args, **kwargs)
        self.result = ResultData(message=message)
        self.ctx.current_view = kwargs.pop("view", None)
        if self.ctx.current_view:
            create_task(self.ctx.run_delayed(0.1, self.ctx.respond_to_view))
        return message