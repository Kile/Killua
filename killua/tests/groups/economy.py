from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

from ..types import ArgumentInteraction
from ...utils.classes import User
from ..testing import Testing, test
from ...cogs.economy import Economy
from ...static.constants import LOOTBOXES, BOOSTERS
from ...utils.classes.guild import Guild as KilluaGuild

from ...utils.classes import lootbox as lootbox_mod


def _expected_boxinfo_contains(data: dict) -> str:
    """Same 'Contains' text as `Economy.boxinfo` — keep in sync with that command."""
    c_min, c_max = data["cards_total"]
    j_min, j_max = data["rewards"]["jenny"]
    b_min, b_max = data["boosters_total"]
    return (
        f"{data['rewards_total']} total rewards\n{f'{c_min}-{c_max}' if c_max != c_min else c_min} cards\n"
        + (
            f"{j_min}-{j_max} jenny per field\n"
            if j_max > 0
            else "No jenny in this box\n"
        )
        + (
            ""
            if c_max == 0
            else (
                f"card rarities: {' or '.join(data['rewards']['cards']['rarities'])}\n"
                f"card types: {' or '.join(data['rewards']['cards']['types'])}"
            )
        )
        + (
            (
                (f"{b_min}" if b_min == b_max else f"\n{b_min}-{b_max}")
                + f" boosters\nAvailable boosters: {' '.join([BOOSTERS[int(x)]['emoji'] for x in data['rewards']['boosters']])}"
            )
            if b_max != 0
            else ""
        )
    )


class TestingEconomy(Testing):
    requires_command = True
    _menus_registered = False

    def __init__(self):
        if not TestingEconomy._menus_registered:
            TestingEconomy._menus_registered = True
        else:
            Economy._init_menus = lambda self: None
        super().__init__(cog=Economy)


class Jenny(TestingEconomy):

    def __init__(self):
        super().__init__()

    @test
    async def no_user_arg(self) -> None:
        user = await User.new(self.base_author.id)
        balance = user.jenny

        await self.command(self.cog, self.base_context)

        assert (
            self.base_context.result.message.content
            == f"{self.base_author.display_name}'s balance is {balance} Jenny"
        ), self.base_context.result.message.content

    @test
    async def user_not_found(self) -> None:
        original = self.cog.client.find_user

        async def _mock_find_user(ctx, user):
            return None

        self.cog.client.find_user = _mock_find_user
        await self.command(self.cog, self.base_context, user="nonexistent")
        self.cog.client.find_user = original

        assert (
            self.base_context.result.message.content == "User not found"
        ), self.base_context.result.message.content


