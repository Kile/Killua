import sys, os
from aiohttp import ClientSession

# This is a necessary hacky fix for importing issues
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from discord import Intents, Message
from discord.abc import Messageable
from ...bot import BaseBot
from .channel import TestingTextChannel
from .user import TestingUser

from typing import Any, Optional, Callable
from asyncio import get_event_loop, TimeoutError, sleep

class TestingBot(BaseBot):
    """A class simulating a discord.py bot instance"""

    def __init__(self, *args, **kwargs) -> None:
        self.fail_timeout = False
        return super().__init__(*args, **kwargs)

    def get_channel(self, channel: int):
        """Returns a channel object"""
        return TestingTextChannel(channel)

    def get_user(self, user: int) -> Any:
        return TestingUser(id=user)

    @property
    def loop(self):
        return get_event_loop()

    @loop.setter
    def loop(self, _): # This attribute cannot be changed
        ...

    def _schedule_event(self, *args, **kwargs):
        ...

    def wait_for(
        self,
        event: str,
        /,
        *,
        check: Optional[Callable[..., bool]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        if self.fail_timeout:
            raise TimeoutError
        return BaseBot.wait_for(self, event, check=check, timeout=timeout)

    async def resolve(self, event: str, /, *args: Any) -> None:
        await sleep(0.1) # waiting for the command to set up the listener
        listeners = self._listeners.get(event)
        if listeners:
            removed = []
            for i, (future, condition) in enumerate(listeners):
                if future.cancelled():
                    removed.append(i)
                    continue

                try:
                    result = condition(*args)
                except Exception as exc:
                    future.set_exception(exc)
                    removed.append(i)
                else:
                    if result:
                        if len(args) == 0:
                            future.set_result(None)
                        elif len(args) == 1:
                            future.set_result(args[0])
                        else:
                            future.set_result(args)
                        removed.append(i)

            if len(removed) == len(listeners):
                self._listeners.pop(event)
            else:
                for idx in reversed(removed):
                    del listeners[idx]

    async def send_message(self, messageable: Messageable, *args, **kwargs) -> Message:
        """We do not want a tip sent which would ruin the test checks so this is overwritten"""
        return await messageable.send(content=kwargs.pop("content", None), *args, **kwargs)

    async def setup_hook(self) -> None:
        self.session = ClientSession()

BOT = TestingBot(command_prefix="k!", intents=Intents.all())