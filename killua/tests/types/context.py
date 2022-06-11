from discord.ext.commands import Context

from ..testing import ResultData
from .message import TestingMessage as Message
from .user import TestingUser as User
from .interaction import TestingInteraction as ArgumentInteraction

from asyncio import create_task, sleep

class TestingContext(Context):
    """A class creating a suitable testing context object"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result = None
        self.me = User()
        self.current_view = None
        self.message.channel.ctx = self
        self.message.ctx = self
        self.timeout_view = False

    async def reply(self, content: str, *args, **kwargs) -> Message:
        """Replies to the current message"""
        message = Message(author=self.me, channel=self.channel, content=content, *args, **kwargs)
        self.result = ResultData(message=message)
        self.current_view = kwargs.pop("view", None)
        if self.current_view:
            if self.timeout_view:
                await self.current_view.on_timeout()
                self.current_view.stop()
            else:
                create_task(self.run_delayed(0.1, self.respond_to_view))
        message.ctx = self
        return message

    async def send(self, content: str = None, *args, **kwargs) -> Message:
        """Sends a message"""
        message = Message(author=self.me, channel=self.channel, content=content, *args, **kwargs)
        self.result = ResultData(message=message)
        self.current_view = kwargs.pop("view", None)
        if self.current_view:
            if self.timeout_view:
                await self.current_view.on_timeout()
                self.current_view.stop()
            else:
                create_task(self.run_delayed(0.1, self.respond_to_view))
        message.ctx = self
        return message

    async def run_delayed(self, delay: float, coroutine: callable, *args, **kwargs) -> None:
        """Runs a coroutine after a delay"""
        await sleep(delay)
        await coroutine(self, *args, **kwargs)

    async def invoke(self, command: str, *args, **kwargs) -> None:
        """Invokes a command"""
        ...

    async def respond_to_view(self, context: Context) -> None:
        """This determined how a view is responded to once it is sent. This is meant to be overwritten"""
        ...