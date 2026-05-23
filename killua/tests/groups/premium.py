from __future__ import annotations

from datetime import datetime, timedelta

from ...utils.classes import User
from ..testing import Testing, test
from ...cogs.premium import Premium
from ...utils.classes.guild import Guild as KilluaGuild
from ...static.constants import DB, PATREON_TIERS


def _reset_guild_state() -> None:
    KilluaGuild.cache.clear()
    DB.guilds.db["guilds"] = []


class TestingPremium(Testing):
    requires_command = True

    def __init__(self):
        super().__init__(cog=Premium)


class Info(TestingPremium):

    def __init__(self):
        super().__init__()

    @test
    async def sends_embed(self) -> None:
        await self.command(self.cog, self.base_context)

        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert (
            self.base_context.result.message.embeds[0].title == "**Support Killua**"
        ), self.base_context.result.message.embeds[0].title


class Guild(TestingPremium):

    def __init__(self):
        super().__init__()

    @test
    async def add_not_premium(self) -> None:
        _reset_guild_state()
        uid = self.base_author.id
        await User.new(uid)
        await DB.teams.update_one(
            {"id": uid}, {"$set": {"badges": [], "premium_guilds": {}}}
        )
        User.cache.pop(uid, None)

        await self.command(self.cog, self.base_context, action="add")

        assert (
            "Sadly you aren't a premium subscriber"
            in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def remove_not_premium_guild(self) -> None:
        _reset_guild_state()

        await self.command(self.cog, self.base_context, action="remove")

        assert (
            "This guild is not a premium guild"
            in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def add_success(self) -> None:
        _reset_guild_state()
        uid = self.base_author.id
        gid = self.base_guild.id
        tier = next(iter(PATREON_TIERS.keys()))
        await User.new(uid)
        await DB.teams.update_one(
            {"id": uid},
            {"$set": {"badges": [tier], "premium_guilds": {}}},
        )
        User.cache.pop(uid, None)

        await self.command(self.cog, self.base_context, action="add")

        assert (
            "Success" in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def add_guild_already_premium(self) -> None:
        _reset_guild_state()
        uid = self.base_author.id
        gid = self.base_guild.id
        tier = next(iter(PATREON_TIERS.keys()))
        await User.new(uid)
        await DB.teams.update_one(
            {"id": uid},
            {"$set": {"badges": [tier], "premium_guilds": {}}},
        )
        User.cache.pop(uid, None)
        g = await KilluaGuild.new(gid)
        await g.add_premium()

        await self.command(self.cog, self.base_context, action="add")

        assert (
            "already has the premium" in self.base_context.result.message.content.lower()
        ), self.base_context.result.message.content

    @test
    async def add_premium_guild_slots_full(self) -> None:
        _reset_guild_state()
        uid = self.base_author.id
        gid = self.base_guild.id
        tier = next(iter(PATREON_TIERS.keys()))
        other_gid = gid + 424242
        await User.new(uid)
        await DB.teams.update_one(
            {"id": uid},
            {
                "$set": {
                    "badges": [tier],
                    "premium_guilds": {str(other_gid): datetime.now()},
                }
            },
        )
        User.cache.pop(uid, None)

        await self.command(self.cog, self.base_context, action="add")

        assert (
            "remove premium perks from one of your other servers"
            in self.base_context.result.message.content.lower()
        ), self.base_context.result.message.content

    @test
    async def remove_success_after_cooldown(self) -> None:
        _reset_guild_state()
        uid = self.base_author.id
        gid = self.base_guild.id
        tier = next(iter(PATREON_TIERS.keys()))
        await User.new(uid)
        g = await KilluaGuild.new(gid)
        await g.add_premium()
        old = datetime.now() - timedelta(days=10)
        await DB.teams.update_one(
            {"id": uid},
            {
                "$set": {
                    "badges": [tier],
                    "premium_guilds": {str(gid): old},
                }
            },
        )
        User.cache.pop(uid, None)

        await self.command(self.cog, self.base_context, action="remove")

        assert (
            "Successfully removed" in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def remove_wrong_subscriber(self) -> None:
        _reset_guild_state()
        uid = self.base_author.id
        gid = self.base_guild.id
        tier = next(iter(PATREON_TIERS.keys()))
        await User.new(uid)
        g = await KilluaGuild.new(gid)
        await g.add_premium()
        await DB.teams.update_one(
            {"id": uid},
            {
                "$set": {
                    "badges": [tier],
                    "premium_guilds": {},
                }
            },
        )
        User.cache.pop(uid, None)

        await self.command(self.cog, self.base_context, action="remove")

        assert (
            "not the one who added" in self.base_context.result.message.content.lower()
        ), self.base_context.result.message.content


class Weekly(TestingPremium):

    def __init__(self):
        super().__init__()

    @test
    async def cooldown_active(self) -> None:
        user = await User.new(self.base_author.id)
        user.weekly_cooldown = datetime.now() + timedelta(days=3)
        await user._update_val("weekly_cooldown", user.weekly_cooldown)

        await self.command(self.cog, self.base_context)

        assert (
            "You can claim your weekly lootbox the next time"
            in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def claim_available(self) -> None:
        user = await User.new(self.base_author.id)
        user.weekly_cooldown = None
        await user._update_val("weekly_cooldown", None)

        await self.command(self.cog, self.base_context)

        assert (
            "Successfully claimed lootbox"
            in self.base_context.result.message.content
        ), self.base_context.result.message.content
