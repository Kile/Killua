from ..types import *
from ...utils.classes import *
from ..testing import Testing, test
from ...cogs.small_commands import SmallCommands

from unittest.mock import MagicMock, AsyncMock, patch

import discord


def _embed0(message):
    raw = message.embeds
    if isinstance(raw, list) and raw:
        return raw[0]
    if isinstance(raw, tuple) and raw:
        inner = raw[0]
        if isinstance(inner, list) and inner:
            return inner[0]
    return raw[0] if raw else None


from ..harnesses import ListenerFakeButton, ListenerFakeRow

# Backwards-compatible aliases for listener-style tests in this module.
_ListenerFakeButton = ListenerFakeButton
_ListenerFakeRow = ListenerFakeRow


class TestingSmallCommands(Testing):
    requires_command = True
    _menus_registered = False

    def __init__(self):
        if not TestingSmallCommands._menus_registered:
            TestingSmallCommands._menus_registered = True
        else:
            SmallCommands._init_menus = lambda self: None
        super().__init__(cog=SmallCommands)


class Uwufy(TestingSmallCommands):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def transforms_text(self) -> None:
        await self.command(self.cog, self.base_context, text="Hello world this is a test")
        assert self.base_context.result.message.content, self.base_context.result.message.content

    @test
    async def preserves_non_empty_output(self) -> None:
        await self.command(self.cog, self.base_context, text="test")
        assert len(self.base_context.result.message.content) > 0


class Ping(TestingSmallCommands):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def responds_pong(self) -> None:
        await self.command(self.cog, self.base_context)
        assert self.base_context.result.message.content.startswith("Pong"), self.base_context.result.message.content
        assert "ms" in self.base_context.result.message.content, self.base_context.result.message.content


class Topic(TestingSmallCommands):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def sends_topic(self) -> None:
        await self.command(self.cog, self.base_context)
        assert self.base_context.result.message.content, self.base_context.result.message.content
        assert len(self.base_context.result.message.content) > 10


class Hi(TestingSmallCommands):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def greets_author(self) -> None:
        await self.command(self.cog, self.base_context)
        expected = "Hello " + str(self.base_context.author)
        assert self.base_context.result.message.content == expected, self.base_context.result.message.content


class Invite(TestingSmallCommands):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def sends_invite_embed(self) -> None:
        await self.command(self.cog, self.base_context)
        assert self.base_context.result.message.embeds, self.base_context.result.message.embeds
        assert self.base_context.result.message.embeds[0].title == "Invite", self.base_context.result.message.embeds[0].title


class Vote(TestingSmallCommands):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def sends_vote_message(self) -> None:
        await self.command(self.cog, self.base_context)
        assert self.base_context.result.message.content.startswith("Thanks for supporting"), self.base_context.result.message.content


class Permissions(TestingSmallCommands):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command
        self.base_context.me.guild_permissions = [
            ("send_messages", True),
            ("administrator", False),
        ]

    @test
    async def sends_permissions_embed(self) -> None:
        await self.command(self.cog, self.base_context)
        assert self.base_context.result.message.embeds, self.base_context.result.message.embeds
        assert self.base_context.result.message.embeds[0].title == "Bot permissions", self.base_context.result.message.embeds[0].title


class EightBall(TestingSmallCommands):
    """discord.py command name is ``8ball`` (invalid Python identifier)."""

    command_name = "8ball"

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def responds_with_embed(self) -> None:
        await self.command(self.cog, self.base_context, question="Will it work?")
        emb = _embed0(self.base_context.result.message)
        assert emb is not None
        assert "8ball" in emb.title.lower(), emb.title
        assert "Will it work" in emb.description, emb.description


class Avatar(TestingSmallCommands):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def default_shows_author(self) -> None:
        await self.command(self.cog, self.base_context, user=None, guild_avatar="no")
        emb = _embed0(self.base_context.result.message)
        assert emb.title.startswith("Avatar of"), emb.title

    @test
    async def user_without_avatar(self) -> None:
        u = MagicMock()
        u.display_name = "NoAvatar"
        u.avatar = None
        u.display_avatar = None
        await self.command(self.cog, self.base_context, user=u, guild_avatar="no")
        assert (
            self.base_context.result.message.content == "User has no avatar"
        ), self.base_context.result.message.content


