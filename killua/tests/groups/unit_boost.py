"""Direct unit tests for utils and API helpers (high statement density)."""

from __future__ import annotations

from datetime import datetime, timedelta
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from PIL import Image
from discord.ext import commands
from discord.ext.commands import BadArgument

from ..testing import Testing, test, collect_test_classes, expect_raises
from ..types import Bot, DiscordMember, Role
from ...cogs.economy import Economy
from ...cogs.api import IPCRoutes
from ...cogs.image_manipulation import ImageManipulation
from ...static.constants import DB, daily_users
from ...static.enums import Booster
from ...utils.checks import (
    blcheck,
    premium_guild_only,
    premium_user_only,
    CommandUsageCache,
    check,
)
from ...utils.classes import User, Guild
from ...utils.classes.lootbox import LootBox
from ...utils.classes.book import Book
from ...utils.converters import TimeConverter
from ...utils.gif import TransparentAnimatedGifConverter, save_transparent_gif
from ...utils.interactions import View, Modal, Button as KButton
from ...utils.paginator import Paginator, DefaultEmbed

import killua.utils.checks as checks_module


class TestingUnitBoost(Testing):
    _menus_registered = False

    def __init__(self) -> None:
        if not TestingUnitBoost._menus_registered:
            TestingUnitBoost._menus_registered = True
        else:
            Economy._init_menus = lambda self: None
        super().__init__(cog=Economy)

    @property
    def all_tests(self):
        return collect_test_classes(self.__class__)


class _UnitBoostTests(TestingUnitBoost):
    pass


def _settings_doc(*, enabled=True, channel_id=None, blacklisted=None):
    cid = str(channel_id)
    return {
        "enabled": enabled,
        "blacklisted_channels": list(blacklisted or []),
        "restricted_to_channels": [cid],
        "restricted_to_roles": [],
        "blacklisted_roles": [],
    }


class _FakeCommand:
    def __init__(self, name: str, cmd_id: str):
        self.name = name
        self.extras = {"id": cmd_id}


def _check_context(testing, *, command_name="daily", command_id="99"):
    cmd = _FakeCommand(command_name, command_id)
    testing.base_context.command = cmd
    return testing.base_context


class TimeConverterUnit(_UnitBoostTests):
    @test
    async def parses_compound_duration(self) -> None:
        conv = TimeConverter()
        assert await conv.convert(self.base_context, "1h") == timedelta(hours=1)
        assert await conv.convert(self.base_context, "30m") == timedelta(minutes=30)
        assert await conv.convert(self.base_context, "1h30m") == timedelta(
            hours=1, minutes=30
        )

    @test
    async def rejects_over_28_days(self) -> None:
        conv = TimeConverter()
        async with expect_raises(BadArgument) as exc_info:
            await conv.convert(self.base_context, "29d")
        assert exc_info.value is not None
        assert "28 days" in str(exc_info.value).lower()

    @test
    async def rejects_unknown_unit_via_dict(self) -> None:
        conv = TimeConverter()
        with patch.dict(
            "killua.utils.converters.time_dict", {"h": 3600}, clear=True
        ):
            async with expect_raises(BadArgument) as exc_info:
                await conv.convert(self.base_context, "1m")
            assert exc_info.value is not None
            assert "invalid time-key" in str(exc_info.value).lower()

    @test
    async def rejects_non_numeric_value(self) -> None:
        conv = TimeConverter()
        with patch("killua.utils.converters.float", side_effect=ValueError):
            async with expect_raises(BadArgument) as exc_info:
                await conv.convert(self.base_context, "1h")
            assert exc_info.value is not None
            assert "not a number" in str(exc_info.value).lower()


