from ..types import *
from ...utils.classes import *
from ..testing import Testing, test
from ...cogs.games import Games
from ...static.constants import TRIVIA_TOPICS, DB
from ...utils.test_db import TestingDatabase
from ..types.member import TestingMember
from unittest.mock import AsyncMock, patch


def _seed_teams(docs: list) -> None:
    TestingDatabase.db["teams"] = []
    for d in docs:
        TestingDatabase.db["teams"].append(d)


def _last_embed_title_description(message):
    raw = message.embeds
    embed = None
    if isinstance(raw, list) and raw:
        embed = raw[-1]
    elif isinstance(raw, tuple) and raw:
        inner = raw[0]
        if isinstance(inner, list) and inner:
            embed = inner[-1]
    assert embed is not None, raw
    return embed.title or "", embed.description or ""


async def _instant_sleep(*_a, **_k):
    return None


class TestingGames(Testing):
    requires_command = True

    def __init__(self):
        super().__init__(cog=Games)


class Gstats(TestingGames):

    def __init__(self):
        super().__init__()

    @test
    async def rps_stats(self) -> None:
        await self.command(self.cog, self.base_context, game_type="rps")
        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert (
            "RPS stats" in self.base_context.result.message.embeds[0].title
        ), self.base_context.result.message.embeds[0].title

    @test
    async def trivia_stats(self) -> None:
        await self.command(self.cog, self.base_context, game_type="trivia")
        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert (
            "Trivia stats" in self.base_context.result.message.embeds[0].title
        ), self.base_context.result.message.embeds[0].title

    @test
    async def counting_stats(self) -> None:
        await self.command(self.cog, self.base_context, game_type="counting")
        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert (
            "Counting stats" in self.base_context.result.message.embeds[0].title
        ), self.base_context.result.message.embeds[0].title


