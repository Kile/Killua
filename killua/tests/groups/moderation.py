from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord.ext import commands

from ..types import DiscordMember, DiscordUser, Role
from ..types.permissions import Permissions
from ..testing import Testing, test
from ...cogs.moderation import Moderation
from ...utils.classes.guild import Guild as KilluaGuild
from ...static.constants import DB


def _reset_guild_state():
    KilluaGuild.cache.clear()
    DB.guilds.db["guilds"] = []


class TestingModeration(Testing):
    requires_command = True

    def __init__(self):
        super().__init__(cog=Moderation)


class Prefix(TestingModeration):

    def __init__(self):
        super().__init__()

    @test
    async def show_prefix(self) -> None:
        _reset_guild_state()
        await self.command(self.cog, self.base_context)

        assert (
            self.base_context.result.message.content
            == "The current server prefix is `k!`"
        ), self.base_context.result.message.content

    @test
    async def set_prefix_as_admin(self) -> None:
        _reset_guild_state()
        self.base_context.author.guild_permissions = Permissions(administrator=True)

        await self.command(self.cog, self.base_context, prefix="!!")

        assert (
            self.base_context.result.message.content
            == "Successfully changed server prefix to `!!`!"
        ), self.base_context.result.message.content

    @test
    async def set_prefix_as_non_admin(self) -> None:
        _reset_guild_state()
        self.base_context.author.guild_permissions = Permissions(administrator=False)

        await self.command(self.cog, self.base_context, prefix="!!")

        assert (
            self.base_context.result.message.content
            == "You need `administrator` permissions to change the server prefix!"
        ), self.base_context.result.message.content


class Kick(TestingModeration):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def target_is_bot(self) -> None:
        await self.command(self.cog, self.base_context, member=self.base_context.me)

        assert (
            self.base_context.result.message.content == "Hey!"
        ), self.base_context.result.message.content

    @test
    async def target_is_self(self) -> None:
        await self.command(self.cog, self.base_context, member=self.base_context.author)

        assert (
            self.base_context.result.message.content
            == "You can't kick yourself!"
        ), self.base_context.result.message.content

    @test
    async def kick_success_no_dm(self) -> None:
        victim = DiscordMember(
            id=999010,
            bot=False,
            username="Victim",
            top_role=Role(position=0),
            guild_permissions=Permissions(administrator=False, kick_members=False),
        )
        self.base_author.top_role = Role(position=10)
        self.base_context.me.top_role = Role(position=10)
        victim.kick = AsyncMock()

        await self.command(
            self.cog,
            self.base_context,
            member=victim,
            config=0,
            reason="spam",
        )

        victim.kick.assert_awaited_once()
        content = self.base_context.result.message.content
        assert ":hammer: Kicked **Victim**" in content
        assert "spam" in content
        assert "Operating moderator:" in content

    @test
    async def kick_victim_higher_role_than_author(self) -> None:
        victim = DiscordMember(
            id=999011,
            bot=False,
            username="Boss",
            top_role=Role(position=20),
        )
        self.base_author.top_role = Role(position=10)

        await self.command(self.cog, self.base_context, member=victim, config=0)

        assert (
            "higher role than you" in self.base_context.result.message.content
        ), self.base_context.result.message.content