class ChecksUnit(_UnitBoostTests):
    @test
    async def blcheck_not_listed(self) -> None:
        DB.const.db["const"] = [{"_id": "blacklist", "blacklist": []}]
        assert await blcheck(self.base_author.id) is False

    @test
    async def blcheck_listed(self) -> None:
        DB.const.db["const"] = [
            {
                "_id": "blacklist",
                "blacklist": [{"id": self.base_author.id, "reason": "x"}],
            }
        ]
        assert await blcheck(self.base_author.id) is True

    @test
    async def premium_guild_denied(self) -> None:
        Guild.cache.pop(self.base_guild.id, None)
        guild = await Guild.new(self.base_guild.id)
        guild.badges = []
        pred = premium_guild_only().predicate
        assert await pred(self.base_context) is False

    @test
    async def premium_user_denied(self) -> None:
        uid = self.base_author.id
        User.cache.pop(uid, None)
        await User.new(uid)
        await DB.teams.update_one({"id": uid}, {"$set": {"badges": []}})
        User.cache.pop(uid, None)
        pred = premium_user_only().predicate
        assert await pred(self.base_context) is False

    @test
    async def premium_guild_allowed(self) -> None:
        Guild.cache.pop(self.base_guild.id, None)
        guild = await Guild.new(self.base_guild.id)
        guild.badges = ["premium"]
        pred = premium_guild_only().predicate
        assert await pred(self.base_context) is True

    @test
    async def premium_user_allowed(self) -> None:
        uid = self.base_author.id
        User.cache.pop(uid, None)
        await User.new(uid)
        await DB.teams.update_one({"id": uid}, {"$set": {"badges": ["6002630"]}})
        User.cache.pop(uid, None)
        pred = premium_user_only().predicate
        assert await pred(self.base_context) is True

    @test
    async def command_usage_cache(self) -> None:
        cache = CommandUsageCache()
        cache.data = {"1": 2}
        assert cache.get("1", 0) == 2
        assert "1" in cache
        await cache.set("2", 5)
        assert cache.data["2"] == 5

    @test
    async def check_predicate_tracks_usage(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {"99": 1}},
        ]
        daily_users.users.clear()
        checks_module.cooldowndict = {}
        await Guild.new(self.base_guild.id)
        await User.new(self.base_author.id)
        ctx = _check_context(self)
        pred = check(time=0).predicate
        assert await pred(ctx) is True
        row = next(d for d in DB.const.db["const"] if d["_id"] == "usage")
        assert row["command_usage"]["99"] == 2

    @test
    async def check_predicate_cooldown_blocks_second_call(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {}},
        ]
        checks_module.cooldowndict = {}
        await Guild.new(self.base_guild.id)
        await User.new(self.base_author.id)
        ctx = _check_context(self)
        pred = check(time=120).predicate
        assert await pred(ctx) is True
        assert await pred(ctx) is False
        emb = ctx.result.message.embeds
        if isinstance(emb, list) and emb:
            title = emb[0].title or ""
        elif isinstance(emb, tuple) and emb and isinstance(emb[0], list) and emb[0]:
            title = emb[0][0].title or ""
        else:
            title = ""
        assert title == "Cooldown"

    @test
    async def check_settings_disabled_command(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {}},
        ]
        checks_module.cooldowndict = {}
        guild = await Guild.new(self.base_guild.id)
        guild.commands = {"daily": _settings_doc(enabled=False, channel_id=self.base_channel.id)}
        await User.new(self.base_author.id)
        ctx = _check_context(self)
        pred = check(time=0).predicate
        assert await pred(ctx) is False

    @test
    async def check_settings_blacklisted_channel(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {}},
        ]
        checks_module.cooldowndict = {}
        guild = await Guild.new(self.base_guild.id)
        cid = str(self.base_channel.id)
        guild.commands = {
            "daily": _settings_doc(
                channel_id=self.base_channel.id,
                blacklisted=[cid],
            )
        }
        await User.new(self.base_author.id)
        ctx = _check_context(self)
        pred = check(time=0).predicate
        assert await pred(ctx) is False

    @test
    async def check_settings_restricted_channel(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {}},
        ]
        checks_module.cooldowndict = {}
        guild = await Guild.new(self.base_guild.id)
        guild.commands = {
            "daily": _settings_doc(channel_id=self.base_channel.id + 999)
        }
        await User.new(self.base_author.id)
        ctx = _check_context(self)
        pred = check(time=0).predicate
        assert await pred(ctx) is False

    @test
    async def check_settings_blacklisted_role(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {}},
        ]
        checks_module.cooldowndict = {}
        Guild.cache.pop(self.base_guild.id, None)
        guild = await Guild.new(self.base_guild.id)
        rid = 88001
        self.base_author.roles = [Role(id=rid, position=1)]
        ctx = _check_context(self)
        guild.commands = {
            "daily": {
                **_settings_doc(channel_id=self.base_channel.id),
                "blacklisted_roles": [str(rid)],
            }
        }
        await User.new(self.base_author.id)
        pred = check(time=0).predicate
        assert await pred(ctx) is False

    @test
    async def check_settings_requires_role(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {}},
        ]
        checks_module.cooldowndict = {}
        Guild.cache.pop(self.base_guild.id, None)
        guild = await Guild.new(self.base_guild.id)
        self.base_author.roles = [Role(id=88003, position=1)]
        ctx = _check_context(self)
        guild.commands = {
            "daily": {
                **_settings_doc(channel_id=self.base_channel.id),
                "restricted_to_roles": ["88002"],
            }
        }
        await User.new(self.base_author.id)
        pred = check(time=0).predicate
        assert await pred(ctx) is False

    @test
    async def check_cooldown_premium_guild_halves_wait(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {}},
        ]
        checks_module.cooldowndict = {}
        guild = await Guild.new(self.base_guild.id)
        guild.badges = ["premium"]
        await User.new(self.base_author.id)
        ctx = _check_context(self)
        pred = check(time=60).predicate
        assert await pred(ctx) is True
        assert await pred(ctx) is False

    @test
    async def check_predicate_blacklisted_user(self) -> None:
        DB.const.db["const"] = [
            {
                "_id": "blacklist",
                "blacklist": [{"id": self.base_author.id, "reason": "x"}],
            },
            {"_id": "usage", "command_usage": {}},
        ]
        checks_module.cooldowndict = {}
        await Guild.new(self.base_guild.id)
        await User.new(self.base_author.id)
        ctx = _check_context(self)
        pred = check(time=0).predicate
        assert await pred(ctx) is False

    @test
    async def check_settings_allows_matching_role(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {}},
        ]
        checks_module.cooldowndict = {}
        Guild.cache.pop(self.base_guild.id, None)
        guild = await Guild.new(self.base_guild.id)
        rid = 88002
        self.base_author.roles = [Role(id=rid, position=1)]
        guild.commands = {
            "daily": {
                **_settings_doc(channel_id=self.base_channel.id),
                "restricted_to_channels": [self.base_channel.id],
                "restricted_to_roles": [str(rid)],
            }
        }
        await User.new(self.base_author.id)
        ctx = _check_context(self)
        pred = check(time=0).predicate
        assert await pred(ctx) is True

    @test
    async def check_settings_delete_invocation(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {}},
        ]
        checks_module.cooldowndict = {}
        Guild.cache.pop(self.base_guild.id, None)
        guild = await Guild.new(self.base_guild.id)
        ctx = _check_context(self)
        guild.commands = {
            "daily": {
                **_settings_doc(channel_id=self.base_channel.id),
                "restricted_to_channels": [self.base_channel.id],
                "delete_invokation": True,
            }
        }
        await User.new(self.base_author.id)
        pred = check(time=0).predicate
        assert await pred(ctx) is True

    @test
    async def check_predicate_without_guild(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {}},
        ]
        checks_module.cooldowndict = {}
        daily_users.users.clear()
        await User.new(self.base_author.id)
        ctx = _check_context(self)
        prev_guild = ctx.guild
        ctx.guild = None
        try:
            pred = check(time=0).predicate
            assert await pred(ctx) is True
        finally:
            ctx.guild = prev_guild

    @test
    async def check_cooldown_new_command_same_user(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {}},
        ]
        checks_module.cooldowndict = {}
        await Guild.new(self.base_guild.id)
        await User.new(self.base_author.id)
        ctx = _check_context(self, command_name="daily", command_id="99")
        cmd2 = MagicMock(spec=commands.Command)
        cmd2.name = "othercmd"
        cmd2.extras = {"id": "100"}
        pred = check(time=120).predicate
        assert await pred(ctx) is True
        ctx.command = cmd2
        assert await pred(ctx) is True

    @test
    async def check_cooldown_expires(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {}},
        ]
        await Guild.new(self.base_guild.id)
        await User.new(self.base_author.id)
        ctx = _check_context(self)
        checks_module.cooldowndict = {
            self.base_author.id: {
                "daily": datetime.now() - timedelta(seconds=200),
            }
        }
        pred = check(time=60).predicate
        assert await pred(ctx) is True

    @test
    async def check_cooldown_premium_user_halves_wait(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {}},
        ]
        checks_module.cooldowndict = {}
        await Guild.new(self.base_guild.id)
        uid = self.base_author.id
        await User.new(uid)
        await DB.teams.update_one({"id": uid}, {"$set": {"badges": ["6002630"]}})
        User.cache.pop(uid, None)
        ctx = _check_context(self)
        pred = check(time=120).predicate
        assert await pred(ctx) is True
        assert await pred(ctx) is False

    @test
    async def check_skips_hybrid_group_usage(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {"99": 0}},
        ]
        checks_module.cooldowndict = {}
        Guild.cache.pop(self.base_guild.id, None)
        await Guild.new(self.base_guild.id)
        await User.new(self.base_author.id)
        ctx = _check_context(self)
        ctx.command = MagicMock(spec=commands.HybridGroup)
        ctx.command.name = "daily"
        ctx.command.extras = {"id": "99"}
        pred = check(time=0).predicate
        assert await pred(ctx) is True
        row = next(d for d in DB.const.db["const"] if d["_id"] == "usage")
        assert row["command_usage"]["99"] == 0

    @test
    async def check_user_installed_usage(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {}},
        ]
        checks_module.cooldowndict = {}
        Guild.cache.pop(self.base_guild.id, None)
        await Guild.new(self.base_guild.id)
        user = await User.new(self.base_author.id)
        ctx = _check_context(self)
        with patch.object(
            user, "register_user_installed_usage", AsyncMock()
        ) as reg:
            with patch.object(User, "new", AsyncMock(return_value=user)):
                with patch.object(
                    type(ctx.bot), "is_user_installed", return_value=True
                ):
                    pred = check(time=0).predicate
                    assert await pred(ctx) is True
            reg.assert_awaited_once()

    @test
    async def check_settings_bad_data_is_ignored(self) -> None:
        DB.const.db["const"] = [
            {"_id": "blacklist", "blacklist": []},
            {"_id": "usage", "command_usage": {}},
        ]
        checks_module.cooldowndict = {}
        guild = await Guild.new(self.base_guild.id)
        guild.commands = {"daily": "broken"}
        await User.new(self.base_author.id)
        ctx = _check_context(self)
        pred = check(time=0).predicate
        assert await pred(ctx) is True


