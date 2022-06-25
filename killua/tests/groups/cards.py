from ..types import *
from ..testing import TestResult, Result, Testing, ResultData
from ...cogs.cards import Cards
from ...utils.paginator import Buttons
from ...static.constants import DB

# from types import FunctionType
# from inspect import isfunction, getmembers

from discord.ext.commands.view import StringView

from typing import Coroutine
from random import randint
from math import ceil

class TestingCards:

    def __init__(self):
        self.base_guild = DiscordGuild()
        self.base_channel = TextChannel(guild=self.base_guild)
        self.base_author = DiscordUser()
        self.base_message = Message(author=self.base_author, channel=self.base_channel)
        self.base_context = Context(message=self.base_message, bot=Bot, view=StringView("testing"))
        # StringView is not used in any method I use and even if it would be, I would
        # be overwriting that method anyways
        self.result = TestResult()

    @property
    def all_tests(self) -> list:
        # TODO make this smart. Tried and failed because dir() errors and __dict__ only lists attributes
        # cog_methods = [(command.name, command) for command in self.cog.get_commands()]
        # own_methods = [method for method in self.__dict__.items() if type(method[1]) == FunctionType]
        # print([x for x in self.__dict__.items() if not str(x[0]).startswith("base")])
        # print(own_methods)

        # return [method for name, method in own_methods if name in [n for n, _ in cog_methods]]
        return [self.book, self.sell]

    def refresh_attributes(self) -> None:
        """Resets all attributes in case they were changed as part of a command"""
        self.base_context.result = None

    async def run_tests(self) -> TestResult:
        """The function that returns the test result for this group"""
        await Bot.setup_hook()
        await self.base_context.respond_to_view(self.base_context)
        self.cog = Cards(Bot) # Because this needs a workling instance of ClientSession which is only added here it also needs to be in here
        for test in self.all_tests:
            await test()

        return self.result

    async def book(self):

        # Test if user has no cards
        try:
            await self.cog.book(self.cog, self.base_context)
            if self.base_context.result.message.content == "You don't have any cards yet!":
                self.result.completed_test(self.cog.book, Result.passed)
            else:
                self.result.completed_test(self.cog.book, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.book, Result.errored, ResultData(error=e))

        # Test if the page chosen is invalid
        try:
            user = User(self.base_author.id)
            user.add_card(randint(1, 99)) # To prevent no cards error
            await self.cog.book(self.cog, self.base_context, page=8)
            if self.base_context.result.message.content == f"Please choose a page number between 1 and {6+ceil(len(user.fs_cards)/18)}":
                self.result.completed_test(self.book, Result.passed)
            else:
                self.result.completed_test(self.cog.book, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.book, Result.errored, ResultData(error=e))

        # Test it responds with a valid paginator
        try:
            user = User(self.base_author.id)
            user.add_card(randint(1, 99)) # To prevent no cards error
            self.base_context.timeout_view = True # Make the view instantly time out
            await self.cog.book(self.cog, self.base_context)
            if isinstance(self.base_context.result.message.view, Buttons):
                self.result.completed_test(self.cog.book, Result.passed)
            else:
                self.result.completed_test(self.cog.book, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.book, Result.errored, ResultData(error=e))

    async def sell(self):

        # Testing no arguments
        try:
            await self.cog.sell(self.cog, self.base_context)
            if self.base_context.result.message and \
                self.base_context.result.message.content == "You need to specify what exactly to sell":
                self.result.completed_test(self.cog.sell, Result.passed)
            else:
                self.result.completed_test(self.cog.sell, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.sell, Result.errored, ResultData(error=e))