class Daily(TestingEconomy):

    def __init__(self):
        super().__init__()

    @test
    async def cooldown_active(self) -> None:
        user = await User.new(self.base_author.id)
        user.daily_cooldown = datetime.now() + timedelta(hours=1)
        await user._update_val("cooldowndaily", user.daily_cooldown)

        await self.command(self.cog, self.base_context)

        assert (
            "You can claim your daily Jenny the next time"
            in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def available(self) -> None:
        KilluaGuild.cache.clear()
        user = await User.new(self.base_author.id)
        user.daily_cooldown = datetime.now() - timedelta(hours=1)
        await user._update_val("cooldowndaily", user.daily_cooldown)

        await self.command(self.cog, self.base_context)

        assert (
            "You claimed your" in self.base_context.result.message.content
            and "daily Jenny" in self.base_context.result.message.content
        ), self.base_context.result.message.content


class Inventory(TestingEconomy):

    def __init__(self):
        super().__init__()

    @test
    async def empty_inventory(self) -> None:
        user = await User.new(self.base_author.id)
        for lb in list(user.lootboxes):
            await user.remove_lootbox(lb)
        for b in list(user.boosters.keys()):
            while user.boosters.get(b, 0) > 0:
                await user.use_booster(int(b))

        await self.command(self.cog, self.base_context)

        assert (
            self.base_context.result.message.content
            == "Sadly you don't have any lootboxes or boosters!"
        ), self.base_context.result.message.content

    @test
    async def non_empty_inventory(self) -> None:
        user = await User.new(self.base_author.id)
        first_box_id = next(iter(LOOTBOXES.keys()))
        await user.add_lootbox(first_box_id)

        await self.command(self.cog, self.base_context)

        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert (
            self.base_context.result.message.embeds[0].title == "Lootbox inventory"
        ), self.base_context.result.message.embeds[0].title

        await user.remove_lootbox(first_box_id)


class Profile(TestingEconomy):

    def __init__(self):
        super().__init__()

    @test
    async def self_profile(self) -> None:
        KilluaGuild.cache.clear()
        await User.new(self.base_author.id)
        await self.command(self.cog, self.base_context, user=None)
        embeds = self.base_context.result.message.embeds
        embed = embeds[-1] if isinstance(embeds, list) else embeds[0]
        assert "Information about" in embed.title, embed.title

    @test
    async def user_not_found(self) -> None:
        KilluaGuild.cache.clear()
        original = self.cog.client.find_user

        async def _mock_find_user(ctx, user):
            return None

        self.cog.client.find_user = _mock_find_user
        await self.command(self.cog, self.base_context, user="notauser99999")
        self.cog.client.find_user = original

        assert (
            "Could not find user" in self.base_context.result.message.content
        ), self.base_context.result.message.content


class Boxinfo(TestingEconomy):

    def __init__(self):
        super().__init__()

    @test
    async def invalid_box(self) -> None:
        await self.command(self.cog, self.base_context, box="999")

        assert (
            self.base_context.result.message.content == "Invalid box name or id"
        ), self.base_context.result.message.content

    @test
    async def valid_box(self) -> None:
        box_id = 1
        data = LOOTBOXES[box_id]
        await self.command(self.cog, self.base_context, box=str(box_id))

        embed = self.base_context.result.message.embeds[0]
        assert embed.title == f"Infos about lootbox {data['emoji']} {data['name']}", (
            embed.title
        )
        assert embed.description == data["description"], embed.description

        by_name = {f.name: f.value for f in embed.fields}
        assert by_name["Contains"] == _expected_boxinfo_contains(data), (
            by_name["Contains"],
            _expected_boxinfo_contains(data),
        )
        assert str(by_name["Price"]) == str(data["price"]), by_name["Price"]
        assert by_name["Buyable"] == ("Yes" if data["available"] else "No"), (
            by_name["Buyable"]
        )


class Boosterinfo(TestingEconomy):

    def __init__(self):
        super().__init__()

    @test
    async def invalid_booster(self) -> None:
        await self.command(self.cog, self.base_context, booster="999")

        assert (
            self.base_context.result.message.content == "Invalid booster name or id"
        ), self.base_context.result.message.content

    @test
    async def valid_booster(self) -> None:
        await self.command(self.cog, self.base_context, booster="1")

        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds


class Open(TestingEconomy):

    def __init__(self):
        super().__init__()

    @test
    async def no_lootboxes(self) -> None:
        user = await User.new(self.base_author.id)
        for lb in list(user.lootboxes):
            await user.remove_lootbox(lb)

        await self.command(self.cog, self.base_context)

        assert (
            self.base_context.result.message.content
            == "Sadly you don't have any lootboxes!"
        ), self.base_context.result.message.content

    @test
    async def open_select_lootbox_runs_stub_open(self) -> None:
        """Path A: lootbox Select + view.wait; LootBox.open/generate_rewards stubbed."""
        from killua.utils.interactions import Select as KSelect

        user = await User.new(self.base_author.id)
        for lb in list(user.lootboxes):
            await user.remove_lootbox(lb)
        await user.add_lootbox(1)

        async def fake_gen(cls, box):
            return [10]

        async def fake_open(self):
            await self.ctx.send("stub-lootbox-opened")

        orig_gen = lootbox_mod.LootBox.generate_rewards
        orig_open = lootbox_mod.LootBox.open
        lootbox_mod.LootBox.generate_rewards = classmethod(fake_gen)  # type: ignore[assignment]
        lootbox_mod.LootBox.open = fake_open  # type: ignore[assignment]

        self.base_context.timeout_view = False

        async def _pick(ctx):
            v = ctx.current_view
            if not v:
                return
            for item in v.children:
                if isinstance(item, KSelect):
                    await item.callback(
                        ArgumentInteraction(
                            ctx,
                            message=ctx.result.message,
                            data={"values": ["1"]},
                        )
                    )
                    break
            if ctx.current_view:
                ctx.current_view.stop()

        _prev_rtv = self.base_context.respond_to_view
        self.base_context.respond_to_view = _pick
        try:
            with patch("killua.bot.randint", return_value=100):
                await self.command(self.cog, self.base_context)
        finally:
            lootbox_mod.LootBox.generate_rewards = orig_gen
            lootbox_mod.LootBox.open = orig_open
            self.base_context.respond_to_view = _prev_rtv

        assert "stub-lootbox-opened" in self.base_context.result.message.content, (
            self.base_context.result.message.content
        )


class Guild(TestingEconomy):

    def __init__(self):
        super().__init__()

    @test
    async def shows_guild_embed(self) -> None:
        await KilluaGuild.new(self.base_guild.id)

        async def _lb(ctx, limit=10):
            return {
                "points": 250,
                "top": [{"name": "RichUser", "points": 120}],
            }

        self.cog._lb = _lb
        await self.command(self.cog, self.base_context)

        emb = self.base_context.result.message.embeds
        if isinstance(emb, tuple):
            emb = emb[0]
        assert emb[0].title.startswith("Information about"), emb[0].title
        fields = {f.name: f.value for f in emb[0].fields}
        assert str(fields["Combined Jenny"]) == "250"
        assert "RichUser" in fields["Richest Member"]


class Leaderboard(TestingEconomy):

    def __init__(self):
        super().__init__()

    @test
    async def nobody_has_jenny(self) -> None:
        async def _lb(ctx, limit=10):
            return {"points": 0, "top": []}

        self.cog._lb = _lb
        await self.command(self.cog, self.base_context)

        assert (
            "Nobody here has any jenny" in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def lists_top_members(self) -> None:
        async def _lb(ctx, limit=10):
            return {
                "points": 900,
                "top": [
                    {"name": "First", "points": 500},
                    {"name": "Second", "points": 300},
                ],
            }

        self.cog._lb = _lb
        await self.command(self.cog, self.base_context)

        emb = self.base_context.result.message.embeds
        if isinstance(emb, tuple):
            emb = emb[0]
        assert "Top users" in emb[0].title
        assert "#1 `First` with `500` jenny" in emb[0].description
        assert "#2 `Second` with `300` jenny" in emb[0].description