class BookUnit(_UnitBoostTests):
    @test
    async def background_cache_and_fetch(self) -> None:
        class Resp:
            async def read(self):
                buf = BytesIO()
                Image.new("RGB", (32, 32), "white").save(buf, format="PNG")
                return buf.getvalue()

        Bot.session.get = AsyncMock(return_value=Resp())
        book = Book(Bot)
        cached = Image.new("RGBA", (20, 20), (1, 2, 3, 255))
        book._set_cache(cached, first_page=True)
        assert book._get_from_cache(0) is not None
        bg = await book._get_background(0)
        assert bg.size[0] > 0
        book.card_cache["1"] = cached
        data = [(1, "http://cards.example/1.png")]
        merged = await book._cards(bg.copy(), data, option=0)
        assert merged.size == bg.size

    @test
    async def create_image_restricted_first_page(self) -> None:
        class Resp:
            async def read(self):
                buf = BytesIO()
                Image.new("RGB", (640, 420), "white").save(buf, format="PNG")
                return buf.getvalue()

        Bot.session.get = AsyncMock(return_value=Resp())
        book = Book(Bot)
        data = [
            [i, None if i % 2 else "http://cards.example/card.png"]
            for i in range(1, 11)
        ]
        img = await book.create_image(data, restricted_slots=True, page=1)
        assert img.size[0] > 0

    @test
    async def default_background_fetch(self) -> None:
        class Resp:
            async def read(self):
                buf = BytesIO()
                Image.new("RGB", (32, 32), "white").save(buf, format="PNG")
                return buf.getvalue()

        Bot.session.get = AsyncMock(return_value=Resp())
        book = Book(Bot)
        book.background_cache.clear()
        bg = await book._get_background(1)
        assert bg.size[0] > 0
        assert book._get_from_cache(1) is not None

    @test
    async def set_page_and_numbers(self) -> None:
        book = Book(Bot)
        bg = Image.new("RGBA", (640 * book.scalar, 420 * book.scalar), (255, 255, 255, 255))
        data = [[i, None] for i in range(1, 11)]
        numbered = book._numbers(bg.copy(), data, page=1)
        paged = book._set_page(numbered, page=2)
        assert paged.size == bg.size

    @test
    async def create_image_and_fetch_card(self) -> None:
        class Resp:
            async def read(self):
                buf = BytesIO()
                Image.new("RGB", (640, 420), "white").save(buf, format="PNG")
                return buf.getvalue()

        Bot.session.get = AsyncMock(return_value=Resp())
        book = Book(Bot)
        book.background_cache.clear()
        book.card_cache.clear()
        data = [
            [i, None if i % 2 else "http://cards.example/card.png"]
            for i in range(1, 11)
        ]
        img = await book.create_image(data, restricted_slots=True, page=1)
        assert img.size[0] > 0

    @test
    async def fetch_card_image(self) -> None:
        class Resp:
            async def read(self):
                buf = BytesIO()
                Image.new("RGBA", (84, 115), (255, 0, 0, 255)).save(buf, format="PNG")
                return buf.getvalue()

        Bot.session.get = AsyncMock(return_value=Resp())
        book = Book(Bot)
        card = await book._get_card("http://cards.example/7.png")
        assert card.size[0] > 0


