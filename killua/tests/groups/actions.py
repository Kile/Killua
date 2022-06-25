from ..types import *
from ..testing import TestResult, Result, Testing, ResultData
from ...cogs.actions import Actions

# from types import FunctionType
# from inspect import isfunction, getmembers

from discord.ext.commands.view import StringView

from typing import Coroutine
from asyncio import wait
from random import randrange, randint

class TestingActions:

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
        return [self.hug, self.pat, self.poke, self.slap, self.tickle, self.cuddle, self.dance, self.neko, self.smile, self.blush, self.tail, self.settings]

    def refresh_attributes(self) -> None:
        """Resets all attributes in case they were changed as part of a command"""
        self.base_context.result = None

    async def run_tests(self) -> TestResult:
        """The function that returns the test result for this group"""
        await Bot.setup_hook()
        self.cog = Actions(Bot) # Because this needs a workling instance of ClientSession which is only added here it also needs to be in here
        for test in self.all_tests:
            await test()

        await self.cog.session.close()
        return self.result

    async def action_logic(self, command: Coroutine) -> None:
        """The underlying test scenarios for an action command"""
        # Testing no arguments with no "yes" response
        self.base_context.command = command

        try:
            Bot.fail_timeout = True
            await command(self.cog, self.base_context)
            # We do not wait for completion here as it is supposed to time out
            if self.base_context.result.message.content == f"You provided no one to {command.name}.. Should- I {command.name} you?":
                self.result.completed_test(command, Result.passed)
            else:
                self.result.completed_test(command, Result.failed, result_data=ResultData(self.base_context.result))
        except Exception as e:
            self.result.completed_test(command, Result.errored, result_data=ResultData(error=e))
        
        Bot.fail_timeout = False

        # Testing no arguments with "yes" response
        try:
            resolving_message = Message(author=self.base_author, channel=self.base_channel, content="yes")
            await wait({command(self.cog, self.base_context), Bot.resolve("message", resolving_message)})
            if self.base_context.result.message.embeds and \
                self.base_context.result.message.embeds[0].image:
                self.result.completed_test(command, Result.passed)
            else:
                self.result.completed_test(command, Result.failed, result_data=self.base_context.result)
        except Exception as e:
            self.result.completed_test(command, Result.errored, ResultData(error=e))

        # Testing argument = author
        try:
            member = DiscordMember(user=self.base_author, guild=self.base_guild)
            await command(self.cog, self.base_context, [member])
            if self.base_context.result.message.content == "Sorry... you can\'t use this command on yourself":
                self.result.completed_test(command, Result.passed)
            else:
                self.result.completed_test(command, Result.failed, result_data=self.base_context.result)
        except Exception as e:
            self.result.completed_test(command, Result.errored, ResultData(error=e))

        # Testing one member correctly supplied
        try:
            member = DiscordMember(guild=self.base_guild)
            await command(self.cog, self.base_context, [member])
            if self.base_context.result.message.embeds and \
                self.base_context.result.message.embeds[0].image:
                self.result.completed_test(command, Result.passed)
            else:
                self.result.completed_test(command, Result.failed, result_data=self.base_context.result)
        except Exception as e:
            self.result.completed_test(command, Result.errored, ResultData(error=e))

        # Testing multiple members correctly supplied
        try:
            members = [DiscordMember(guild=self.base_guild) for _ in range(randrange(2, 10))]
            await command(self.cog, self.base_context, members)
            if self.base_context.result.message.embeds and \
                self.base_context.result.message.embeds[0].image: 
                self.result.completed_test(command, Result.passed)
            else:
                self.result.completed_test(command, Result.failed, result_data=self.base_context.result)
        except Exception as e:
            self.result.completed_test(command, Result.errored, ResultData(error=e))
        
        # Testing single member action disabled
        try:
            member = DiscordMember(guild=self.base_guild)
            User(member.id).set_action_settings({command.name: False})
            await command(self.cog, self.base_context, [member])
            if self.base_context.result.message.content == f"**{member.display_name}** has disabled this action":
                self.result.completed_test(command, Result.passed)
            else:
                self.result.completed_test(command, Result.failed, result_data=self.base_context.result)
        except Exception as e:
            self.result.completed_test(command, Result.errored, ResultData(error=e))

        # Testing some members action disabled
        try:
            members = [DiscordMember(guild=self.base_guild, id=id) for id in range(randint(4, 10))]
            disabled = 0
            for p, member in enumerate(members):
                if p < len(members) - 1: # We do not want all members to have this action disabled
                    # print(command.name)
                    User(member.id).set_action_settings({command.name: False})
                    disabled += 1
                else:
                    User(member.id).set_action_settings({command.name: True})
            await command(self.cog, self.base_context, members)
            if self.base_context.result.message.embeds and \
                self.base_context.result.message.embeds[0].footer.text == f"{disabled} user{'s' if disabled > 1 else ''} disabled being targetted with this action":
                self.result.completed_test(command, Result.passed)
            else:
                self.result.completed_test(command, Result.failed, result_data=self.base_context.result)
        except Exception as e:
            self.result.completed_test(command, Result.errored, ResultData(error=e))

        # Testing all members action disabled
        try:
            members = [DiscordMember(guild=self.base_guild) for _ in range(randint(4, 10))]
            for member in members:
                User(member.id).set_action_settings({command.name: False})
            await command(self.cog, self.base_context, members)
            if self.base_context.result.message.content == "All members targetted have disabled this action.":
                self.result.completed_test(command, Result.passed)
            else:
                self.result.completed_test(command, Result.failed, result_data=self.base_context.result)
        except Exception as e:
            self.result.completed_test(command, Result.errored, ResultData(error=e))

    async def no_arguments_logic(self, command: Coroutine) -> None:
        "Contains the logic for all action commands which have no arguments and respond with a GIF no matter what"
        # The one and only test needed for this is to make sure the command responds with a GIF in embed
        try:
            await command(self.cog, self.base_context)
            if self.base_context.result.message.embeds and \
                self.base_context.result.message.embeds[0].image:
                self.result.completed_test(command, Result.passed)
            else:
                self.result.completed_test(command, Result.failed, result_data=self.base_context.result)
        except Exception as e:
            self.result.completed_test(command, Result.errored, ResultData(error=e))

    async def hug(self) -> None:
        await self.action_logic(self.cog.hug)

    async def pat(self) -> None:
        await self.action_logic(self.cog.pat)

    async def poke(self) -> None:
        await self.action_logic(self.cog.poke)

    async def slap(self) -> None:
        await self.action_logic(self.cog.slap)

    async def tickle(self) -> None:
        await self.action_logic(self.cog.tickle)

    async def cuddle(self) -> None:
        await self.action_logic(self.cog.cuddle)

    async def dance(self) -> None:
        await self.no_arguments_logic(self.cog.dance)

    async def neko(self) -> None:
        await self.no_arguments_logic(self.cog.neko)

    async def smile(self) -> None:
        await self.no_arguments_logic(self.cog.smile)

    async def blush(self) -> None:
        await self.no_arguments_logic(self.cog.blush)

    async def tail(self) -> None:
        await self.no_arguments_logic(self.cog.tail)

    async def settings(self) -> None:
        # Check when embed times out:
        try:
            self.base_context.timeout_view = True
            await self.cog.settings(self.cog, self.base_context)
            if self.base_context.result.message.embeds and \
                self.base_context.result.message.embeds[0].title == "Settings":
                self.result.completed_test(self.cog.settings, Result.passed)
            else:
                self.result.completed_test(self.cog.settings, Result.failed, result_data=self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.settings, Result.errored, ResultData(error=e))


        # Test trying to save when no settings were changed
        # BUG this is currently only working some times. After hours of debugging I have given up on finding on how to 
        # consistently and correctly test it
        # self.base_context.timeout_view = False
        # try:
        #     async def respond_to_view_no_settings_changed(context: Context):
        #         for child in context.current_view.children:
        #             if child.custom_id == "save":
        #                 await child.callback(ArgumentInteraction(context))
        #                 await context.current_view.on_timeout() # Because wrong save does not stop the view.wait I need to manually stop it here
        #                 context.current_view.stop()

        #     self.base_context.respond_to_view = respond_to_view_no_settings_changed
        #     await wait_for(self.cog.settings(self.cog, self.base_context), timeout=5)
        #     if self.base_context.result.message.content == "You have not changed any settings":
        #         self.result.completed_test(self.cog.settings, Result.passed)
        #     else:
        #         self.result.completed_test(self.cog.settings, Result.failed, result_data=self.base_context.result)
        # except Exception as e:
        #     self.result.completed_test(self.cog.settings, Result.errored, ResultData(error=e))

        # # Test changing one action setting and then saving
        # try:
        #     self.base_context.view_counter = 0

        #     async def respond_to_view_changing(context: Context):
        #         if context.view_counter > 0:
        #             await context.current_view.on_timeout()
        #             return context.current_view.stop()

        #         context.current_view.values = []
        #         context.current_view.timed_out = False

        #         for child in context.current_view.children:
        #             if child.custom_id != "save":
        #                 for option in child.options:
        #                     if option.label != "hug":
        #                         context.current_view.values.append(option.value)

        #         for child in context.current_view.children:
        #             if child.custom_id == "save":
        #                 await child.callback(ArgumentInteraction(context))
        #         context.view_counter += 1 # This is to make sure the test is only run once
                
        #     setattr(self.base_context, "respond_to_view", respond_to_view_changing)
        #     await wait_for(self.cog.settings(self.cog, self.base_context), timeout=15)

        #     if User(self.base_context.author.id).action_settings["hug"] is False and \
        #         self.base_context.result.message.embeds:
        #         self.result.completed_test(self.cog.settings, Result.passed)
        #     else:
        #         self.result.completed_test(self.cog.settings, Result.failed, result_data=self.base_context.result)
        # except Exception as e:
        #     self.result.completed_test(self.cog.settings, Result.errored, ResultData(error=e))