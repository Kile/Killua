import sys, os
from aiohttp import ClientSession
import discord

# This is a necessary hacky fix for importing issues
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from discord import Intents, Message
from discord.abc import Messageable
from ...bot import BaseBot
from .channel import TestingTextChannel
from .user import TestingUser

from typing import Any, Callable

from asyncio import get_event_loop, TimeoutError, sleep


class TestingBot(BaseBot):
    """A class simulating a discord.py bot instance"""

    def __init__(self, *args, **kwargs) -> None:
        self.fail_timeout = False
        super().__init__(*args, **kwargs)

    def get_channel(self, channel: int):
        """Returns a channel object"""
        return TestingTextChannel(channel)

    def get_user(self, user: int) -> Any:
        return TestingUser(id=user)

    @property
    def loop(self):
        return get_event_loop()

    @loop.setter
    def loop(self, _):  # This attribute cannot be changed
        ...

    def _schedule_event(self, *args, **kwargs): ...

    def wait_for(
        self,
        event: str,
        /,
        *,
        check: Callable[..., bool] | None = None,
        timeout: float | None = None,
    ) -> Any:
        if self.fail_timeout:
            raise TimeoutError
        return BaseBot.wait_for(self, event, check=check, timeout=timeout)

    async def resolve(self, event: str, /, *args: Any) -> None:
        await sleep(0.1)  # waiting for the command to set up the listener
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
        content = kwargs.pop("content", None)
        if args and isinstance(args[0], str):
            content = args[0]
            args = args[1:]
        return await messageable.send(
            content=content, *args, **kwargs
        )

    async def find_dominant_color(self, url: str) -> int:
        return 0x3E4A78

    def sha256_for_api(self, endpoint: str, expires_in_seconds: int) -> tuple[str, str]:
        return ("fake_token", "9999999999")

    def api_url(self, *, to_fetch=False, is_for_cards=False):
        return "http://localhost:6060"

    async def make_embed_from_api(
        self,
        image_url: str,
        embed: discord.Embed,
        expire_in: int = 60 * 60 * 24 * 7,
        no_token: bool = False,
        thumbnail: bool = False,
        force_fetch: bool = False,
    ) -> tuple[discord.Embed, discord.File | None]:
        if thumbnail:
            embed.set_thumbnail(url=image_url)
        else:
            embed.set_image(url=image_url)
        return embed, None

    def convert_to_timestamp(self, snowflake_id: int) -> str:
        return f"<t:{int((snowflake_id >> 22) / 1000 + 1420070400)}:f>"

    def get_lootbox_from_name(self, name: str):
        from ...static.constants import LOOTBOXES
        for lb_id, lb in LOOTBOXES.items():
            if lb["name"].lower() == name.lower():
                return lb_id
        return None

    async def fetch_user(self, user_id: int):
        return TestingUser(id=user_id)

    async def _dm_check(self, user) -> bool:
        return True

    def is_user_installed(self, ctx) -> bool:
        return False

    async def setup_hook(self) -> None:
        self.session = ClientSession()


BOT = TestingBot(command_prefix="k!", intents=Intents.all())