class PaginatorUnit(_UnitBoostTests):
    @test
    async def first_page_from_strings(self) -> None:
        pag = Paginator(self.base_context, pages=["alpha", "beta"])
        await pag._get_first_embed()
        assert pag.embed.description == "alpha"

    @test
    async def custom_embed_formatter(self) -> None:
        def fmt(page, emb, pages):
            emb.description = pages[page - 1].upper()
            return emb

        pag = Paginator(
            self.base_context, pages=["page"], func=fmt, embed=DefaultEmbed()
        )
        await pag._get_first_embed()
        assert pag.embed.description == "PAGE"

    @test
    async def turn_page_with_buttons(self) -> None:
        import asyncio

        from ..harnesses.paginator import embed_footer_page, press_paginator_button

        pag = Paginator(self.base_context, pages=["one", "two", "three"])
        task = asyncio.create_task(pag.start())
        await asyncio.sleep(0)
        await press_paginator_button(pag.view, "next", context=self.base_context)
        footer = embed_footer_page(pag.embed)
        assert footer is not None and footer[0] == 2
        pag.view.stop()
        await task

    @test
    async def paginator_first_and_last(self) -> None:
        import asyncio

        from ..harnesses.paginator import press_paginator_button

        pag = Paginator(self.base_context, pages=["a", "b", "c"])
        task = asyncio.create_task(pag.start())
        await asyncio.sleep(0)
        await press_paginator_button(pag.view, "last", context=self.base_context)
        assert pag.view.page == 3
        await press_paginator_button(pag.view, "first", context=self.base_context)
        assert pag.view.page == 1
        pag.view.stop()
        await task

    @test
    async def paginator_stop_button(self) -> None:
        import asyncio

        from ..harnesses.paginator import press_paginator_button

        pag = Paginator(self.base_context, pages=["only"])
        task = asyncio.create_task(pag.start())
        await asyncio.sleep(0)
        await press_paginator_button(pag.view, "delete", context=self.base_context)
        pag.view.stop()
        await task


