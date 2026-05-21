from ..types import *
from ...utils.classes import *
from ..testing import Testing, test
from ...cogs.web_scraping import WebScraping

import inspect
from unittest.mock import AsyncMock, patch

from ..harnesses import embed_footer_page, press_paginator_button


class MockResponse:
    def __init__(self, status=200, data=None):
        self.status = status
        self._data = data or {}

    async def json(self):
        return self._data

    async def text(self):
        return ""


class MockPxlResult:
    def __init__(self, success=True, data=None, error=""):
        self.success = success
        self.data = data or {}
        self.error = error


class TestingWebScraping(Testing):
    requires_command = True
    _menus_registered = False

    def __init__(self):
        if not TestingWebScraping._menus_registered:
            TestingWebScraping._menus_registered = True
        else:
            WebScraping._init_menus = lambda self: None
        super().__init__(cog=WebScraping)


class Novel(TestingWebScraping):

    def __init__(self):
        super().__init__()

    @test
    async def no_results(self) -> None:
        original = self.cog.client.session.get
        self.cog.client.session.get = AsyncMock(
            return_value=MockResponse(200, {"numFound": 0, "docs": []})
        )
        await self.command(self.cog, self.base_context, book="xyznonexistent999")
        self.cog.client.session.get = original
        assert (
            self.base_context.result.message.content == "No results found"
        ), self.base_context.result.message.content

    @test
    async def api_error(self) -> None:
        original = self.cog.client.session.get
        self.cog.client.session.get = AsyncMock(return_value=MockResponse(500))
        await self.command(self.cog, self.base_context, book="test")
        self.cog.client.session.get = original
        assert (
            "Something went wrong" in self.base_context.result.message.content
        ), self.base_context.result.message.content


class Img(TestingWebScraping):

    def __init__(self):
        super().__init__()

    @test
    async def no_results(self) -> None:
        original = self.cog.get_bing_images
        self.cog.get_bing_images = AsyncMock(return_value=[])
        await self.command(self.cog, self.base_context, query="xyznonexistent")
        self.cog.get_bing_images = original
        assert (
            self.base_context.result.message.content == "No results found"
        ), self.base_context.result.message.content

    @test
    async def api_error(self) -> None:
        original = self.cog.get_bing_images
        self.cog.get_bing_images = AsyncMock(return_value=500)
        await self.command(self.cog, self.base_context, query="test")
        self.cog.get_bing_images = original
        assert (
            "Something went wrong" in self.base_context.result.message.content
            and "500" in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def img_paginator_next_page(self) -> None:
        """Paginator: press next on multi-image img results."""
        links = [f"https://example.com/img{i}.png" for i in range(5)]
        orig = self.cog.get_bing_images
        self.cog.get_bing_images = AsyncMock(return_value=links)
        self.base_context.timeout_view = False

        async def _press_next(ctx):
            await press_paginator_button(
                ctx.current_view,
                "next",
                context=ctx,
                message=ctx.result.message,
            )
            ctx.current_view.stop()

        _prev_rtv = self.base_context.respond_to_view
        self.base_context.respond_to_view = _press_next
        try:
            with patch("killua.bot.randint", return_value=100):
                await self.command(self.cog, self.base_context, query="cats")
        finally:
            self.cog.get_bing_images = orig
            self.base_context.respond_to_view = _prev_rtv
        raw = self.base_context.result.message.embeds
        emb = None
        if isinstance(raw, list) and raw:
            emb = raw[-1]
        elif isinstance(raw, tuple) and raw:
            inner = raw[0]
            if isinstance(inner, list) and inner:
                emb = inner[-1]
        assert emb is not None, raw
        assert emb.image is not None, emb
        assert emb.image.url == links[1], emb.image.url
        page = embed_footer_page(emb)
        assert page == (2, 5), page


class Google(TestingWebScraping):

    def __init__(self):
        super().__init__()

    @test
    async def success(self) -> None:
        self.cog.pxl.web_search = AsyncMock(
            return_value=MockPxlResult(
                success=True,
                data={
                    "results": [
                        {
                            "title": "Test Result",
                            "url": "http://example.com",
                            "description": "A test description for search results",
                        }
                    ]
                },
            )
        )
        await self.command(self.cog, self.base_context, text="test query")
        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert (
            "Results for query" in self.base_context.result.message.embeds[0].title
        ), self.base_context.result.message.embeds[0].title

    @test
    async def api_error(self) -> None:
        self.cog.pxl.web_search = AsyncMock(
            return_value=MockPxlResult(success=False, error="Service unavailable")
        )
        await self.command(self.cog, self.base_context, text="test query")
        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert (
            "error" in self.base_context.result.message.embeds[0].title.lower()
        ), self.base_context.result.message.embeds[0].title

    @test
    async def api_timeout(self) -> None:
        from asyncio import TimeoutError as AsyncTimeout

        async def timeout_wait(awaitable, *args, **kwargs):
            # `wait_for(coro, t)` evaluates `coro` before calling wait_for; if we raise
            # immediately, that coroutine (e.g. from AsyncMock) is never awaited.
            if inspect.iscoroutine(awaitable):
                awaitable.close()
            raise AsyncTimeout()

        with patch("killua.cogs.web_scraping.wait_for", side_effect=timeout_wait):
            await self.command(self.cog, self.base_context, text="slow query")
        assert (
            "too long" in self.base_context.result.message.content.lower()
        ), self.base_context.result.message.content
