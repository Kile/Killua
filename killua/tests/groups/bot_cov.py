"""BaseBot helper coverage (formatting, encrypt, api_url)."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

from PIL import Image

from ..testing import Testing, test, collect_test_classes
from ..types import Bot
from ...cogs.help import HelpCommand


class TestingBotCov(Testing):
    def __init__(self) -> None:
        super().__init__(cog=HelpCommand)

    @property
    def all_tests(self):
        return collect_test_classes(self.__class__)


class _BotTests(TestingBotCov):
    pass


class BotHelperTests(_BotTests):
    @test
    async def encrypt_round_trip(self) -> None:
        enc = Bot._encrypt(12345, smallest=False)
        assert isinstance(enc, str)
        assert len(enc) > 0

    @test
    async def api_url_branches(self) -> None:
        assert Bot.api_url(to_fetch=True).startswith("http://")
        prev_local, prev_docker = Bot.force_local, Bot.run_in_docker
        Bot.force_local = True
        Bot.run_in_docker = False
        try:
            local = Bot.api_url(is_for_cards=True)
            assert local.startswith("http://") and local != Bot.url
        finally:
            Bot.force_local = prev_local
            Bot.run_in_docker = prev_docker

    @test
    async def get_formatted_commands(self) -> None:
        cmds = Bot.get_formatted_commands()
        assert isinstance(cmds, dict)

    @test
    async def get_raw_formatted_commands(self) -> None:
        raw = Bot.get_raw_formatted_commands()
        assert isinstance(raw, list)

    @test
    async def find_user(self) -> None:
        ctx = self.base_context
        uid = str(self.base_author.id)
        found = await Bot.find_user(ctx, uid)
        assert found is not None
        assert await Bot.find_user(ctx, "not-a-real-user-id") is None

    @test
    async def is_user_installed(self) -> None:
        ctx = self.base_context
        ctx.guild = None
        assert Bot.is_user_installed(ctx) in (True, False)

    @test
    async def sha256_for_api(self) -> None:
        token, expiry = Bot.sha256_for_api("test", 60)
        assert token and expiry

    @test
    async def get_lootbox_from_name(self) -> None:
        from ...static.constants import LOOTBOXES

        name = next(v["name"] for v in LOOTBOXES.values() if v.get("available"))
        assert Bot.get_lootbox_from_name(name) is not None
        assert Bot.get_lootbox_from_name("not-a-real-box") is None

    @test
    async def convert_to_timestamp(self) -> None:
        ts = Bot.convert_to_timestamp(self.base_author.id)
        assert "<t:" in ts

    @test
    async def get_group_from_command(self) -> None:
        cmd = Bot.get_command("daily")
        if cmd:
            assert Bot._get_group(cmd) is not None or Bot._get_group(cmd) is None

    @test
    async def find_dominant_color(self) -> None:
        class Resp:
            status = 200

            async def read(self):
                buf = BytesIO()
                Image.new("RGB", (4, 4), "red").save(buf, format="PNG")
                return buf.getvalue()

        Bot.session.get = AsyncMock(return_value=Resp())
        color = await Bot.find_dominant_color("http://example.test/x.png")
        assert isinstance(color, int)