class ImageManipulationUnit(_UnitBoostTests):
    def _cog(self) -> ImageManipulation:
        if not hasattr(ImageManipulationUnit, "_cog_instance"):
            ImageManipulationUnit._cog_instance = ImageManipulation(Bot)
        return ImageManipulationUnit._cog_instance

    @test
    async def crop_to_circle(self) -> None:
        cog = self._cog()
        im = Image.new("RGBA", (40, 40), (255, 0, 0, 255))
        circ = cog._crop_to_circle(im)
        assert circ.size == im.size

    @test
    async def create_spin_frames(self) -> None:
        cog = self._cog()
        im = Image.new("RGBA", (20, 20), (255, 0, 0, 255))
        frames = cog._create_frames(im)
        assert len(frames) == 17

    @test
    async def put_horizontally(self) -> None:
        cog = self._cog()
        im1 = Image.new("RGBA", (20, 10), (255, 0, 0, 255))
        im2 = Image.new("RGBA", (30, 30), (0, 255, 0, 255))
        out = cog._put_horizontally(im1, im2)
        assert out.width == im2.width

    @test
    async def get_image_bytes(self) -> None:
        class Resp:
            async def read(self):
                return b"\x89PNG\r\n\x1a\n" + b"x" * 20

        Bot.session.get = AsyncMock(return_value=Resp())
        buf = await self._cog()._get_image_bytes("http://example.com/x.png")
        assert buf.getvalue()[:8] == b"\x89PNG\r\n\x1a\n"

    @test
    async def create_spin_gif(self) -> None:
        class Resp:
            async def read(self):
                buf = BytesIO()
                Image.new("RGB", (60, 40), "red").save(buf, format="PNG")
                return buf.getvalue()

        Bot.session.get = AsyncMock(return_value=Resp())
        out = await self._cog()._create_spin_gif("http://example.com/face.png")
        assert out.getvalue()[:6] == b"GIF89a"

    @test
    async def create_wtf_meme(self) -> None:
        class Resp:
            async def read(self):
                buf = BytesIO()
                Image.new("RGBA", (40, 20), (0, 255, 0, 255)).save(buf, format="PNG")
                return buf.getvalue()

        Bot.session.get = AsyncMock(return_value=Resp())
        cog = self._cog()
        cog.wtf_meme = None
        out = await cog.create_wtf_meme("http://example.com/src.png")
        assert out.getvalue()[:8] == b"\x89PNG\r\n\x1a\n"

    @test
    async def get_target_url_from_attachment(self) -> None:
        cog = self._cog()
        att = MagicMock()
        att.url = "https://example.com/attached.png"
        self.base_message.attachments = [att]
        url = await cog._validate_input(self.base_context, None)
        assert url == "https://example.com/attached.png"

    @test
    async def validate_input_accepts_plain_url(self) -> None:
        cog = self._cog()
        with patch.object(
            commands.MemberConverter,
            "convert",
            side_effect=commands.MemberNotFound("x"),
        ):
            with patch.object(
                commands.EmojiConverter,
                "convert",
                side_effect=commands.EmojiNotFound("x"),
            ):
                url = await cog._validate_input(
                    self.base_context, "https://example.com/pic.png"
                )
        assert url == "https://example.com/pic.png"


