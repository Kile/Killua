from __future__ import annotations

from typing import TYPE_CHECKING
from asyncio import create_task

from discord import Message, User, TextChannel
from discord.state import ConnectionState

if TYPE_CHECKING:
    from discord.types.message import Message as MessagePayload

from .utils import get_random_discord_id, random_date

class TestingMessage(Message):
    """A class to construct a testing"""

    def __init__(self, author: User, channel: TextChannel, **kwargs):
        payload = self.__get_payload(author=author, channel_id=channel.id, **kwargs)
        ConnectionState.__init__ = self.__nothing # This is too complicated to construct with no benefit of it being instantiated correctly
        state = ConnectionState()
        state._users = {}
        super().__init__(data=payload, state=state, channel=channel)
        self.deleted = False
        self.edited = False
        self.published = False

    def __nothing(self) -> None:
        ...

    def __get_payload(self, **kwargs) -> MessagePayload:
        """Gets the payload for a message"""
        payload = {
            "channel_id": kwargs.pop("channel_id"),
            "guild_id": kwargs.pop("guild_id", get_random_discord_id()),
            "id": kwargs.pop("id", get_random_discord_id()),
            "author": kwargs.pop("author")._to_minimal_user_json(),
            "content": kwargs.pop("content", ""),
            "timestamp": kwargs.pop("timestamp", str(random_date())),
            "edited_timestamp": kwargs.pop("edited_timestamp", None),
            "tts": kwargs.pop("tts", False),
            "mention_everyone": kwargs.pop("mention_everyone", False),
            "mentions": kwargs.pop("mentions", []),
            "mention_roles": kwargs.pop("mention_roles", []),
            "attachments": kwargs.pop("attachments", []),
            "embeds": kwargs.pop("embeds", []),
            "pinned": kwargs.pop("pinned", False),
            "type": kwargs.pop("type", 0) # https://discord.com/developers/docs/resources/channel#message-object-message-types 
        }
        if not payload["embeds"] and "embed" in kwargs:
            payload["embeds"] = [kwargs.pop("embed").to_dict()]

        for key, value in kwargs.items(): # From my understanding the other attributes being NotRequired
            # means that they not have to be added to the dictionary, however if they are they need to be valid.
            # So I am saving myself the effort of making defaults but still supporting them by adding this
            payload[key] = value

        return payload

    async def edit(self, **kwargs) -> None:
        """Edits the message"""
        self.__dict__.update(kwargs) # Changes the properties defined in the kwargs
        self.edited = True
        self.ctx.current_view = kwargs.pop("view", None)
        if "embed" in kwargs:
            self.embeds.append(kwargs["embed"])

        if self.ctx.current_view:
            if not len([c for c in self.ctx.current_view.children if c.disabled]) == len(self.ctx.current_view.children):
                create_task(self.ctx.run_delayed(5, self.ctx.respond_to_view))
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