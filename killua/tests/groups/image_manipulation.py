from ..types import *
from ...utils.classes import *
from ..testing import Testing, test
from ...cogs.image_manipulation import ImageManipulation

from unittest.mock import AsyncMock
import io


class MockPxlResult:
    def __init__(self, success=True, error="", file_type="png"):
        self.success = success
        self.file_type = file_type
        self.error = error

    def convert_to_ioBytes(self):
        return io.BytesIO(b"fake_image_data")


def _normalize_embeds(message):
    e = getattr(message, "embeds", None) or []
    if isinstance(e, tuple) and e:
        inner = e[0]
        if isinstance(inner, list):
            return inner
        return list(e)
    return list(e) if e else []


def _assert_api_file(message, command_name: str, ext: str = "png"):
    assert message.file is not None, "expected file on result message"
    assert message.file.filename == f"{command_name}.{ext}", message.file.filename


class TestingImageManipulation(Testing):
    requires_command = True

    def __init__(self):
        super().__init__(cog=ImageManipulation)


class Ajit(TestingImageManipulation):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def success(self) -> None:
        self.cog.pxl.ajit = AsyncMock(return_value=MockPxlResult())
        await self.command(self.cog, self.base_context, target=None)
        _assert_api_file(self.base_context.result.message, "ajit")


class Emojaic(TestingImageManipulation):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def success(self) -> None:
        self.cog.pxl.emojaic = AsyncMock(return_value=MockPxlResult())
        await self.command(self.cog, self.base_context, target=None)
        _assert_api_file(self.base_context.result.message, "emojaic")


class Eyes(TestingImageManipulation):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def success(self) -> None:
        self.cog.pxl.eyes = AsyncMock(return_value=MockPxlResult())
        await self.command(self.cog, self.base_context, type="big", target=None)
        _assert_api_file(self.base_context.result.message, "eyes")


class Flag(TestingImageManipulation):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def success(self) -> None:
        self.cog.pxl.flag = AsyncMock(return_value=MockPxlResult())
        await self.command(self.cog, self.base_context, flag="us", target=None)
        _assert_api_file(self.base_context.result.message, "flag")


class Flash(TestingImageManipulation):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def success(self) -> None:
        self.cog.pxl.flash = AsyncMock(return_value=MockPxlResult(file_type="gif"))
        await self.command(self.cog, self.base_context, target=None)
        assert self.base_context.result.message.file is not None
        assert self.base_context.result.message.file.filename.endswith("flash.gif")
        assert self.base_context.result.message.file.spoiler is True


class Glitch(TestingImageManipulation):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def success(self) -> None:
        self.cog.pxl.glitch = AsyncMock(return_value=MockPxlResult(file_type="gif"))
        await self.command(self.cog, self.base_context, target=None)
        _assert_api_file(self.base_context.result.message, "glitch", ext="gif")


class Jpeg(TestingImageManipulation):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def success(self) -> None:
        self.cog.pxl.jpeg = AsyncMock(return_value=MockPxlResult())
        await self.command(self.cog, self.base_context, target=None)
        _assert_api_file(self.base_context.result.message, "jpeg")

    @test
    async def api_error_embed(self) -> None:
        self.cog.pxl.jpeg = AsyncMock(
            return_value=MockPxlResult(success=False, error="pxl down")
        )
        await self.command(self.cog, self.base_context, target=None)
        embeds = _normalize_embeds(self.base_context.result.message)
        assert embeds, embeds
        assert "error" in embeds[0].title.lower(), embeds[0].title


class Lego(TestingImageManipulation):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def success(self) -> None:
        self.cog.pxl.lego = AsyncMock(return_value=MockPxlResult())
        await self.command(self.cog, self.base_context, target=None)
        _assert_api_file(self.base_context.result.message, "lego")


class Nokia(TestingImageManipulation):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def success(self) -> None:
        self.cog.pxl.imagescript = AsyncMock(return_value=MockPxlResult())
        await self.command(self.cog, self.base_context, target=None)
        _assert_api_file(self.base_context.result.message, "nokia")


class Screenshot(TestingImageManipulation):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def success(self) -> None:
        self.cog.pxl.screenshot = AsyncMock(return_value=MockPxlResult())
        await self.command(
            self.cog,
            self.base_context,
            website="https://example.com/page",
        )
        _assert_api_file(self.base_context.result.message, "screenshot")


class Snapchat(TestingImageManipulation):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def success(self) -> None:
        self.cog.pxl.snapchat = AsyncMock(return_value=MockPxlResult())
        await self.command(self.cog, self.base_context, filter="dog", target=None)
        _assert_api_file(self.base_context.result.message, "snapchat")


class Sonic(TestingImageManipulation):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def success(self) -> None:
        self.cog.pxl.sonic = AsyncMock(return_value=MockPxlResult())
        await self.command(self.cog, self.base_context, text="gotta go fast")
        _assert_api_file(self.base_context.result.message, "sonic")


class Spin(TestingImageManipulation):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def success(self) -> None:
        buf = io.BytesIO(b"gif-bytes")
        self.cog._create_spin_gif = AsyncMock(return_value=buf)
        await self.command(self.cog, self.base_context, target=None)
        assert self.base_context.result.message.file is not None
        assert self.base_context.result.message.file.filename == "spin.gif"


class Thonkify(TestingImageManipulation):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def success(self) -> None:
        self.cog.pxl.thonkify = AsyncMock(return_value=MockPxlResult())
        await self.command(self.cog, self.base_context, text="hello")
        _assert_api_file(self.base_context.result.message, "thonkify")

    @test
    async def api_error(self) -> None:
        self.cog.pxl.thonkify = AsyncMock(
            return_value=MockPxlResult(success=False, error="API down")
        )
        await self.command(self.cog, self.base_context, text="hello")
        embeds = _normalize_embeds(self.base_context.result.message)
        assert embeds, embeds
        assert (
            "error" in embeds[0].title.lower()
        ), embeds[0].title


class Wtf(TestingImageManipulation):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def success(self) -> None:
        buf = io.BytesIO(b"png-bytes")
        self.cog.create_wtf_meme = AsyncMock(return_value=buf)
        await self.command(self.cog, self.base_context, target=None)
        assert self.base_context.result.message.file is not None
        assert self.base_context.result.message.file.filename == "wtf.png"
