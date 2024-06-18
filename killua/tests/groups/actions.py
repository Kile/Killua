from ..types import *
from ...utils.classes import *
from ..testing import Testing, test
from ...cogs.actions import Actions

from random import randrange, randint
from asyncio import wait


class TestingActions(Testing):

    def __init__(self):
        super().__init__(cog=Actions)


class Settings(TestingActions):

    def __init__(self):
        super().__init__()

    @test
    async def embed_times_out(self) -> None:
        self.base_context.timeout_view = True

        await self.command(self.cog, self.base_context)

        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert (
            self.base_context.result.message.embeds[0].title == "Settings"
        ), self.base_context.result.message.embeds[0].title

    @test
    async def no_settings_changed(self) -> None:

        async def respond_to_view_no_settings_changed(context: Context):
            for child in context.current_view.children:
                if child.custom_id == "save":
                    await child.callback(ArgumentInteraction(context))

        self.base_context.timeout_view = False
        self.base_context.respond_to_view = respond_to_view_no_settings_changed
        await self.command(self.cog, self.base_context)

        assert (
            self.base_context.result.message.content
            == "You have not changed any settings"
        ), self.base_context.result.message.content

    @test
    async def change_one_and_save(self) -> None:

        self.base_context.view_counter = 0

        async def respond_to_view_changing(context: Context):
            if context.view_counter > 0:
                await context.current_view.on_timeout()
                return context.current_view.stop()

            context.current_view.values = []
            context.current_view.timed_out = False

            for child in context.current_view.children:
                if child.custom_id != "save":
                    for option in child.options:
                        if option.label != "hug":
                            context.current_view.values.append(option.value)

            for child in context.current_view.children:
                if child.custom_id == "save":
                    await child.callback(ArgumentInteraction(context))
            context.view_counter += 1  # This is to make sure the test is only run once

        self.base_context.respond_to_view = respond_to_view_changing
        await self.command(self.cog, self.base_context)

        assert User(self.base_context.author.id).action_settings["hug"] is False, User(
            self.base_context.author.id
        ).action_settings["hug"]
        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds


class _ActionCommand(TestingActions):

    def __init__(self, command: str):
        super().__init__()

        self.base_context.command = self.command
        self.__name__ = command  # This is to identify what command it came from

    @test
    async def no_arguments_without_yes(self) -> None:
        Bot.fail_timeout = True
        await self.command(self.cog, self.base_context)

        assert (
            self.base_context.result.message.content
            == f"You provided no one to {self.command.name}.. Should- I {self.command.name} you?"
        ), self.base_context.result.message.content

    @test
    async def no_arguments_with_yes(self) -> None:
        Bot.fail_timeout = False

        resolving_message = Message(
            author=self.base_author, channel=self.base_channel, content="yes"
        )
        await wait(
            {
                self.command(self.cog, self.base_context),
                Bot.resolve("message", resolving_message),
            }
        )

        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert self.base_context.result.message.embeds[
            0
        ].image, self.base_context.result.message.embeds[0].image

    @test
    async def argument_is_author(self) -> None:
        await self.command(self.cog, self.base_context, [self.base_author])

        assert (
            self.base_context.result.message.content
            == "Sorry... you can't use this command on yourself"
        ), self.base_context.result.message.content

    @test
    async def one_member_correctly_supplied(self) -> None:
        member = DiscordMember(guild=self.base_guild)
        await self.command(self.cog, self.base_context, [member])

        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert self.base_context.result.message.embeds[
            0
        ].image, self.base_context.result.message.embeds[0].image

    @test
    async def multiple_members_correctly_supplied(self) -> None:
        members = [
            DiscordMember(guild=self.base_guild) for _ in range(randrange(2, 10))
        ]
        await self.command(self.cog, self.base_context, members)

        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert self.base_context.result.message.embeds[
            0
        ].image, self.base_context.result.message.embeds[0].image

    @test
    async def single_member_action_disabled(self) -> None:
        member = DiscordMember(guild=self.base_guild)
        User(member.id).set_action_settings({self.command.name: False})
        await self.command(self.cog, self.base_context, [member])

        assert (
            self.base_context.result.message.content
            == f"**{member.display_name}** has disabled this action"
        ), self.base_context.result.message.content

    @test
    async def some_members_action_disabled(self) -> None:
        members = [
            DiscordMember(guild=self.base_guild, id=id) for id in range(randint(4, 10))
        ]
        disabled = 0
        for p, member in enumerate(members):
            if (
                p < len(members) - 1
            ):  # We do not want all members to have this action disabled
                User(member.id).set_action_settings({self.command.name: False})
                disabled += 1
            else:
                User(member.id).set_action_settings({self.command.name: True})
        await self.command(self.cog, self.base_context, members)

        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert (
            self.base_context.result.message.embeds[0].footer.text
            == f"{disabled} user{'s' if disabled > 1 else ''} disabled being targetted with this action"
        ), self.base_context.result.message.embeds[0].footer.text

    @test
    async def all_members_action_disabled(self) -> None:
        members = [DiscordMember(guild=self.base_guild) for _ in range(randint(4, 10))]
        for member in members:
            User(member.id).set_action_settings({self.command.name: False})
        await self.command(self.cog, self.base_context, members)

        assert (
            self.base_context.result.message.content
            == "All members targetted have disabled this action."
        ), self.base_context.result.message.content


class _NoArgsCommand(TestingActions):

    def __init__(self, command: str):
        super().__init__()

        self.base_context.command = self.command
        self.__name__ = command

    @test
    async def no_arguments(self) -> None:
        await self.command(self.cog, self.base_context)

        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert self.base_context.result.message.embeds[
            0
        ].image, self.base_context.result.message.embeds[0].image


class Hug(_ActionCommand):
    def __init__(self):
        super().__init__("hug")


class Pat(_ActionCommand):
    def __init__(self):
        super().__init__("pat")


class Poke(_ActionCommand):
    def __init__(self):
        super().__init__("poke")


class Slap(_ActionCommand):
    def __init__(self):
        super().__init__("slap")


class Tickle(_ActionCommand):
    def __init__(self):
        super().__init__("tickle")


class Cuddle(_ActionCommand):
    def __init__(self):
        super().__init__("cuddle")


class Dance(_NoArgsCommand):
    def __init__(self):
        super().__init__("dance")


class Neko(_NoArgsCommand):
    def __init__(self):
        super().__init__("neko")


class Smile(_NoArgsCommand):
    def __init__(self):
        super().__init__("smile")


class Blush(_NoArgsCommand):
    def __init__(self):
        super().__init__("blush")


class Tail(_NoArgsCommand):
    def __init__(self):
        super().__init__("tail")