class Gleaderboard(TestingGames):

    def __init__(self):
        super().__init__()

    @test
    async def rps_global(self) -> None:
        _seed_teams(
            [
                {
                    "id": 501001,
                    "points": 10,
                    "stats": {
                        "rps": {"pve": {"won": 3}, "pvp": {"won": 20}},
                        "trivia": {
                            "easy": {"right": 1},
                            "medium": {"right": 0},
                            "hard": {"right": 0},
                        },
                        "counting_highscore": {"easy": 1, "hard": 0},
                    },
                },
                {
                    "id": 501002,
                    "points": 5,
                    "stats": {
                        "rps": {"pve": {"won": 9}, "pvp": {"won": 1}},
                        "trivia": {
                            "easy": {"right": 2},
                            "medium": {"right": 1},
                            "hard": {"right": 0},
                        },
                        "counting_highscore": {"easy": 3, "hard": 2},
                    },
                },
            ]
        )
        await self.command(
            self.cog, self.base_context, game="rps", where="global"
        )
        title, desc = _last_embed_title_description(self.base_context.result.message)
        assert "leaderboard" in title.lower(), title
        assert "<@501001>" in desc or "<@501002>" in desc, desc

    @test
    async def rps_server_filters_members(self) -> None:
        in_guild = TestingMember(id=601001, username="A")
        self.base_guild.members = [self.base_author, in_guild]
        _seed_teams(
            [
                {
                    "id": 601001,
                    "points": 1,
                    "stats": {
                        "rps": {"pve": {"won": 1}, "pvp": {"won": 1}},
                        "trivia": {
                            "easy": {"right": 0},
                            "medium": {"right": 0},
                            "hard": {"right": 0},
                        },
                        "counting_highscore": {"easy": 0, "hard": 0},
                    },
                },
                {
                    "id": 609999,
                    "points": 99,
                    "stats": {
                        "rps": {"pve": {"won": 99}, "pvp": {"won": 99}},
                        "trivia": {
                            "easy": {"right": 0},
                            "medium": {"right": 0},
                            "hard": {"right": 0},
                        },
                        "counting_highscore": {"easy": 0, "hard": 0},
                    },
                },
            ]
        )
        await self.command(
            self.cog, self.base_context, game="rps", where="server"
        )
        title, desc = _last_embed_title_description(self.base_context.result.message)
        assert "leaderboard" in title.lower(), title
        assert "<@601001>" in desc, desc
        assert "609999" not in desc, desc

    @test
    async def counting_global(self) -> None:
        _seed_teams(
            [
                {
                    "id": 701001,
                    "points": 1,
                    "stats": {
                        "rps": {"pve": {"won": 0}, "pvp": {"won": 0}},
                        "trivia": {
                            "easy": {"right": 0},
                            "medium": {"right": 0},
                            "hard": {"right": 0},
                        },
                        "counting_highscore": {"easy": 50, "hard": 12},
                    },
                },
                {
                    "id": 701002,
                    "points": 1,
                    "stats": {
                        "rps": {"pve": {"won": 0}, "pvp": {"won": 0}},
                        "trivia": {
                            "easy": {"right": 0},
                            "medium": {"right": 0},
                            "hard": {"right": 0},
                        },
                        "counting_highscore": {"easy": 10, "hard": 99},
                    },
                },
            ]
        )
        await self.command(
            self.cog, self.base_context, game="counting", where="global"
        )
        title, desc = _last_embed_title_description(self.base_context.result.message)
        assert "counting" in title.lower(), title
        assert "<@701001>" in desc or "<@701002>" in desc, desc

    @test
    async def trivia_global(self) -> None:
        _seed_teams(
            [
                {
                    "id": 801001,
                    "points": 1,
                    "stats": {
                        "rps": {"pve": {"won": 0}, "pvp": {"won": 0}},
                        "trivia": {
                            "easy": {"right": 5},
                            "medium": {"right": 1},
                            "hard": {"right": 0},
                        },
                        "counting_highscore": {"easy": 0, "hard": 0},
                    },
                },
                {
                    "id": 801002,
                    "points": 1,
                    "stats": {
                        "rps": {"pve": {"won": 0}, "pvp": {"won": 0}},
                        "trivia": {
                            "easy": {"right": 2},
                            "medium": {"right": 4},
                            "hard": {"right": 1},
                        },
                        "counting_highscore": {"easy": 0, "hard": 0},
                    },
                },
            ]
        )
        await self.command(
            self.cog, self.base_context, game="trivia", where="global"
        )
        title, desc = _last_embed_title_description(self.base_context.result.message)
        assert "trivia" in title.lower(), title
        assert "<@801001>" in desc or "<@801002>" in desc, desc


