from ..types import *
from ...utils.classes import *
from ..testing import Testing, test
from ...cogs.dev import Dev
from ...static.constants import DB, INFO

from datetime import datetime
from unittest.mock import AsyncMock


class TestingDev(Testing):
    requires_command = True

    def __init__(self):
        super().__init__(cog=Dev)

    def _mock_cog_externals(self):
        pass


class Eval(TestingDev):

    def __init__(self):
        super().__init__()

    @test
    async def eval(self) -> None:
        await self.command(self.cog, self.base_context, code="1+1")

        assert (
            self.base_context.result.message.content == "```py" + "\n" + "2```"
        ), self.base_context.result.message.content

    @test
    async def eval_exception(self) -> None:
        await self.command(self.cog, self.base_context, code="1/0")

        assert (
            self.base_context.result.message.content == "division by zero"
        ), self.base_context.result.message.content


class Say(TestingDev):

    def __init__(self):
        super().__init__()

    @test
    async def say(self) -> None:
        await self.command(self.cog, self.base_context, content="Hello World")

        assert (
            self.base_context.result.message.content == "Hello World"
        ), self.base_context.result.message.content


class Update(TestingDev):

    def __init__(self):
        super().__init__()

    @test
    async def version_not_found(self) -> None:
        DB.news.db["news"] = []
        await self.command(self.cog, self.base_context, version="nonexistent")

        assert (
            self.base_context.result.message.content
            == "That version does not exist"
        ), self.base_context.result.message.content

    @test
    async def no_version_no_updates(self) -> None:
        DB.news.db["news"] = []
        await self.command(self.cog, self.base_context)

        assert (
            self.base_context.result.message.content == "No updates found"
        ), self.base_context.result.message.content

    @test
    async def correct_usage(self) -> None:
        DB.news.db["news"] = [
            {
                "_id": "test_update_1",
                "type": "update",
                "published": True,
                "version": "1.0",
                "title": "Test Update",
                "content": "Some update content",
                "author": "tester",
                "images": [],
                "links": {},
                "notify_users": [],
                "timestamp": datetime.now(),
            }
        ]

        await self.command(self.cog, self.base_context, version="1.0")

        assert self.base_context.current_view is not None, (
            "Expected a LayoutView to be sent"
        )


class Info(TestingDev):

    def __init__(self):
        super().__init__()

    @test
    async def sends_info_embed(self) -> None:
        await self.command(self.cog, self.base_context)

        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert (
            self.base_context.result.message.embeds[0].title == "Infos about the bot"
        ), self.base_context.result.message.embeds[0].title
        assert (
            self.base_context.result.message.embeds[0].description == INFO
        ), self.base_context.result.message.embeds[0].description


class Apistats(TestingDev):
    command_name = "api_stats"

    def __init__(self):
        super().__init__()

    @test
    async def fetches_diagnostics(self) -> None:
        class Resp:
            status = 200

            async def json(self):
                return {"usage": {}, "ipc": {}}

        self.cog.client.session.get = AsyncMock(return_value=Resp())
        await self.command(self.cog, self.base_context)
        assert self.base_context.result.message.embeds or self.base_context.result.message.content


class Voteremind(TestingDev):

    def __init__(self):
        super().__init__()

    @test
    async def enable_when_disabled(self) -> None:
        user = await User.new(self.base_author.id)
        user.voting_reminder = False

        await self.command(self.cog, self.base_context, toggle="on")

        assert (
            self.base_context.result.message.content
            == "Enabled the voteremind! You can turn it off any time with this command!"
        ), self.base_context.result.message.content

    @test
    async def enable_when_already_enabled(self) -> None:
        user = await User.new(self.base_author.id)
        user.voting_reminder = True

        await self.command(self.cog, self.base_context, toggle="on")

        assert (
            self.base_context.result.message.content
            == "You already have the voteremind enabled!"
        ), self.base_context.result.message.content

    @test
    async def disable_when_enabled(self) -> None:
        user = await User.new(self.base_author.id)
        user.voting_reminder = True

        await self.command(self.cog, self.base_context, toggle="off")

        assert (
            self.base_context.result.message.content
            == "Disabled the voteremind! You can turn it back on any time with this command!"
        ), self.base_context.result.message.content

    @test
    async def disable_when_already_disabled(self) -> None:
        user = await User.new(self.base_author.id)
        user.voting_reminder = False

        await self.command(self.cog, self.base_context, toggle="off")

        assert (
            self.base_context.result.message.content
            == "You already have the voteremind disabled!"
        ), self.base_context.result.message.content
