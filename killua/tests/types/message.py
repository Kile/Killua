from __future__ import annotations

from typing import TYPE_CHECKING
from asyncio import create_task
from functools import partial

from discord import Message, Member, TextChannel

if TYPE_CHECKING:
    from discord.types.message import Message as MessagePayload

from .utils import get_random_discord_id, random_date

class TestingMessage:
    """A class to construct a testing"""

    __class__ = Message

    def __init__(self, author: Member, channel: TextChannel, **kwargs):

        self.deleted = False
        self.edited = False
        self.published = False

        self.author = author
        self.channel = channel
        self.channel_id = kwargs.pop("channel_id", get_random_discord_id())
        self.guild_id = kwargs.pop("guild_id", get_random_discord_id())
        self.id = kwargs.pop("id", get_random_discord_id())
        self.content = kwargs.pop("content", "")
        self.timestamp = kwargs.pop("timestamp", str(random_date()))
        self.edited_timestamp = kwargs.pop("edited_timestamp", None)
        self.tts = kwargs.pop("tts", False),
        self.mention_everyone = kwargs.pop("mention_everyone", False),
        self.mentions = kwargs.pop("mentions", []),
        self.mention_roles = kwargs.pop("mention_roles", []),
        self.attachments = kwargs.pop("attachments", []),
        self.embeds = kwargs.get("embeds", []),
        self.pinned = kwargs.pop("pinned", False),
        self.type = kwargs.pop("type", 0) # https://discord.com/developers/docs/resources/channel#message-object-message-types 
        
        if "embed" in kwargs:
            self.embeds = [kwargs.pop("embed")]

    async def edit(self, **kwargs) -> None:
        """Edits the message"""
        self.__dict__.update(kwargs) # Changes the properties defined in the kwargs
        self.edited = True
        self.ctx.current_view = kwargs.pop("view", None)
        if "embed" in kwargs:
            self.embeds.append(kwargs["embed"])

        if self.ctx.current_view:
            if not len([c for c in self.ctx.current_view.children if c.disabled]) == len(self.ctx.current_view.children):
                self.ctx.current_view.wait = partial(self.ctx.respond_to_view, self.ctx)
            else: return

        self.ctx.result.message = self
        # print(
        #     "Edited view: ", self.view,
        #     "Edited embeds: ", self.embeds,
        #     "Edited content: ", self.content
        # )

    async def delete(self) -> None:
        """Deletes the message"""
        self.deleted = True

    async def publish(self) -> None:
        """Publishes the message"""
        self.published = True