class Rps(TestingGames):

    def __init__(self):
        super().__init__()

    @test
    async def play_against_self(self) -> None:
        await self.command(self.cog, self.base_context, user=self.base_context.author)
        assert (
            self.base_context.result.message.content
            == "Baka! You can't play against yourself"
        ), self.base_context.result.message.content

    @test
    async def play_against_other_bot_rejected(self) -> None:
        other_bot = DiscordMember(
            id=self.base_context.me.id + 424242,
            bot=True,
            username="NotKillua",
            mutual_guilds=[object()],
        )
        await self.command(self.cog, self.base_context, user=other_bot)
        assert "Beep-boop" in self.base_context.result.message.content

    @test
    async def play_opponent_without_mutual_guilds(self) -> None:
        opp = DiscordMember(
            id=self.base_author.id + 8001,
            bot=False,
            username="Stranger",
            mutual_guilds=[],
        )
        await User.new(opp.id)
        await self.command(self.cog, self.base_context, user=opp)
        assert "share a server" in self.base_context.result.message.content.lower()

    @test
    async def play_points_nonpositive_rejected(self) -> None:
        opp = DiscordMember(
            id=self.base_author.id + 8002,
            bot=False,
            username="Buddy",
            mutual_guilds=[object()],
        )
        self.base_guild.members = [self.base_author, opp]
        await User.new(self.base_author.id)
        await User.new(opp.id)
        with patch("killua.cogs.games.blcheck", new_callable=AsyncMock, return_value=False):
            await self.command(self.cog, self.base_context, user=opp, points=-1)
        assert "1-100" in self.base_context.result.message.content

    @test
    async def play_points_over_cap_rejected(self) -> None:
        opp = DiscordMember(
            id=self.base_author.id + 8003,
            bot=False,
            username="Buddy2",
            mutual_guilds=[object()],
        )
        self.base_guild.members = [self.base_author, opp]
        await User.new(self.base_author.id)
        await User.new(opp.id)
        with patch("killua.cogs.games.blcheck", new_callable=AsyncMock, return_value=False):
            await self.command(self.cog, self.base_context, user=opp, points=101)
        assert "1-100" in self.base_context.result.message.content

    @test
    async def play_points_author_too_poor(self) -> None:
        opp = DiscordMember(
            id=self.base_author.id + 8004,
            bot=False,
            username="RichFriend",
            mutual_guilds=[object()],
        )
        self.base_guild.members = [self.base_author, opp]
        u1 = await User.new(self.base_author.id)
        await u1.set_jenny(5)
        await User.new(opp.id)
        with patch("killua.cogs.games.blcheck", new_callable=AsyncMock, return_value=False):
            await self.command(self.cog, self.base_context, user=opp, points=10)
        assert "not have enough Jenny" in self.base_context.result.message.content

    @test
    async def play_points_opponent_too_poor(self) -> None:
        opp = DiscordMember(
            id=self.base_author.id + 8005,
            bot=False,
            username="PoorFriend",
            mutual_guilds=[object()],
        )
        self.base_guild.members = [self.base_author, opp]
        u1 = await User.new(self.base_author.id)
        await u1.set_jenny(500)
        u2 = await User.new(opp.id)
        await u2.set_jenny(3)
        with patch("killua.cogs.games.blcheck", new_callable=AsyncMock, return_value=False):
            await self.command(self.cog, self.base_context, user=opp, points=10)
        assert "opponent does not have enough" in self.base_context.result.message.content

    @test
    async def pvp_accept_challenge_one_confirm(self) -> None:
        """Opponent accepts channel confirm; both players pick via patched DM select."""
        from ..harnesses import find_button, patch_member_rps_select

        opp = DiscordMember(
            id=self.base_author.id + 8010,
            bot=False,
            username="Rival",
            mutual_guilds=[object()],
        )
        self.base_guild.members = [self.base_author, opp]
        u1 = await User.new(self.base_author.id)
        await u1.set_jenny(500)
        u2 = await User.new(opp.id)
        await u2.set_jenny(500)

        await patch_member_rps_select(self.base_author, self.base_context, choice=0)
        await patch_member_rps_select(opp, self.base_context, choice=1)

        async def accept_challenge(ctx):
            button = find_button(ctx.current_view, custom_id="confirm")
            if button:
                await button.callback(ArgumentInteraction(ctx, user=opp))

        self.base_context.timeout_view = False
        _prev_rtv = self.base_context.respond_to_view
        self.base_context.respond_to_view = accept_challenge
        try:
            with patch("killua.cogs.games.blcheck", AsyncMock(return_value=False)):
                with patch(
                    "killua.cogs.games.Rps._will_exceed_interaction_limit",
                    return_value=True,
                ):
                    with patch("killua.cogs.games.random.randint", return_value=1):
                        await self.command(
                            self.cog, self.base_context, user=opp, points=5
                        )
        finally:
            self.base_context.respond_to_view = _prev_rtv

        msg = self.base_context.result.message.content or ""
        assert (
            "against" in msg.lower()
            or "won" in msg.lower()
            or "lost" in msg.lower()
            or "=" in msg
        ), msg

    @test
    async def singleplayer_vs_killua_dm_select_outcome(self) -> None:
        """Author picks via patched DM RpsSelect; bot choice patched; channel outcome."""
        from ..harnesses import patch_member_rps_select

        await patch_member_rps_select(self.base_author, self.base_context, choice=0)

        with patch(
            "killua.cogs.games.Rps._will_exceed_interaction_limit",
            return_value=True,
        ):
            with patch("killua.cogs.games.random.randint", return_value=1):
                await self.command(
                    self.cog, self.base_context, user=self.base_context.me
                )

        msg = self.base_context.result.message.content or ""
        assert (
            "against" in msg.lower()
            or "won" in msg.lower()
            or "lost" in msg.lower()
            or "=" in msg
        ), msg