class Ban(TestingModeration):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def ban_member_success(self) -> None:
        victim = DiscordMember(
            id=999020,
            bot=False,
            username="BadActor",
            top_role=Role(position=0),
        )
        self.base_author.top_role = Role(position=10)
        self.base_context.me.top_role = Role(position=10)
        victim.ban = AsyncMock()

        with patch.object(
            commands.MemberConverter,
            "convert",
            new=AsyncMock(return_value=victim),
        ):
            await self.command(
                self.cog,
                self.base_context,
                member="BadActor",
                config=0,
                reason="ads",
            )

        victim.ban.assert_awaited_once()
        content = self.base_context.result.message.content
        assert ":hammer: Banned **BadActor**" in content
        assert "ads" in content

    @test
    async def ban_numeric_id_success(self) -> None:
        uid = "912345678901234567"
        self.base_context.guild.ban = AsyncMock()

        with patch.object(
            commands.MemberConverter,
            "convert",
            new=AsyncMock(side_effect=commands.MemberNotFound(uid)),
        ):
            await self.command(
                self.cog,
                self.base_context,
                member=uid,
                reason="raid",
            )

        self.base_context.guild.ban.assert_awaited_once()
        content = self.base_context.result.message.content
        assert ":hammer: Banned **" in content
        assert "raid" in content

    @test
    async def ban_numeric_id_http_error(self) -> None:
        uid = "912345678901234568"
        resp = MagicMock()
        resp.status = 400

        async def boom(*a, **k):
            raise discord.HTTPException(resp, {"code": 500, "message": "fail"})

        self.base_context.guild.ban = boom

        with patch.object(
            commands.MemberConverter,
            "convert",
            new=AsyncMock(side_effect=commands.MemberNotFound(uid)),
        ):
            await self.command(self.cog, self.base_context, member=uid)

        assert (
            "Something went wrong" in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def ban_member_higher_role_than_author(self) -> None:
        victim = DiscordMember(
            id=999021,
            bot=False,
            username="ModPlus",
            top_role=Role(position=50),
        )
        self.base_author.top_role = Role(position=10)

        with patch.object(
            commands.MemberConverter,
            "convert",
            new=AsyncMock(return_value=victim),
        ):
            await self.command(
                self.cog, self.base_context, member="x", config=0
            )

        assert "higher role than you" in self.base_context.result.message.content


class Unban(TestingModeration):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def unban_digit_success(self) -> None:
        self.base_context.guild.unban = AsyncMock()
        await self.command(self.cog, self.base_context, member="888877776666555444")

        self.base_context.guild.unban.assert_awaited_once()
        assert "Unbanned user with id" in self.base_context.result.message.content

    @test
    async def unban_digit_http_10013(self) -> None:
        resp = MagicMock()
        resp.status = 404

        async def unban_fail(*a, **k):
            raise discord.HTTPException(
                resp, {"code": 10013, "message": "Unknown User"}
            )

        self.base_context.guild.unban = unban_fail

        await self.command(self.cog, self.base_context, member="111122223333444455")

        assert (
            "No user with the user ID" in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def unban_digit_http_10026(self) -> None:
        resp = MagicMock()
        resp.status = 400

        async def unban_fail(*a, **k):
            raise discord.HTTPException(
                resp, {"code": 10026, "message": "not banned"}
            )

        self.base_context.guild.unban = unban_fail

        await self.command(self.cog, self.base_context, member="222233334444555566")

        assert (
            self.base_context.result.message.content
            == "The user is not currently banned"
        ), self.base_context.result.message.content

    @test
    async def unban_by_username(self) -> None:
        banned_user = DiscordUser(name="exactname", id=333001, username="u1")
        entry = type("BanEntry", (), {"user": banned_user})()
        self.base_context.guild._ban_list = [entry]
        self.base_context.guild.unban = AsyncMock()

        await self.command(self.cog, self.base_context, member="exactname")

        self.base_context.guild.unban.assert_awaited_once_with(entry)
        assert "Unbanned <@333001>" in self.base_context.result.message.content


class Shush(TestingModeration):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def shush_success(self) -> None:
        victim = DiscordMember(
            id=999030,
            bot=False,
            username="Loud",
            top_role=Role(position=0),
        )
        self.base_author.top_role = Role(position=10)
        self.base_context.me.top_role = Role(position=10)
        victim.timeout = AsyncMock()

        await self.command(
            self.cog,
            self.base_context,
            member=victim,
            time=timedelta(seconds=60),
            reason="noise",
        )

        victim.timeout.assert_awaited_once()
        args, kwargs = victim.timeout.await_args
        assert args[0] == timedelta(seconds=60)
        content = self.base_context.result.message.content
        assert "Timeouted" in content
        assert "noise" in content


class Unshush(TestingModeration):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def unshush_not_timed_out(self) -> None:
        victim = DiscordMember(
            id=999040,
            bot=False,
            timed_out=False,
            top_role=Role(position=0),
        )
        self.base_author.top_role = Role(position=10)

        await self.command(self.cog, self.base_context, member=victim)

        assert (
            self.base_context.result.message.content
            == "This user is not timed out"
        ), self.base_context.result.message.content

    @test
    async def unshush_success(self) -> None:
        victim = DiscordMember(
            id=999041,
            bot=False,
            timed_out=True,
            top_role=Role(position=0),
        )
        self.base_author.top_role = Role(position=10)
        self.base_context.me.top_role = Role(position=10)
        victim.timeout = AsyncMock()

        await self.command(self.cog, self.base_context, member=victim, reason="ok")

        victim.timeout.assert_awaited_with(None, reason="ok")
        assert "Removed the timeout" in self.base_context.result.message.content
