from types import SimpleNamespace
from unittest.mock import patch

from ..types import *
from ...utils.classes import *
from ..testing import Testing, test
from ...cogs.help import HelpCommand, HelpPaginator
from ...utils.classes.guild import Guild as KilluaGuild
from ...static.constants import DB
from ...static.enums import Category
from ...utils.paginator import Paginator
from ..harnesses import embed_footer_page, press_paginator_button


def _help_group_stub_cmd_alpha():
    """Alpha stub for help group formatting tests."""
    pass


def _help_group_stub_cmd_beta():
    """Beta stub for help group formatting tests."""
    pass


def _fake_commands_for_actions_help_group():
    return [
        SimpleNamespace(
            callback=_help_group_stub_cmd_alpha,
            name="hlp_alpha",
            qualified_name="hlp_alpha",
            help="Alpha stub for help group formatting tests.",
            usage="hlp_alpha",
            extras={"category": Category.ACTIONS, "id": 990101},
            hidden=False,
            parent=None,
            cog=None,
            checks=[],
            app_command=SimpleNamespace(parent=None),
        ),
        SimpleNamespace(
            callback=_help_group_stub_cmd_beta,
            name="hlp_beta",
            qualified_name="hlp_beta",
            help="Beta stub for help group formatting tests.",
            usage="hlp_beta",
            extras={"category": Category.ACTIONS, "id": 990102},
            hidden=False,
            parent=None,
            cog=None,
            checks=[],
            app_command=SimpleNamespace(parent=None),
        ),
    ]


def _reset_guild_state():
    KilluaGuild.cache.clear()
    DB.guilds.db["guilds"] = []


class TestingHelp(Testing):
    requires_command = True

    def __init__(self):
        super().__init__(cog=HelpCommand)


class Help(TestingHelp):

    def __init__(self):
        super().__init__()

    @test
    async def nonexistent_command(self) -> None:
        _reset_guild_state()

        await self.command(self.cog, self.base_context, command="totally_fake_command_xyz")

        assert (
            self.base_context.result.message.content
            == 'No command called "totally_fake_command_xyz" found.'
        ), self.base_context.result.message.content

    @test
    async def valid_command(self) -> None:
        _reset_guild_state()

        await self.command(self.cog, self.base_context, command="daily")

        msg = self.base_context.result.message
        assert (
            "not found" not in (msg.content or "").lower()
        ), msg.content

    @test
    async def help_menu_no_args(self) -> None:
        _reset_guild_state()
        await self.command(self.cog, self.base_context)

        msg = self.base_context.result.message
        embeds = getattr(msg, "embeds", None)
        embed = None
        if isinstance(embeds, list) and embeds:
            embed = embeds[-1]
        elif isinstance(embeds, tuple) and embeds:
            inner = embeds[0]
            if isinstance(inner, list) and inner:
                embed = inner[-1]
        assert embed is not None, embeds
        assert embed.title == "Help menu", embed.title

    @test
    async def unknown_group_or_command(self) -> None:
        _reset_guild_state()
        await self.command(self.cog, self.base_context, group="notarealgroupname")

        assert (
            'No command called "notarealgroupname" found.'
            in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def group_help_paginator_with_mocked_walk_commands(self) -> None:
        """Patch walk_commands so get_group_help builds pages without a full gateway/cog tree."""
        _reset_guild_state()
        await KilluaGuild.new(self.base_guild.id)

        fakes = _fake_commands_for_actions_help_group()
        orig_start = HelpPaginator.start
        HelpPaginator.start = Paginator.start
        self.base_context.timeout_view = False

        async def _press_next(ctx):
            await press_paginator_button(
                ctx.current_view,
                "next",
                context=ctx,
                message=ctx.result.message,
            )
            ctx.current_view.stop()

        prev_rtv = self.base_context.respond_to_view
        self.base_context.respond_to_view = _press_next
        try:
            with patch.object(
                self.cog.client,
                "walk_commands",
                return_value=fakes,
            ):
                await self.command(self.cog, self.base_context, group="actions")
        finally:
            HelpPaginator.start = orig_start
            self.base_context.respond_to_view = prev_rtv

        msg = self.base_context.result.message
        embeds = getattr(msg, "embeds", None)
        emb = None
        if isinstance(embeds, list) and embeds:
            emb = embeds[-1]
        elif isinstance(embeds, tuple) and embeds:
            inner = embeds[0]
            if isinstance(inner, list) and inner:
                emb = inner[-1]
        assert emb is not None, embeds
        assert "`hlp_beta`" in (emb.title or ""), emb.title
        assert "Beta stub for help group formatting tests." in (emb.description or ""), (
            emb.description
        )
        fp = embed_footer_page(emb)
        assert fp is not None, emb.footer
        assert fp == (2, 2), fp