class Trivia(TestingGames):

    def __init__(self):
        super().__init__()

    @test
    async def invalid_topic(self) -> None:
        await self.command(self.cog, self.base_context, topic="TotallyFakeTopic123")
        assert (
            "That is not a valid topic" in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def single_wrong_answer_select(self) -> None:
        """Path A: trivia question Select callback picks a wrong option."""
        from killua.utils.interactions import Select as KSelect

        api_payload = {
            "response_code": 0,
            "results": [
                {
                    "category": "9",
                    "type": "multiple",
                    "difficulty": "easy",
                    "question": "Test%3F",
                    "correct_answer": "Yes",
                    "incorrect_answers": ["No", "Maybe", "Perhaps"],
                }
            ],
        }

        class Resp:
            async def json(self):
                return api_payload

        orig_get = self.cog.client.session.get
        self.cog.client.session.get = AsyncMock(return_value=Resp())

        self.base_context.timeout_view = False
        phase_holder = {"n": 0}

        async def _answer_then_dismiss_play_again(ctx):
            v = ctx.current_view
            if not v:
                return
            if phase_holder["n"] == 0:
                for item in v.children:
                    if isinstance(item, KSelect):
                        await item.callback(
                            ArgumentInteraction(
                                ctx,
                                message=ctx.result.message,
                                data={"values": ["0"]},
                            )
                        )
                        break
                phase_holder["n"] = 1
            else:
                v.stop()

        _prev_rtv = self.base_context.respond_to_view
        self.base_context.respond_to_view = _answer_then_dismiss_play_again
        try:
            with patch("killua.cogs.games.random.sample", lambda seq, k: list(seq)[:k]):
                with patch("killua.bot.randint", return_value=7):
                    await self.command(self.cog, self.base_context, difficulty="easy")
        finally:
            self.cog.client.session.get = orig_get
            self.base_context.respond_to_view = _prev_rtv

        assert "Sadly not the right answer" in (
            self.base_context.result.message.content or ""
        ), self.base_context.result.message.content

    def _trivia_api_ok(self):
        return {
            "response_code": 0,
            "results": [
                {
                    "category": "9",
                    "type": "multiple",
                    "difficulty": "easy",
                    "question": "Test%3F",
                    "correct_answer": "Yes",
                    "incorrect_answers": ["No", "Maybe", "Perhaps"],
                }
            ],
        }

    @test
    async def single_correct_answer_select(self) -> None:
        """Path A: correct option updates stats and shows reward text."""
        from killua.utils.interactions import Select as KSelect

        class Resp:
            def __init__(self, payload):
                self._payload = payload

            async def json(self):
                return self._payload

        api_payload = self._trivia_api_ok()
        orig_get = self.cog.client.session.get
        self.cog.client.session.get = AsyncMock(return_value=Resp(api_payload))

        self.base_context.timeout_view = False

        async def _pick_correct(ctx):
            v = ctx.current_view
            if not v:
                return
            for item in v.children:
                if isinstance(item, KSelect):
                    correct_i = next(
                        i for i, o in enumerate(item.options) if o.label == "Yes"
                    )
                    await item.callback(
                        ArgumentInteraction(
                            ctx,
                            message=ctx.result.message,
                            data={"values": [str(correct_i)]},
                        )
                    )
                    break
            v.stop()

        _prev_rtv = self.base_context.respond_to_view
        self.base_context.respond_to_view = _pick_correct
        try:
            with patch("killua.cogs.games.random.sample", lambda seq, k: list(seq)[:k]):
                with patch("killua.bot.randint", return_value=7):
                    await self.command(self.cog, self.base_context, difficulty="easy")
        finally:
            self.cog.client.session.get = orig_get
            self.base_context.respond_to_view = _prev_rtv

        assert "Correct!" in (
            self.base_context.result.message.content or ""
        ), self.base_context.result.message.content

    @test
    async def trivia_api_failure_message(self) -> None:
        class Resp:
            async def json(self):
                return {"response_code": 5, "results": []}

        orig_get = self.cog.client.session.get
        self.cog.client.session.get = AsyncMock(return_value=Resp())
        try:
            await self.command(self.cog, self.base_context, difficulty="easy")
        finally:
            self.cog.client.session.get = orig_get
        txt = (self.base_context.result.message.content or "").lower()
        assert "issue with the api" in txt, self.base_context.result.message.content

    @test
    async def play_again_triggers_second_round_then_wrong(self) -> None:
        """Select correct, press Play Again, then wrong answer on second question."""
        from killua.utils.interactions import Select as KSelect

        from ..harnesses import find_button

        class Resp:
            def __init__(self, payload):
                self._payload = payload

            async def json(self):
                return self._payload

        api_payload = self._trivia_api_ok()
        orig_get = self.cog.client.session.get
        self.cog.client.session.get = AsyncMock(return_value=Resp(api_payload))

        self.base_context.timeout_view = False
        phase = {"n": 0}

        async def _phased(ctx):
            v = ctx.current_view
            if not v:
                return
            if phase["n"] == 0:
                for item in v.children:
                    if isinstance(item, KSelect):
                        correct_i = next(
                            i for i, o in enumerate(item.options) if o.label == "Yes"
                        )
                        await item.callback(
                            ArgumentInteraction(
                                ctx,
                                message=ctx.result.message,
                                data={"values": [str(correct_i)]},
                            )
                        )
                        break
                phase["n"] = 1
            elif phase["n"] == 1:
                btn = find_button(v, custom_id="play_again")
                assert btn is not None
                await btn.callback(
                    ArgumentInteraction(ctx, message=ctx.result.message)
                )
                phase["n"] = 2
            else:
                for item in v.children:
                    if isinstance(item, KSelect):
                        wrong_i = next(
                            i
                            for i, o in enumerate(item.options)
                            if o.label != "Yes"
                        )
                        await item.callback(
                            ArgumentInteraction(
                                ctx,
                                message=ctx.result.message,
                                data={"values": [str(wrong_i)]},
                            )
                        )
                        break
                v.stop()

        _prev_rtv = self.base_context.respond_to_view
        self.base_context.respond_to_view = _phased
        try:
            with patch("killua.cogs.games.random.sample", lambda seq, k: list(seq)[:k]):
                with patch("killua.bot.randint", return_value=7):
                    await self.command(
                        self.cog, self.base_context, difficulty="easy"
                    )
        finally:
            self.cog.client.session.get = orig_get
            self.base_context.respond_to_view = _prev_rtv

        content = self.base_context.result.message.content or ""
        assert "Sadly not the right answer" in content, content

    @test
    async def multiplayer_both_wrong_after_dm_selects(self) -> None:
        """PvP trivia: confirm, both answer via patched DM Select (wrong options)."""
        from ..harnesses import find_button, patch_member_trivia_select

        opp = DiscordMember(
            id=self.base_author.id + 8020,
            bot=False,
            username="TriviaRival",
            mutual_guilds=[object()],
        )
        self.base_guild.members = [self.base_author, opp]
        u1 = await User.new(self.base_author.id)
        await u1.set_jenny(500)
        u2 = await User.new(opp.id)
        await u2.set_jenny(500)

        class Resp:
            def __init__(self, payload):
                self._payload = payload

            async def json(self):
                return self._payload

        api_payload = self._trivia_api_ok()
        orig_get = self.cog.client.session.get
        self.cog.client.session.get = AsyncMock(return_value=Resp(api_payload))

        await patch_member_trivia_select(
            self.base_author, self.base_context, choice_index=0
        )
        await patch_member_trivia_select(opp, self.base_context, choice_index=1)

        async def accept_challenge(ctx):
            button = find_button(ctx.current_view, custom_id="confirm")
            if button:
                await button.callback(ArgumentInteraction(ctx, user=opp))

        self.base_context.timeout_view = False
        _prev_rtv = self.base_context.respond_to_view
        self.base_context.respond_to_view = accept_challenge
        try:
            with patch("killua.cogs.games.blcheck", AsyncMock(return_value=False)):
                with patch(
                    "killua.cogs.games.Trivia._will_exceed_interaction_limit",
                    return_value=True,
                ):
                    with patch(
                        "killua.cogs.games.random.sample",
                        lambda seq, k: list(seq)[:k],
                    ):
                        with patch("killua.bot.randint", return_value=7):
                            await self.command(
                                self.cog,
                                self.base_context,
                                opponent=opp,
                                jenny=5,
                                difficulty="easy",
                            )
        finally:
            self.cog.client.session.get = orig_get
            self.base_context.respond_to_view = _prev_rtv

        msg = self.base_context.result.message.content or ""
        assert "wrong answer" in msg.lower(), msg


class Count(TestingGames):

    def __init__(self):
        super().__init__()

    @test
    async def wrong_button_ends_run(self) -> None:
        """Memorize phase sleeps patched; wrong CountButtons tap ends with Wrong choice."""
        from killua.cogs.games import CountButtons

        from ..harnesses import iter_view_items

        await User.new(self.base_author.id)

        self.base_context.timeout_view = False

        async def _wrong_first_click(ctx):
            v = ctx.current_view
            if not v:
                return
            ref = next(
                (c for c in iter_view_items(v) if isinstance(c, CountButtons)), None
            )
            assert ref is not None
            stage = getattr(v, "stage", 1)
            need = ref.solutions[stage]
            wrong_btn = next(
                c
                for c in iter_view_items(v)
                if isinstance(c, CountButtons) and c.index != need
            )
            await wrong_btn.callback(
                ArgumentInteraction(ctx, message=ctx.result.message)
            )
            v.stop()

        _prev = self.base_context.respond_to_view
        self.base_context.respond_to_view = _wrong_first_click
        try:
            with patch("killua.cogs.games.asyncio.sleep", _instant_sleep):
                await self.command(self.cog, self.base_context, difficulty="easy")
        finally:
            self.base_context.respond_to_view = _prev

        txt = self.base_context.result.message.content or ""
        assert "Wrong choice" in txt or "wrong" in txt.lower(), txt

    @test
    async def correct_first_stage_shows_next_level_prompt(self) -> None:
        from killua.cogs.games import CountButtons

        from ..harnesses import iter_view_items

        await User.new(self.base_author.id)
        self.base_context.timeout_view = False

        async def _right_click(ctx):
            v = ctx.current_view
            if not v:
                return
            stage = getattr(v, "stage", 1)
            ref = next(
                (c for c in iter_view_items(v) if isinstance(c, CountButtons)), None
            )
            assert ref is not None
            need = ref.solutions[stage]
            btn = next(
                c
                for c in iter_view_items(v)
                if isinstance(c, CountButtons) and c.index == need
            )
            await btn.callback(ArgumentInteraction(ctx, message=ctx.result.message))
            v.stop()

        _prev = self.base_context.respond_to_view
        self.base_context.respond_to_view = _right_click
        try:
            with patch("killua.cogs.games.asyncio.sleep", _instant_sleep):
                await self.command(self.cog, self.base_context, difficulty="easy")
        finally:
            self.base_context.respond_to_view = _prev

        txt = self.base_context.result.message.content or ""
        assert (
            "next level" in txt.lower()
            or "congrats" in txt.lower()
            or "well done" in txt.lower()
        ), txt