class Translate(TestingSmallCommands):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def invalid_language(self) -> None:
        await self.command(
            self.cog,
            self.base_context,
            source="notareallanguage",
            target="english",
            text="hello",
        )
        assert (
            "Invalid language" in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def success_with_mocked_api(self) -> None:
        orig_get = self.cog.client.session.get

        class Resp:
            status = 200

            async def json(self):
                return {
                    "responseData": {"translatedText": "bonjour"},
                    "matches": [{"quality": 90}],
                }

            async def text(self):
                return ""

        self.cog.client.session.get = AsyncMock(return_value=Resp())
        await self.command(
            self.cog,
            self.base_context,
            source="english",
            target="french",
            text="hello",
        )
        self.cog.client.session.get = orig_get
        emb = _embed0(self.base_context.result.message)
        assert emb is not None
        assert emb.title == "Translation Successful", emb.title
        assert "bonjour" in emb.description, emb.description

    @test
    async def api_non_200(self) -> None:
        orig_get = self.cog.client.session.get

        class Resp:
            status = 503

            async def json(self):
                return {}

            async def text(self):
                return "unavailable"

        self.cog.client.session.get = AsyncMock(return_value=Resp())
        await self.command(
            self.cog,
            self.base_context,
            source="english",
            target="french",
            text="hello",
        )
        self.cog.client.session.get = orig_get
        assert ":x:" in self.base_context.result.message.content


class Calc(TestingSmallCommands):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def missing_expression(self) -> None:
        await self.command(self.cog, self.base_context, expression=None)
        assert (
            "Please give me something" in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def success_mocked_mathjs(self) -> None:
        orig_post = self.cog.client.session.post

        class Resp:
            status = 200

            async def json(self):
                return {"result": ["42"], "error": None}

        self.cog.client.session.post = AsyncMock(return_value=Resp())
        await self.command(self.cog, self.base_context, expression="6*7")
        self.cog.client.session.post = orig_post
        assert "42" in self.base_context.result.message.content

    @test
    async def mathjs_reports_error(self) -> None:
        orig_post = self.cog.client.session.post

        class Resp:
            status = 200

            async def json(self):
                return {"result": None, "error": "Unexpected operator"}

        self.cog.client.session.post = AsyncMock(return_value=Resp())
        await self.command(self.cog, self.base_context, expression="+++")
        self.cog.client.session.post = orig_post
        assert (
            "Unexpected operator" in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def malformed_json_response(self) -> None:
        orig_post = self.cog.client.session.post

        class Resp:
            status = 200

            async def json(self):
                return {"oops": True}

        self.cog.client.session.post = AsyncMock(return_value=Resp())
        await self.command(self.cog, self.base_context, expression="1+1")
        self.cog.client.session.post = orig_post
        assert (
            "unknown error" in self.base_context.result.message.content.lower()
        ), self.base_context.result.message.content


class Wyr(TestingSmallCommands):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def sends_question_embed(self) -> None:
        await self.command(self.cog, self.base_context)
        emb = _embed0(self.base_context.result.message)
        assert emb is not None
        assert "would you rather" in emb.title.lower(), emb.title
        assert len(emb.fields) >= 2, emb.fields

    @test
    async def vote_option_a_updates_embed(self) -> None:
        """Path B: Events.on_interaction for wyr:opt-a (see killua/tests/component_interaction.py)."""
        from ...cogs.events import Events
        from ...utils.classes.guild import Guild as KilluaGuild
        from ..harnesses import MockComponentInteraction

        await KilluaGuild.new(self.base_guild.id)
        voter = DiscordMember(guild=self.base_guild, id=self.base_author.id + 8000)
        self.base_guild.members = [self.base_author, voter]

        emb = discord.Embed(title="Would you rather...", color=0x3E4A78)
        emb.add_field(name="A) left `[0 people]`", value="No takers", inline=False)
        emb.add_field(name="B) right `[0 people]`", value="No takers", inline=False)
        sty = int(discord.ButtonStyle.blurple)
        row = _ListenerFakeRow(
            [
                _ListenerFakeButton(custom_id="wyr:opt-a:", label="A", style=sty),
                _ListenerFakeButton(custom_id="wyr:opt-b:", label="B", style=sty),
            ]
        )

        class PM:
            def __init__(self):
                self.id = 777001
                self.embeds = [emb]
                self.components = [row]

        pm = PM()
        events = Events(self.cog.client)
        with patch("killua.bot.randint", return_value=100):
            await events.on_interaction(
                MockComponentInteraction(
                    context=self.base_context,
                    custom_id="wyr:opt-a:",
                    user=voter,
                    message=pm,
                    client=self.cog.client,
                )
            )
        name0 = pm.embeds[0].fields[0].name
        assert "1 person" in name0 or "1 people" in name0, name0


class Poll(TestingSmallCommands):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def vote_first_option_updates_embed(self) -> None:
        """Path B: Events.on_interaction for poll:opt-1 completes a component response."""
        from ...cogs.events import Events
        from ...utils.classes.guild import Guild as KilluaGuild
        from ..harnesses import MockComponentInteraction

        await KilluaGuild.new(self.base_guild.id)
        voter = DiscordMember(guild=self.base_guild, id=self.base_author.id + 9000)
        self.base_guild.members = [self.base_author, voter]

        emb = discord.Embed(title="Poll", description="Q?", color=0x3E4A78)
        emb.add_field(name="1) One `[0 votes]`", value="No votes", inline=False)
        emb.add_field(name="2) Two `[0 votes]`", value="No votes", inline=False)
        enc = self.cog.client._encrypt(self.base_author.id, smallest=False)
        sty = int(discord.ButtonStyle.blurple)
        red = int(discord.ButtonStyle.red)
        row = _ListenerFakeRow(
            [
                _ListenerFakeButton(custom_id="poll:opt-1:", label="1", style=sty),
                _ListenerFakeButton(custom_id="poll:opt-2:", label="2", style=sty),
                _ListenerFakeButton(
                    custom_id=f"poll:close:{enc}:",
                    label="Close",
                    style=red,
                ),
            ]
        )

        class PM:
            def __init__(self):
                self.id = 777002
                self.embeds = [emb]
                self.components = [row]

        pm = PM()
        events = Events(self.cog.client)
        ix = MockComponentInteraction(
            context=self.base_context,
            custom_id="poll:opt-1:",
            user=voter,
            message=pm,
            client=self.cog.client,
        )
        with patch("killua.bot.randint", return_value=100):
            await events.on_interaction(ix)
        assert ix.response.is_done(), (
            "poll vote path should respond via interaction.response (edit or send)"
        )

    @test
    async def poll_modal_submit_publishes_embed(self) -> None:
        """Hybrid poll path: interaction → modal → channel embed with option buttons."""
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        class _ModalResp:
            async def send_modal(self, modal):
                self._modal = modal

        ix = MagicMock()
        ix.response = _ModalResp()
        self.base_context.interaction = ix

        def _filled_poll_setup(*_a, **_k):
            modal = SimpleNamespace()
            modal.timed_out = False
            modal.children = [
                SimpleNamespace(
                    custom_id="question",
                    label="Question",
                    value="Doors or wheels?",
                ),
                SimpleNamespace(
                    custom_id="option:1", label="Option 1", value="Doors"
                ),
                SimpleNamespace(
                    custom_id="option:2", label="Option 2", value="Wheels"
                ),
                SimpleNamespace(
                    custom_id="option:3", label="Option 3", value=""
                ),
                SimpleNamespace(
                    custom_id="option:4", label="Option 4", value=""
                ),
            ]

            async def _wait():
                return False

            modal.wait = _wait
            return modal

        with patch(
            "killua.cogs.small_commands.PollSetup", side_effect=_filled_poll_setup
        ):
            await self.command(self.cog, self.base_context)

        emb = _embed0(self.base_context.result.message)
        assert emb is not None, self.base_context.result.message.embeds
        assert emb.title == "Poll", emb.title
        assert "Doors or wheels" in (emb.description or ""), emb.description
        view = self.base_context.current_view
        assert view is not None, "poll should attach a view with option buttons"
        assert len(getattr(view, "children", [])) >= 2, view.children