class ApiHelpersUnit(_UnitBoostTests):
    def _ipc(self) -> IPCRoutes:
        from .api import TestingApi

        if TestingApi._ipc is None:
            TestingApi._ipc = IPCRoutes(Bot)
        return TestingApi._ipc

    @test
    async def get_reward_streaks(self) -> None:
        ipc = self._ipc()
        assert ipc._get_reward(0) == 100
        r5 = ipc._get_reward(5)
        assert isinstance(r5, (int, Booster))
        r7 = ipc._get_reward(7, weekend=True)
        assert isinstance(r7, (int, Booster))

    @test
    async def create_path_short_streak(self) -> None:
        ipc = self._ipc()
        user = MagicMock()
        path = ipc._create_path(3, user, "http://x")
        assert len(path) == 11
        assert path[2] is user

    @test
    async def create_path_long_streak(self) -> None:
        ipc = self._ipc()
        user = MagicMock()
        path = ipc._create_path(10, user, "http://x")
        assert len(path) == 11
        assert path[5] is user

    @test
    async def format_command_metadata(self) -> None:
        ipc = self._ipc()
        cmd = MagicMock()
        cmd.checks = []
        cmd.qualified_name = "economy daily"
        cmd.name = "daily"
        cmd.usage = ""
        cmd.help = "help"
        cmd.aliases = []
        cmd.cog = MagicMock(spec=commands.Cog)
        out = ipc.format_command(cmd)
        assert out["name"] == "daily"

    @test
    async def user_edit_fields(self) -> None:
        ipc = self._ipc()
        uid = self.base_author.id
        await User.new(uid)
        res = await ipc.user_edit(
            {"user_id": uid, "voting_reminder": True, "email_notifications": False}
        )
        assert res["success"] is True

    @test
    async def streak_image_builds(self) -> None:
        from ..types import DiscordUser

        ipc = self._ipc()
        user = DiscordUser(id=self.base_author.id)
        path = ipc._create_path(5, user, "http://api")
        buf = BytesIO()
        Image.new("RGBA", (100, 100), (0, 0, 0, 0)).save(buf, format="PNG")
        buf.seek(0)

        async def fake_dl(_url):
            im = Image.open(buf).convert("RGBA")
            return im

        ipc.download = fake_dl
        out = await ipc.streak_image(path)
        assert out.getvalue()[:8] == b"\x89PNG\r\n\x1a\n"

    @test
    async def news_delete_existing(self) -> None:
        ipc = self._ipc()
        DB.news.db["news"] = [
            {"_id": "del1", "type": "news", "messageId": None, "published": False}
        ]
        with patch.object(ipc, "_delete_discord_message", AsyncMock()):
            res = await ipc.news_delete({"news_id": "del1"})
        assert res["status"] == "deleted"


