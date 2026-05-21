from ..types import *
from ...utils.classes import *
from ..testing import Testing, test
from ...cogs.actions import Actions, AnimeAsset, ArtistAsset

from random import randrange, randint
from asyncio import create_task, wait
from unittest.mock import patch

from ..types.utils import get_random_discord_id
from ..harnesses import MockComponentInteraction


def _embed0_actions(message):
    raw = message.embeds
    if isinstance(raw, list) and raw:
        return raw[-1]
    if isinstance(raw, tuple) and raw:
        inner = raw[0]
        if isinstance(inner, list) and inner:
            return inner[-1]
    return None


class TestingActions(Testing):
    requires_command = True

    def __init__(self):
        super().__init__(cog=Actions)
        self._mock_cog_externals()

    def _mock_cog_externals(self):
        """Mocks external API calls on the cog so tests work offline"""
        cog = self.cog

        async def mock_request_action(endpoint):
            return AnimeAsset(url="https://example.com/test.gif", anime_name="Test Anime")

        async def mock_get_image_url(endpoint):
            return ArtistAsset(url="http://localhost:6060/image/test.gif", artist=None, featured=False)

        cog.request_action = mock_request_action
        cog._get_image_url = mock_get_image_url


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
        from ...static.constants import ACTIONS

        self.base_context.view_counter = 0
        self.base_context.timeout_view = False

        # Select every action except hug (disables hug), then save — same as production UI.
        select_values = [k for k in ACTIONS.keys() if k != "hug"]

        async def respond_to_view_changing(context: Context):
            if context.view_counter > 0:
                await context.current_view.on_timeout()
                return context.current_view.stop()

            select_ix = ArgumentInteraction(
                context, data={"values": select_values}
            )
            for child in context.current_view.children:
                if getattr(child, "custom_id", None) == "select":
                    await child.callback(select_ix)
            context.current_view.interaction = select_ix
            for child in context.current_view.children:
                if getattr(child, "custom_id", None) == "save":
                    await child.callback(ArgumentInteraction(context))
            context.view_counter += 1

        self.base_context.respond_to_view = respond_to_view_changing
        await self.command(self.cog, self.base_context)

        user = await User.new(self.base_context.author.id)
        assert user.action_settings["hug"] is False, user.action_settings["hug"]
        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds


class _ActionCommand(TestingActions):

    def __init__(self, command: str):
        super().__init__()

        self.base_context.command = self.command
        self.__name__ = command

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
                create_task(self.command(self.cog, self.base_context)),
                create_task(Bot.resolve("message", resolving_message)),
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
        user = await User.new(member.id)
        await user.set_action_settings({self.command.name: False})
        await self.command(self.cog, self.base_context, [member])

        assert (
            self.base_context.result.message.content
            == f"All members targeted have disabled this action."
        ), self.base_context.result.message.content

    @test
    async def some_members_action_disabled(self) -> None:
        members = [
            DiscordMember(guild=self.base_guild, id=get_random_discord_id()) for _ in range(randint(4, 10))
        ]
        disabled = 0
        for p, member in enumerate(members):
            user = await User.new(member.id)
            if p < len(members) - 1:
                await user.set_action_settings({self.command.name: False})
                disabled += 1
            else:
                await user.set_action_settings({self.command.name: True})
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
            user = await User.new(member.id)
            await user.set_action_settings({self.command.name: False})
        await self.command(self.cog, self.base_context, members)

        assert (
            self.base_context.result.message.content
            == "All members targeted have disabled this action."
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

    @test
    async def hug_back_button_invokes_return_hug(self) -> None:
        """Path B: Actions.on_interaction when target presses Hug back (see killua/tests/component_interaction.py)."""
        target = DiscordMember(guild=self.base_guild, id=self.base_author.id + 5000)
        self.base_guild.members = [self.base_author, target]
        await User.new(self.base_author.id)
        await User.new(target.id)

        enc = Bot._encrypt(target.id)
        cid = f"action:hug:{self.base_author.id}:{enc}:"

        with patch("killua.bot.randint", return_value=100):
            await self.command(self.cog, self.base_context, [target])

        msg = self.base_context.result.message
        assert msg.embeds, msg.embeds

        ix = MockComponentInteraction(
            context=self.base_context,
            custom_id=cid,
            user=target,
            message=msg,
            client=Bot,
        )
        with patch("killua.bot.randint", return_value=100):
            await self.cog.on_interaction(ix)

        assert self.base_context.result.message.embeds, (
            self.base_context.result.message.embeds
        )
        emb = _embed0_actions(self.base_context.result.message)
        assert emb is not None
        t = emb.title or ""
        assert self.base_author.display_name in t, t
        assert target.display_name in t, t


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


class Smile(_NoArgsCommand):
    def __init__(self):
        super().__init__("smile")


class Blush(_NoArgsCommand):
    def __init__(self):
        super().__init__("blush")


class Cry(_NoArgsCommand):
    def __init__(self):
        super().__init__("cry")


class Smug(_NoArgsCommand):
    def __init__(self):
        super().__init__("smug")


class Yawn(_NoArgsCommand):
    def __init__(self):
        super().__init__("yawn")


class Nope(_NoArgsCommand):
    def __init__(self):
        super().__init__("nope")
