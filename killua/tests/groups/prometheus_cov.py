"""Prometheus cog metric paths with mocks (no HTTP server)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from ..testing import Testing, test, collect_test_classes
from ..types import Bot
from ...cogs.prometheus import PrometheusCog
from ...static.constants import API_ROUTES


class TestingPrometheus(Testing):
    def __init__(self) -> None:
        super().__init__(cog=PrometheusCog)

    @property
    def all_tests(self):
        return collect_test_classes(self.__class__)


class _PromTests(TestingPrometheus):
    requires_command = False


class PrometheusHandlerTests(_PromTests):
    @test
    async def update_api_stats(self) -> None:
        cog = PrometheusCog(Bot, port=9999)
        route = next(iter(API_ROUTES))
        payload = {
            "ipc": {"response_time": 12},
            "usage": {
                route: {
                    "request_count": 10,
                    "successful_responses": 9,
                    "failed_responses": 1,
                },
                "spam": {"request_count": 0},
            },
        }

        class Resp:
            status = 200
            headers = {"X-Response-Time": "5ms"}

            async def json(self):
                return payload

        Bot.session.get = AsyncMock(return_value=Resp())
        await cog.update_api_stats()
        assert cog.api_previous.get(route, {}).get("request_count") == 10

    @test
    async def update_api_stats_non_200(self) -> None:
        cog = PrometheusCog(Bot, port=9999)

        class Resp:
            status = 500

        Bot.session.get = AsyncMock(return_value=Resp())
        await cog.update_api_stats()

    @test
    async def on_connect_and_disconnect(self) -> None:
        cog = PrometheusCog(Bot, port=9999)
        await cog.on_connect()
        await cog.on_disconnect()
        await cog.on_shard_ready(0)
        await cog.on_shard_disconnect(0)

    @test
    async def on_ready_starts_server_in_docker(self) -> None:
        cog = PrometheusCog(Bot, port=9999)
        Bot.run_in_docker = True
        try:
            with patch.object(cog, "init_gauges", AsyncMock()):
                with patch.object(cog, "start_prometheus") as start:
                    await cog.on_ready()
                    await cog.on_ready()
                    start.assert_called_once()
        finally:
            Bot.run_in_docker = False
            cog.initial = False

    @test
    async def on_command_increments(self) -> None:
        cog = PrometheusCog(Bot, port=9999)
        ctx = self.base_context
        cmd = Bot.get_command("ping")
        if cmd is None:

            class _PingCmd:
                name = "ping"
                qualified_name = "ping"
                extras = {"id": 1}
                cog = None

            cmd = _PingCmd()
        else:
            cmd.extras = dict(getattr(cmd, "extras", None) or {})
            cmd.extras["id"] = 1
        ctx.command = cmd
        await cog.on_command(ctx)
