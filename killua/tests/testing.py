from __future__ import annotations

from discord.ext.commands import Cog, Command
from discord.ext.commands.view import StringView

import sys, traceback
import logging
from typing import TYPE_CHECKING, List, Coroutine, Optional

if TYPE_CHECKING:
    from .types import Context, TestResult


class Testing:
    """Modifies several discord classes to be suitable in a testing environment"""

    def __new__(
        cls, *args, **kwargs
    ):  # This prevents this class from direct instatioation
        if cls is Testing:
            raise TypeError(f"only children of '{cls.__name__}' may be instantiated")
        return object.__new__(cls, *args, **kwargs)

    def __init__(self, cog: Cog):
        from .types import (
            DiscordGuild,
            TextChannel,
            DiscordMember,
            Message,
            Context,
            TestResult,
            Bot,
        )

        self.base_guild: DiscordGuild = DiscordGuild()
        self.base_channel: TextChannel = TextChannel(guild=self.base_guild)
        self.base_author: DiscordMember = DiscordMember()
        self.base_message: Message = Message(
            author=self.base_author, channel=self.base_channel
        )
        self.base_context: Context = Context(
            message=self.base_message, bot=Bot, view=StringView("testing")
        )
        # StringView is not used in any method I use and even if it would be, I would
        # be overwriting that method anyways
        self.result: TestResult = TestResult()
        self.cog: Cog = cog(Bot)

    @property
    def all_tests(self) -> List[Testing]:
        """Automatically checks what functions are test based on their name and the overlap with the Cog method names"""
        cog_methods = []
        for cmd in [(command.name, command) for command in self.cog.get_commands()]:
            if hasattr(cmd[1], "walk_commands") and cmd[1].walk_commands():
                for child in cmd[1].walk_commands():
                    cog_methods.append((child.name, child))
            else:
                cog_methods.append(cmd)

        command_classes: List[Testing] = []

        for cls in self.__class__.__subclasses__():
            # print(cls)
            if cls.__subclasses__():
                for subcls in cls.__subclasses__():
                    command_classes.append(subcls)
            else:
                command_classes.append(cls)
        # print(command_classes)
        # return [cls.test_command for cls in command_classes]
        return [
            cls
            for cls in command_classes
            if cls.__name__.lower() in [n for n, _ in cog_methods]
        ]

    @property
    def command(self) -> Coroutine:
        """The command that is being tested"""
        for command in self.cog.walk_commands():
            if isinstance(command, Command):
                if command.name.lower() == self.__class__.__name__.lower():
                    return command

    async def run_tests(self, only_command: Optional[str] = None) -> TestResult:
        """The function that returns the test result for this group"""
        for test in self.all_tests:
            command = test()

            if only_command and command.__class__.__name__.lower() != only_command:
                continue  # Skip if the command is not the one we want to test

            await command.test_command()
            self.result.add_result(command.result)

        # await self.cog.client.session.close()
        return self.result

    async def test_command(self) -> None:
        """Runs all tests of a command"""

        for method in test.tests(self):
            await method(self)

    @classmethod
    async def press_confirm(cls, context: Context):
        """Presses the confirm button of a ConfirmView"""
        from .types import ArgumentInteraction

        for child in context.current_view.children:
            if child.custom_id == "confirm":
                await child.callback(ArgumentInteraction(context))


class test(object):

    def __init__(self, method):
        self._method = method

    async def __call__(self, obj: Testing, *args, **kwargs):
        from .types import Result, ResultData

        try:
            logging.debug(
                f"Running test {self._method.__name__} of command {obj.__class__.__name__}"
            )
            await self._method(obj, *args, **kwargs)
            logging.debug("successfully passed test")
            obj.result.completed_test(self._method, Result.passed)
        except Exception as e:
            _, _, var = sys.exc_info()
            traceback.print_tb(var)
            tb_info = traceback.extract_tb(var)
            filename, line_number, _, text = tb_info[-1]

            if isinstance(e, AssertionError):
                parsed_text = text.split(",")[0]

                logging.error(
                    f'{filename}:{line_number} test "{self._method.__name__}" of command "{obj.__class__.__name__.lower()}" failed at \n{parsed_text} \nwith actual result \n"{e}"'
                )
                obj.result.completed_test(
                    self._method, Result.failed, result_data=ResultData(error=e)
                )
            else:
                logging.critical(
                    f'{filename}:{line_number} test "{self._method.__name__}" of command "{obj.__class__.__name__.lower()}" raised the the following exception in the statement {text}: \n"{e}"'
                )
                obj.result.completed_test(
                    self._method, Result.errored, ResultData(error=e)
                )

    @classmethod
    def tests(cls, subject):
        def g():
            for name in dir(subject):
                method = getattr(subject, name)
                if isinstance(method, test):
                    yield name, method

        return [method for _, method in g()]
