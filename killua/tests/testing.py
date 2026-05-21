from __future__ import annotations

from discord.ext.commands import Cog, Command
from discord.ext.commands.view import StringView

import sys, traceback
import logging
from typing import TYPE_CHECKING, List, Coroutine, Optional

from . import config

if TYPE_CHECKING:
    from .types import Context, TestResult


def _test_class_command_name(cls) -> str:
    """Discord command name for this test class (defaults to class name)."""
    return getattr(cls, "command_name", None) or cls.__name__.lower()


def collect_test_classes(group_cls: type) -> list:
    """Return leaf test classes registered under a group (depth-first subclass walk)."""
    found: list = []

    def walk(base: type) -> None:
        for cls in base.__subclasses__():
            if cls.__subclasses__():
                walk(cls)
            else:
                found.append(cls)

    walk(group_cls)
    return found


class Testing:
    """Modifies several discord classes to be suitable in a testing environment"""

    # Set True on cog group classes (TestingCards, TestingGames, …) so leaf command
    # classes fail fast when no matching discord command exists.
    requires_command: bool = False

    def __new__(
        cls, *args, **kwargs
    ):  # This prevents this class from direct instantiation
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
        if self._should_bind_command():
            cmd = self.command
            if cmd is None:
                want = _test_class_command_name(self.__class__)
                raise ValueError(
                    f"No discord command named {want!r} on cog {cog.__name__!r} "
                    f"(test class {self.__class__.__name__})"
                )

    @classmethod
    def _should_bind_command(cls) -> bool:
        if not getattr(cls, "requires_command", False):
            return False
        if cls.__name__.startswith("Testing"):
            return False
        for name in dir(cls):
            if isinstance(getattr(cls, name, None), test):
                return True
        return False

    @property
    def all_tests(self) -> List[Testing]:
        """Automatically checks what functions are test based on their name and the overlap with the Cog method names"""
        cog_methods = []
        for cmd in [(command.name, command) for command in self.cog.get_commands()]:
            cog_methods.append(cmd)
            if hasattr(cmd[1], "walk_commands") and cmd[1].walk_commands():
                for child in cmd[1].walk_commands():
                    cog_methods.append((child.name, child))

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
            if _test_class_command_name(cls) in [n for n, _ in cog_methods]
        ]

    @property
    def command(self) -> Coroutine:
        """The command that is being tested"""
        want = _test_class_command_name(self.__class__)
        for command in self.cog.walk_commands():
            if isinstance(command, Command):
                if command.name.lower() == want.lower():
                    return command

    async def run_tests(self, only_command: Optional[str] = None) -> TestResult:
        """The function that returns the test result for this group"""
        for test in self.all_tests:
            command = test()

            if only_command and _test_class_command_name(command.__class__) != only_command:
                continue  # Skip if the command is not the one we want to test

            await command.test_command()
            cmd_name = _test_class_command_name(command.__class__)
            self.result.by_command.setdefault(cmd_name, []).extend(command.result.records)
            self.result.add_result(command.result)

        # await self.cog.client.session.close()
        return self.result

    async def test_command(self) -> None:
        """Runs all tests of a command"""
        from .fixtures import reset_test_fixtures

        reset_test_fixtures()
        for method in test.tests(self):
            await method(self)

    @classmethod
    async def press_confirm(cls, context: Context):
        """Presses the confirm button of a ConfirmView or ConfirmButton"""
        from .harnesses.views import find_button
        from .types import ArgumentInteraction

        button = find_button(context.current_view, custom_id="confirm")
        if button:
            await button.callback(ArgumentInteraction(context))

    @classmethod
    async def press_cancel(cls, context: Context):
        """Presses the cancel button of a ConfirmView or ConfirmButton."""
        from .harnesses.views import find_button
        from .types import ArgumentInteraction

        button = find_button(context.current_view, custom_id="cancel")
        if button:
            await button.callback(ArgumentInteraction(context))


class test(object):

    def __init__(self, method):
        self._method = method

    async def __call__(self, obj: Testing, *args, **kwargs):
        from .types import Result, ResultData

        try:
            cmd_label = _test_class_command_name(obj.__class__)
            logging.debug(
                f"Running test {self._method.__name__} of command {cmd_label}"
            )
            await self._method(obj, *args, **kwargs)
            logging.debug("successfully passed test")
            obj.result.completed_test(self._method, Result.passed)
        except Exception as e:
            _, _, var = sys.exc_info()
            if not config.SUPPRESS_TEST_TRACEBACKS:
                traceback.print_tb(var)
            tb_info = traceback.extract_tb(var)
            filename, line_number, _, text = tb_info[-1]

            if isinstance(e, AssertionError):
                parsed_text = text.split(",")[0]

                logging.error(
                    f'{filename}:{line_number} test "{self._method.__name__}" of command "{cmd_label}" failed at \n{parsed_text} \nwith actual result \n"{e}"'
                )
                obj.result.completed_test(
                    self._method, Result.failed, result_data=ResultData(error=e)
                )
            else:
                logging.critical(
                    f'{filename}:{line_number} test "{self._method.__name__}" of command "{cmd_label}" raised the the following exception in the statement {text}: \n"{e}"'
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