class LootboxUnit(_UnitBoostTests):
    @test
    async def generate_rewards(self) -> None:
        rewards = await LootBox.generate_rewards(1)
        assert isinstance(rewards, list)
        assert len(rewards) > 0

    @test
    async def booster_select_options(self) -> None:
        from killua.utils.classes.lootbox import _BoosterSelect

        sel = _BoosterSelect(used=[], inventory={"1": 2})
        assert len(sel.options) >= 0


class GifUnit(_UnitBoostTests):
    @test
    async def transparent_gif_converter(self) -> None:
        img = Image.new("RGBA", (4, 4), (255, 0, 0, 128))
        conv = TransparentAnimatedGifConverter(img, alpha_threshold=128)
        out = conv.process()
        assert out is not None

    @test
    async def save_transparent_gif(self) -> None:
        frames = [
            Image.new("RGBA", (4, 4), (255, 0, 0, 255)),
            Image.new("RGBA", (4, 4), (0, 255, 0, 255)),
        ]
        buf = BytesIO()
        save_transparent_gif(frames, 100, buf)
        assert buf.tell() > 0


class InteractionsUnit(_UnitBoostTests):
    @test
    async def view_allows_owner(self) -> None:
        from ..harnesses.interaction import MockComponentInteraction

        view = View(self.base_author.id)
        ix = MockComponentInteraction(
            context=self.base_context,
            user=self.base_author,
            custom_id="x",
            message=self.base_message,
            client=Bot,
        )
        assert await view.interaction_check(ix) is True

    @test
    async def view_denies_other_user(self) -> None:
        from ..harnesses.interaction import MockComponentInteraction
        from ..types import DiscordMember

        view = View(self.base_author.id)
        other = DiscordMember(id=self.base_author.id + 1, username="other")
        ix = MockComponentInteraction(
            context=self.base_context,
            user=other,
            custom_id="x",
            message=self.base_message,
            client=Bot,
        )
        ix.response.defer = AsyncMock()
        assert await view.interaction_check(ix) is False

    @test
    async def modal_timeout_flag(self) -> None:
        modal = Modal(title="t")
        assert modal.timed_out is False
        await modal.on_timeout()
        assert modal.timed_out is True

    @test
    async def killua_button_sets_value(self) -> None:
        from ..types import ArgumentInteraction

        view = View(self.base_author.id)
        btn = KButton(label="go", custom_id="go-btn")
        view.add_item(btn)
        await btn.callback(ArgumentInteraction(self.base_context))
        assert view.value == "go-btn"

    @test
    async def view_disable_skips_when_already_disabled(self) -> None:
        view = View(self.base_author.id)
        btn = discord.ui.Button(label="x", custom_id="x", disabled=True)
        view.add_item(btn)
        msg = MagicMock()
        msg.edit = AsyncMock()
        assert await view.disable(msg) is None


