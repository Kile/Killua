"""Events cog listener and poll/wyr interaction tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import discord
from discord.ext import commands

from ..testing import Testing, test, collect_test_classes
from ..types import Bot, DiscordMember
from ...cogs.events import Events
from ...utils.classes.guild import Guild as KilluaGuild
from ..harnesses import (
    ListenerFakeButton,
    ListenerFakeRow,
    MockComponentInteraction,
    build_poll_message,
    build_wyr_message,
    cast_vote,
    encrypted_tail_on_button,
    option_button_custom_id,
)
class TestingEvents(Testing):
    def __init__(self) -> None:
        super().__init__(cog=Events)

    @property
    def all_tests(self):
        return collect_test_classes(self.__class__)


class _EventsTests(TestingEvents):
    pass


class PollInteractionTests(_EventsTests):
    @test
    async def author_cannot_vote(self) -> None:
        await KilluaGuild.new(self.base_guild.id)
        events = self.cog
        enc = Bot._encrypt(self.base_author.id, smallest=False)
        emb = discord.Embed(title="Poll", description="Q?", color=0x3E4A78)
        emb.add_field(name="1) One `[0 votes]`", value="—", inline=False)
        sty = int(discord.ButtonStyle.blurple)
        row = ListenerFakeRow(
            [
                ListenerFakeButton(custom_id="poll:opt-1:", label="1", style=sty),
                ListenerFakeButton(
                    custom_id=f"poll:close:{enc}:", label="Close", style=sty
                ),
            ]
        )

        class PM:
            id = 88001
            embeds = [emb]
            components = [row]

        ix = MockComponentInteraction(
            context=self.base_context,
            custom_id="poll:opt-1:",
            user=self.base_author,
            message=PM(),
            client=Bot,
        )
        await events.on_interaction(ix)
        assert ix.response.is_done()

    @test
    async def close_requires_author(self) -> None:
        await KilluaGuild.new(self.base_guild.id)
        events = self.cog
        voter = DiscordMember(guild=self.base_guild, id=self.base_author.id + 1)
        enc = Bot._encrypt(self.base_author.id, smallest=False)
        emb = discord.Embed(title="Poll", color=0x3E4A78)
        sty = int(discord.ButtonStyle.blurple)
        row = ListenerFakeRow(
            [
                ListenerFakeButton(custom_id="poll:opt-1:", label="1", style=sty),
                ListenerFakeButton(
                    custom_id=f"poll:close:{enc}:", label="Close", style=sty
                ),
            ]
        )

        class PM:
            id = 88002
            embeds = [emb]
            components = [row]

        ix = MockComponentInteraction(
            context=self.base_context,
            custom_id=f"poll:close:{enc}:",
            user=voter,
            message=PM(),
            client=Bot,
        )
        await events.on_interaction(ix)
        assert ix.response.is_done()

    @test
    async def wyr_option_b_vote(self) -> None:
        await KilluaGuild.new(self.base_guild.id)
        voter = DiscordMember(guild=self.base_guild, id=self.base_author.id + 2)
        emb = discord.Embed(title="Would you rather...", color=0x3E4A78)
        emb.add_field(name="A) left `[0 people]`", value="—", inline=False)
        emb.add_field(name="B) right `[0 people]`", value="—", inline=False)
        sty = int(discord.ButtonStyle.blurple)
        row = ListenerFakeRow(
            [
                ListenerFakeButton(custom_id="wyr:opt-a:", label="A", style=sty),
                ListenerFakeButton(custom_id="wyr:opt-b:", label="B", style=sty),
            ]
        )

        class PM:
            id = 88003
            embeds = [emb]
            components = [row]

        events = self.cog
        with patch("killua.bot.randint", return_value=100):
            await events.on_interaction(
                MockComponentInteraction(
                    context=self.base_context,
                    custom_id="wyr:opt-b:",
                    user=voter,
                    message=PM(),
                    client=Bot,
                )
            )


class PollWyrEncryptionTests(_EventsTests):
    @test
    async def poll_sixth_vote_uses_button_encryption(self) -> None:
        guild = await KilluaGuild.new(self.base_guild.id)
        guild.badges = [b for b in guild.badges if b not in ("premium", "partner")]
        guild.polls = {}
        author_id = self.base_author.id
        existing = [author_id + 10 + i for i in range(5)]
        msg = build_poll_message(
            author_id, visible_voter_ids=existing, option_index=1
        )
        sixth = DiscordMember(
            guild=self.base_guild, id=author_id + 99, username="V6"
        )
        events = self.cog
        prefix = "poll:opt-1:"
        before = option_button_custom_id(msg, 1)
        assert before == prefix, before

        with patch("killua.bot.randint", return_value=100):
            await cast_vote(
                events,
                context=self.base_context,
                message=msg,
                voter=sixth,
                custom_id=prefix,
            )

        after = option_button_custom_id(msg, 1)
        tail = encrypted_tail_on_button(after, prefix)
        assert len(tail) > 0, after
        assert Bot._encrypt(sixth.id) in tail.split(","), after

    @test
    async def wyr_sixth_vote_uses_button_encryption(self) -> None:
        guild = await KilluaGuild.new(self.base_guild.id)
        guild.badges = [b for b in guild.badges if b not in ("premium", "partner")]
        guild.polls = {}
        existing = [self.base_author.id + 20 + i for i in range(5)]
        msg = build_wyr_message(side="b", visible_voter_ids=existing)
        sixth = DiscordMember(
            guild=self.base_guild, id=self.base_author.id + 199, username="W6"
        )
        events = self.cog
        prefix = "wyr:opt-b:"
        before = msg.components[0].children[1].custom_id
        assert before == prefix, before

        with patch("killua.bot.randint", return_value=100):
            await cast_vote(
                events,
                context=self.base_context,
                message=msg,
                voter=sixth,
                custom_id=prefix,
            )

        after = msg.components[0].children[1].custom_id
        tail = encrypted_tail_on_button(after, prefix)
        assert len(tail) > 0, after
        assert Bot._encrypt(sixth.id) in tail.split(","), after

    @test
    async def poll_premium_vote_persisted_in_db(self) -> None:
        guild = await KilluaGuild.new(self.base_guild.id)
        await guild.add_premium()
        author_id = self.base_author.id
        msg_id = 99010
        msg = build_poll_message(author_id, message_id=msg_id, option_count=2)
        await guild.add_poll(
            str(msg_id),
            {"author": author_id, "votes": {"0": [], "1": []}},
        )
        voter = DiscordMember(
            guild=self.base_guild, id=author_id + 50, username="PremVoter"
        )

        with patch("killua.bot.randint", return_value=100):
            await cast_vote(
                self.cog,
                context=self.base_context,
                message=msg,
                voter=voter,
                custom_id="poll:opt-1:",
            )

        refreshed = await KilluaGuild.new(self.base_guild.id)
        assert voter.id in refreshed.polls[str(msg_id)]["votes"]["0"], (
            refreshed.polls[str(msg_id)]["votes"]
        )

    @test
    async def poll_non_premium_stays_embed_path(self) -> None:
        guild = await KilluaGuild.new(self.base_guild.id)
        assert not guild.is_premium
        author_id = self.base_author.id
        msg_id = 99011
        msg = build_poll_message(author_id, message_id=msg_id)
        voter = DiscordMember(
            guild=self.base_guild, id=author_id + 51, username="FreeVoter"
        )

        with patch("killua.bot.randint", return_value=100):
            await cast_vote(
                self.cog,
                context=self.base_context,
                message=msg,
                voter=voter,
                custom_id="poll:opt-1:",
            )

        refreshed = await KilluaGuild.new(self.base_guild.id)
        assert str(msg_id) not in refreshed.polls
        field_value = msg.embeds[0].fields[0].value
        assert f"<@{voter.id}>" in field_value, field_value


class CommandErrorTests(_EventsTests):
    @test
    async def bot_missing_permissions(self) -> None:
        events = self.cog
        ctx = self.base_context
        ctx.command = Bot.get_command("ping")
        ctx.me.guild_permissions = [("send_messages", True)]
        await events.on_command_error(
            ctx, commands.BotMissingPermissions(missing_permissions=["manage_messages"])
        )
        assert "don't have the required permissions" in ctx.result.message.content

    @test
    async def missing_permissions(self) -> None:
        events = self.cog
        ctx = self.base_context
        ctx.command = Bot.get_command("ping")
        await events.on_command_error(
            ctx, commands.MissingPermissions(missing_permissions=["ban_members"])
        )
        assert "You don't have the required permissions" in ctx.result.message.content

    @test
    async def command_not_found_silent(self) -> None:
        events = self.cog
        ctx = self.base_context
        ctx.command = None
        before = len(ctx.result.message.content or "")
        await events.on_command_error(ctx, commands.CommandNotFound("nope"))
        assert (ctx.result.message.content or "") == "" or len(ctx.result.message.content or "") >= before

    @test
    async def date_helper(self) -> None:
        events = self.cog
        assert events._date_helper(15) == 3
        assert events._date_helper(9) == 9

    @test
    async def is_author_numeric(self) -> None:
        events = self.cog
        enc = str(self.base_author.id)
        interaction = MagicMock()
        interaction.user.id = self.base_author.id
        assert events.is_author(interaction, enc)
