"""Additional command and util coverage for large cogs."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from discord.ext import commands

from ..testing import Testing, test, collect_test_classes
from ..types import Bot
from ...cogs.dev import Dev
from ...cogs.events import Events
from ...cogs.shop import Shop
from ...utils.checks import check


class TestingDeep(Testing):
    _menus_registered = False

    def __init__(self) -> None:
        if not TestingDeep._menus_registered:
            TestingDeep._menus_registered = True
        else:
            # Shop menu registration is global; skip re-init on subsequent group runs.
            Shop._init_menus = lambda self: None
        super().__init__(cog=Shop)

    @property
    def all_tests(self):
        return collect_test_classes(self.__class__)


class _DeepTests(TestingDeep):
    requires_command = False


class DevDeep(_DeepTests):
    requires_command = False

    def __init__(self) -> None:
        super().__init__()
        self._dev = Dev(Bot)

    @test
    async def dev_stats_command(self) -> None:
        ctx = self.base_context

        class _StatsCmd:
            name = "stats"

        ctx.command = Bot.get_command("stats") or _StatsCmd()
        with patch.object(self._dev, "initial_top", AsyncMock()) as top:
            await self._dev.stats.callback(self._dev, ctx, "usage")
        top.assert_awaited_once()

class EventsDeep(_DeepTests):
    @test
    async def events_date_and_author(self) -> None:
        events = Events(Bot)
        assert events._date_helper(0) == 0
        ix = MagicMock()
        ix.user.id = self.base_author.id
        assert events.is_author(ix, str(self.base_author.id))

    @test
    async def events_missing_required_arg(self) -> None:
        events = Events(Bot)
        ctx = self.base_context
        ctx.command = Bot.get_command("ping")
        await events.on_command_error(
            ctx, commands.MissingRequiredArgument(param=MagicMock(name="text"))
        )
        assert "missed a required argument" in ctx.result.message.content


class ChecksDeep(_DeepTests):
    @test
    async def check_decorator_wraps_command(self) -> None:
        decorated = check(0)
        assert callable(decorated)