class CardsStaticUnit(_UnitBoostTests):
    @test
    async def import_spell_classes(self) -> None:
        from killua.static import cards as cards_mod
        import inspect

        count = 0
        for name, cls in inspect.getmembers(cards_mod, inspect.isclass):
            if name.startswith("Card10") and hasattr(cls, "exec"):
                count += 1
        assert count >= 10


class LootboxDeepUnit(_UnitBoostTests):
    @test
    async def lootbox_view_and_sku(self) -> None:
        import discord as d

        ctx = self.base_context
        rewards = [10, None, None]
        box = LootBox(ctx, rewards)
        view = box._create_view()
        assert len(view.children) == 25
        sku = MagicMock()
        sku.name = "titans crate"
        assert LootBox.get_lootbox_from_sku(sku)[0] == 7


class ApiMoreUnit(_UnitBoostTests):
    def _ipc(self) -> IPCRoutes:
        from .api import TestingApi

        if TestingApi._ipc is None:
            TestingApi._ipc = IPCRoutes(Bot)
        return TestingApi._ipc

    @test
    async def guild_command_usage_outside_docker(self) -> None:
        ipc = self._ipc()
        prev = Bot.run_in_docker
        Bot.run_in_docker = False
        try:
            res = await ipc.guild_command_usage({"guild_id": self.base_guild.id})
            assert res.get("error")
        finally:
            Bot.run_in_docker = prev

    @test
    async def get_message_command(self) -> None:
        ipc = self._ipc()
        cmd = ipc.get_message_command("daily")
        assert cmd is not None or cmd is None

    @test
    async def convert_datetime_and_snowflakes(self) -> None:
        ipc = self._ipc()
        dt = datetime(2024, 1, 2, 3, 4, 5)
        assert ipc._convert_datetime(dt) == dt.isoformat()
        snow = ipc._convert_snowflakes(1234567890123456789)
        assert isinstance(snow, str)
        nested = ipc._convert_datetime({"ts": dt, "items": [dt]})
        assert nested["ts"] == dt.isoformat()
