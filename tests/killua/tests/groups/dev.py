from ..types import *
from ..testing import Testing, test
from ...cogs.dev import Dev
from ...static.constants import DB

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
            DB.const.db["const"] = [{"_id": "updates", "updates": [{"version": "1.0"}]}]

            async def respond_to_modal(context: Context):
                for child in context.modal.children:
                    if child.label == "Version":
                        child._value = "1.0"
                    elif child.label == "Description":
                        child._value = "test"

            self.base_context.respond_to_modal = respond_to_modal
            await self.command(self.cog, self.base_context)

            assert self.base_context.result.message.content == "This is an already existing version", self.base_context.result.message.content
    
        @test
        async def publish_update(self) -> None:
            DB.const.db["const"] = [{"_id": "updates", "updates": []}]

            async def respond_to_modal(context: Context):
                for child in context.modal.children:
                    if child.label == "Version":
                        child._value = "1.0"
                    elif child.label == "Description":
                        child._value = "test"

            self.base_context.respond_to_modal = respond_to_modal
            await self.command(self.cog, self.base_context)

            assert self.base_context.result.message.content == "Published new update `No version` -> `1.0`", self.base_context.result.message.content
            assert DB.const.find_one({"_id": "updates"})["updates"][0]["version"], "1.0"

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
