from __future__ import annotations

from discord.ext.commands import Cog
from discord.ext.commands.view import StringView

from typing import Any, Coroutine, TYPE_CHECKING

if TYPE_CHECKING:
    from .types import Context, TestResult

class Testing:
    """Modifies several discord classes to be suitable in a testing environment"""

    def __new__(cls, *args, **kwargs): # This prevents this class from direct instatioation
        if cls is Testing:
            raise TypeError(f"only children of '{cls.__name__}' may be instantiated")
        return object.__new__(cls, *args, **kwargs)

    def __init__(self, cog: Cog):
        from .types import DiscordGuild, TextChannel, DiscordMember, Message, Context, TestResult, Bot

        self.base_guild: DiscordGuild = DiscordGuild()
        self.base_channel: TextChannel = TextChannel(guild=self.base_guild)
        self.base_author: DiscordMember = DiscordMember()
        self.base_message: Message = Message(author=self.base_author, channel=self.base_channel)
        self.base_context: Context = Context(message=self.base_message, bot=Bot, view=StringView("testing"))
        # StringView is not used in any method I use and even if it would be, I would
        # be overwriting that method anyways
        self.result = TestResult()
        self.cog = cog(Bot)

    @property
    def all_tests(self) -> list:
        """Automatically checks what functions are test based on their name and the overlap with the Cog method names"""
        cog_methods = []
        for cmd in [(command.name, command) for command in self.cog.get_commands()]:
            if cmd[1].walk_commands():
                for child in cmd[1].walk_commands():
                    cog_methods.append((child.name, child))
            else:
                cog_methods.append(cmd)

        own_methods = [method for method in dir(self) if not method.startswith("__") and not method.startswith("base")]

        return [getattr(self, name) for name in own_methods if name in [n for n, _ in cog_methods]]

    def refresh_attributes(self) -> None:
        """Resets all attributes in case they were changed as part of a command"""
        self.base_context.result = None

    async def run_tests(self) -> TestResult:
        """The function that returns the test result for this group"""
        for test in self.all_tests:
            await test()

        # await self.cog.client.session.close()
        return self.result

    from .types import Context

    @classmethod
    async def run_command(self, command: Coroutine, context: Context, *args, **kwargs) -> Any:
        try:
            return await command(context, *args, **kwargs)
        except Exception as e:
            return e

    @classmethod
    async def press_confirm(cls, context: Context):
        """Presses the confirm button of a ConfirmView"""
        from .types import ArgumentInteraction

        for child in context.current_view.children:
            if child.custom_id == "confirm":
                await child.callback(ArgumentInteraction(context))