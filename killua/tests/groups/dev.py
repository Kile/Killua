from ..types import *
from ..testing import Testing, test
from ...cogs.dev import Dev
from ...utils.paginator import Buttons
from ...static.constants import DB
from killua.static.enums import Category, HuntOptions, Items, SellOptions

class TestingDev(Testing):

    def __init__(self):
        super().__init__(cog=Dev)

class Eval(TestingDev):

    def __init__(self):
        super().__init__()

    # more a formality, this command is not really complicated
    @test
    async def eval(self) -> None:
        await self.command(self.cog, self.base_context, code="1+1")

        assert self.base_context.result.message.content == "```py" + "\n" + "2```", self.base_context.result.message.content

class Say(TestingDev):

    def __init__(self):
        super().__init__()

    # Same as eval, not a complicated command, not many tests
    @test
    async def say(self) -> None:
        await self.command(self.cog, self.base_context, content="Hello World")

        assert self.base_context.result.message.content == "Hello World", self.base_context.result.message.content

class Publish_Update(TestingDev):
    
        def __init__(self):
            super().__init__()

        @test
        async def publish_already_published_version(self) -> None:
            DB.updates.db = {"updates": [{"_id": "log", "past_updates": []}, {"_id": "current", "version": "1.0.0"}]}
            await self.command(self.cog, self.base_context, version="1.0", update="Test")

            assert self.base_context.result.message.content == "This is an already existing version", self.base_context.result.message.content
    
        @test
        async def publish_update(self) -> None:
            DB.updates.db = {"updates": [{"_id": "log", "past_updates": []}]}
            await self.command(self.cog, self.base_context, version="1.0", update="test")

            assert self.base_context.result.message.content == "Published update", self.base_context.result.message.content
            assert DB.updates.find_one({"_id": "current"}), DB.updates.find_one({"_id": "current"})
            assert DB.updates.find_one({"_id": "current"})["version"] == "1.0", DB.updates.find_one({"_id": "current"})["version"]

class Update(TestingDev):

    def __init__(self):
        super().__init__()

    @test
    async def incorrect_usage(self) -> None:
        await self.command(self.cog, self.base_context, version="incorrect")

        assert self.base_context.result.message.content == "Invalid version!", self.base_context.result.message.content

    @test
    async def correct_usage(self) -> None:
        await self.command(self.cog, self.base_context, version="1.0")

        assert self.base_context.result.message.embeds, self.base_context.result.message.embeds
        assert self.base_context.result.message.embeds[0].title == "Infos about version `1.0`", self.base_context.result.message.embeds[0].title
        assert self.base_context.result.message.embeds[0].description == "test", self.base_context.result.message.embeds[0].description
