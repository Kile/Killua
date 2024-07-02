from discord.ext.commands import Context, Command
from discord.ui import View

from .testing_results import ResultData
from .message import TestingMessage as Message
from .user import TestingUser as User
from .channel import TestingTextChannel as TextChannel
from .member import TestingMember as Member

from typing import Union
from functools import partial


class TestingContext:
    """A class creating a suitable testing context object"""

    __class__ = Context

    def __init__(self, **kwargs):
        self.result: Union[ResultData, None] = None
        self.me: User = User()
        self.message: Message = kwargs.pop("message")
        self.bot: User = kwargs.pop("bot")
        self.channel: TextChannel = self.message.channel
        self.author: Member = self.message.author
        self.command: Union[Command, None] = None

        self.current_view: Union[View, None] = None
        self.message.channel.ctx: TestingContext = self
        self.message.ctx: TestingContext = self
        self.timeout_view: bool = False

    async def reply(self, content: str, *args, **kwargs) -> Message:
        """Replies to the current message"""
        message = Message(
            author=self.me, channel=self.channel, content=content, *args, **kwargs
        )
        self.result = ResultData(message=message)
        self.current_view: Union[View, None] = kwargs.pop("view", None)

        if self.current_view:
            if self.timeout_view:
                await self.current_view.on_timeout()
                self.current_view.stop()
            else:
                self.current_view.wait = partial(self.respond_to_view, self)
        message.ctx = self
        return message

    async def send(self, content: str = None, *args, **kwargs) -> Message:
        """Sends a message"""
        message = Message(
            author=self.me, channel=self.channel, content=content, *args, **kwargs
        )
        self.result = ResultData(message=message)
        self.current_view: Union[View, None] = kwargs.pop("view", None)

        if self.current_view:
            if self.timeout_view:
                await self.current_view.on_timeout()
                self.current_view.stop()
            else:
                self.current_view.wait = partial(self.respond_to_view, self)
        message.ctx = self
        return message

    async def invoke(self, command: str, *args, **kwargs) -> None:
        """Invokes a command"""
        ...

    async def respond_to_view(self, context: Context) -> None:
        """This determined how a view is responded to once it is sent. This is meant to be overwritten"""
        ...
