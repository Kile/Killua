from ..types import *
from ...utils.classes import *
from ..testing import Testing, test
from ...static.constants import editing, DB
from ...cogs.shop import Shop
from ...static.constants import LOOTBOXES, PRICES
from ..types.member import TestingMember
from ...static.cards import Card

import copy
from unittest.mock import patch, AsyncMock

from ..harnesses import embed_footer_page, press_paginator_button

from pathlib import Path
from datetime import datetime
import json


def _ensure_card_catalog() -> None:
    if Card.raw:
        return
    cards_file = Path(__file__).parents[3] / "cards.json"
    if cards_file.exists():
        with open(cards_file) as f:
            Card.raw = json.load(f)


class TestingShop(Testing):
    requires_command = True

    def __init__(self):
        _ensure_card_catalog()
        super().__init__(cog=Shop)
        self.base_context.command = self.command

    async def _ensure_shop_const(self) -> None:
        sh = await DB.const.find_one({"_id": "shop"})
        _seed_shop_offers_sync((sh or {}).get("offers", []))


class Jenny(TestingShop):

    def __init__(self):
        super().__init__()

    @test
    async def give_to_self(self) -> None:
        other = TestingMember(id=self.base_author.id)
        await self.command(self.cog, self.base_context, other, amount=10)
        assert (
            self.base_context.result.message.content
            == "You can't give yourself anything!"
        ), self.base_context.result.message.content

    @test
    async def give_to_bot(self) -> None:
        other = TestingMember(bot=True)
        await self.command(self.cog, self.base_context, other, amount=10)
        assert (
            self.base_context.result.message.content == "\U0001f916"
        ), self.base_context.result.message.content

    @test
    async def less_than_one(self) -> None:
        other = TestingMember()
        await self.command(self.cog, self.base_context, other, amount=0)
        assert (
            self.base_context.result.message.content
            == "You can't transfer less than 1 Jenny!"
        ), self.base_context.result.message.content

    @test
    async def not_enough_jenny(self) -> None:
        user = await User.new(self.base_author.id)
        await user.remove_jenny(user.jenny)
        other = TestingMember()
        await self.command(self.cog, self.base_context, other, amount=100)
        assert (
            self.base_context.result.message.content
            == "You can't transfer more Jenny than you have"
        ), self.base_context.result.message.content

    @test
    async def success(self) -> None:
        user = await User.new(self.base_author.id)
        await user.add_jenny(100)
        other = TestingMember()
        await self.command(self.cog, self.base_context, other, amount=10)
        assert (
            "transferred" in self.base_context.result.message.content
            and "Jenny" in self.base_context.result.message.content
        ), self.base_context.result.message.content


class Lootbox(TestingShop):

    def __init__(self):
        super().__init__()

    @test
    async def invalid_box(self) -> None:
        await self.command(self.cog, self.base_context, box="999")
        assert (
            self.base_context.result.message.content
            == "This lootbox is not for sale!"
        ), self.base_context.result.message.content

    @test
    async def not_enough_jenny(self) -> None:
        first_box_id = next(k for k, v in LOOTBOXES.items() if v["available"])
        user = await User.new(self.base_author.id)
        await user.remove_jenny(user.jenny)
        await self.command(self.cog, self.base_context, box=str(first_box_id))
        assert (
            "don't have enough jenny" in self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def success(self) -> None:
        first_box_id = next(k for k, v in LOOTBOXES.items() if v["available"])
        price = LOOTBOXES[first_box_id]["price"]
        user = await User.new(self.base_author.id)
        await user.add_jenny(price)
        await self.command(self.cog, self.base_context, box=str(first_box_id))
        assert (
            "Successfully bought lootbox" in self.base_context.result.message.content
        ), self.base_context.result.message.content


class Lootboxes(TestingShop):

    def __init__(self):
        super().__init__()

    @test
    async def shop_paginator_next_page(self) -> None:
        """Path A: shop lootboxes uses ShopPaginator when >10 boxes; patch start to avoid menu re-invoke."""
        from ...cogs.shop import ShopPaginator
        from ...utils.paginator import Paginator

        extra = {}
        for i in range(10001, 10013):
            d = copy.deepcopy(LOOTBOXES[1])
            d["name"] = f"Test paginator box {i}"
            d["available"] = True
            extra[i] = d
        orig_start = ShopPaginator.start
        ShopPaginator.start = Paginator.start
        self.base_context.timeout_view = False

        async def _next(ctx):
            await press_paginator_button(
                ctx.current_view,
                "next",
                context=ctx,
                message=ctx.result.message,
            )
            ctx.current_view.stop()

        _prev_rtv = self.base_context.respond_to_view
        self.base_context.respond_to_view = _next
        try:
            LOOTBOXES.update(extra)
            with patch("killua.bot.randint", return_value=100):
                await self.command(self.cog, self.base_context)
        finally:
            for k in extra:
                LOOTBOXES.pop(k, None)
            ShopPaginator.start = orig_start
            self.base_context.respond_to_view = _prev_rtv

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
        fp = embed_footer_page(emb)
        assert fp is not None, emb.footer
        assert fp[0] == 2 and fp[1] >= 2, fp


def _seed_shop_offers_sync(card_ids: list) -> None:
    """Mutate shared test DB.const collection (same store as DB.const property)."""
    coll = DB.const.db.setdefault("const", [])
    for doc in coll:
        if doc.get("_id") == "shop":
            doc["offers"] = card_ids
            doc["reduced"] = None
            doc.setdefault("log", [])
            return
    coll.append({"_id": "shop", "offers": card_ids, "reduced": None, "log": []})


async def _seed_shop_offers(card_ids: list) -> None:
    _seed_shop_offers_sync(card_ids)


class ShopCmd(TestingShop):
    command_name = "shop"

    def __init__(self):
        super().__init__()

    @test
    async def main_shop_embed(self) -> None:
        await self.command(self.cog, self.base_context)
        assert self.base_context.result.message.embeds

    @test
    async def shop_select_invokes_subcommand(self) -> None:
        """Top-level shop: select menu invokes the chosen subcommand."""
        from killua.utils.interactions import Select as KSelect

        subcommands = list(self.command.commands)
        target = next(c for c in subcommands if c.name == "cards")

        self.base_context.timeout_view = False
        _prev_invoke = self.base_context.invoke
        invoke_mock = AsyncMock(wraps=_prev_invoke)
        self.base_context.invoke = invoke_mock

        async def pick_cards_shop(ctx):
            select = None
            for child in ctx.current_view.children:
                if isinstance(child, KSelect):
                    select = child
                    break
            assert select is not None
            idx = str(subcommands.index(target))
            await select.callback(
                ArgumentInteraction(ctx, data={"values": [idx]})
            )
            ctx.current_view.stop()

        _prev = self.base_context.respond_to_view
        self.base_context.respond_to_view = pick_cards_shop
        try:
            await self.command(self.cog, self.base_context)
        finally:
            self.base_context.respond_to_view = _prev
            self.base_context.invoke = _prev_invoke

        invoke_mock.assert_awaited_once()
        assert invoke_mock.await_args[0][0].name == "cards"


class CardsShopCmd(TestingShop):
    command_name = "cards"

    def __init__(self):
        super().__init__()

    @test
    async def cards_shop_embed(self) -> None:
        await self._ensure_shop_const()
        self.cog.last_update = datetime.now()
        self.base_context.timeout_view = True
        await self.command(self.cog, self.base_context)
        assert self.base_context.result.message.embeds


class TodoShopCmd(TestingShop):
    command_name = "todo"

    def __init__(self):
        super().__init__()

    @test
    async def todo_shop_embed(self) -> None:
        await self.command(self.cog, self.base_context)
        assert self.base_context.result.message.embeds


class BuyCmd(TestingShop):
    command_name = "buy"

    def __init__(self):
        super().__init__()

    @test
    async def buy_without_item(self) -> None:
        await self.command(self.cog, self.base_context)
        assert self.base_context.result.message.content

    def _buy_subcommand(self, name: str):
        from discord.ext.commands import Command

        for command in self.cog.walk_commands():
            if (
                isinstance(command, Command)
                and command.name == name
                and getattr(command.parent, "name", None) == "buy"
            ):
                return command
        raise AssertionError(f"buy {name} subcommand not found")

    @test
    async def buy_space_insufficient_jenny(self) -> None:
        from ...utils.classes.todo import TodoList

        todo_list = await TodoList.create(
            owner=self.base_author.id,
            title="Poor list",
            status="public",
            done_delete=False,
        )
        editing[self.base_author.id] = todo_list.id
        user = await User.new(self.base_author.id)
        await user.set_jenny(0)

        await self._buy_subcommand("todo")(self.cog, self.base_context, what="space")

        assert "don't have enough Jenny" in (
            self.base_context.result.message.content
        ), self.base_context.result.message.content
        assert user.jenny == 0

    @test
    async def buy_space_cancel(self) -> None:
        from ...utils.classes.todo import TodoList

        todo_list = await TodoList.create(
            owner=self.base_author.id,
            title="Cancel list",
            status="public",
            done_delete=False,
        )
        editing[self.base_author.id] = todo_list.id
        user = await User.new(self.base_author.id)
        await user.add_jenny(50_000)
        spots_before = todo_list.spots

        self.base_context.timeout_view = False
        self.base_context.respond_to_view = Testing.press_cancel

        await self._buy_subcommand("todo")(self.cog, self.base_context, what="space")

        assert "see you later" in (
            self.base_context.result.message.content.lower()
        ), self.base_context.result.message.content
        refreshed = await TodoList.new(todo_list.id)
        assert refreshed.spots == spots_before

    @test
    async def buy_lootbox_insufficient_jenny_via_buy(self) -> None:
        first_box_id = next(k for k, v in LOOTBOXES.items() if v["available"])
        user = await User.new(self.base_author.id)
        await user.set_jenny(0)

        await self._buy_subcommand("lootbox")(
            self.cog, self.base_context, box=str(first_box_id)
        )

        assert "don't have enough jenny" in (
            self.base_context.result.message.content.lower()
        ), self.base_context.result.message.content

    @test
    async def buy_lootbox_success_deducts_jenny(self) -> None:
        first_box_id = next(k for k, v in LOOTBOXES.items() if v["available"])
        price = LOOTBOXES[first_box_id]["price"]
        user = await User.new(self.base_author.id)
        await user.set_jenny(price + 100)
        before = user.jenny

        await self._buy_subcommand("lootbox")(
            self.cog, self.base_context, box=str(first_box_id)
        )

        assert "Successfully bought lootbox" in (
            self.base_context.result.message.content
        ), self.base_context.result.message.content
        user = await User.new(self.base_author.id)
        assert user.jenny == before - price

    @test
    async def buy_card_insufficient_jenny(self) -> None:
        card_id = 572
        await _seed_shop_offers([card_id])
        user = await User.new(self.base_author.id)
        await user.set_jenny(0)
        price = PRICES[Card(card_id).rank]

        await self._buy_subcommand("card")(self.cog, self.base_context, item=str(card_id))

        assert "don't have enough Jenny" in (
            self.base_context.result.message.content
        ), self.base_context.result.message.content
        assert user.jenny == 0
        user = await User.new(self.base_author.id)
        assert not user.has_any_card(card_id)

    @test
    async def buy_card_success_deducts_jenny(self) -> None:
        card_id = 572
        await _seed_shop_offers([card_id])
        user = await User.new(self.base_author.id)
        price = PRICES[Card(card_id).rank]
        await user.add_jenny(price + 50)
        before = user.jenny

        await self._buy_subcommand("card")(self.cog, self.base_context, item=str(card_id))

        assert "Successfully bought card" in (
            self.base_context.result.message.content
        ), self.base_context.result.message.content
        user = await User.new(self.base_author.id)
        assert user.jenny == before - price
        assert user.has_any_card(card_id)

    @test
    async def buy_space_confirm_adds_spots(self) -> None:
        """One ConfirmButton on ctx.send — press confirm via respond_to_view."""
        from ...utils.classes.todo import TodoList

        todo_list = await TodoList.create(
            owner=self.base_author.id,
            title="Shop list",
            status="public",
            done_delete=False,
        )
        editing[self.base_author.id] = todo_list.id
        user = await User.new(self.base_author.id)
        await user.add_jenny(50_000)
        jenny_before = user.jenny
        spots_before = todo_list.spots
        cost = int(100 * todo_list.spots * 0.5)

        self.base_context.timeout_view = False
        self.base_context.respond_to_view = Testing.press_confirm

        await self._buy_subcommand("todo")(
            self.cog, self.base_context, what="space"
        )

        assert "bought 10 more todo spots" in (
            self.base_context.result.message.content
        ), self.base_context.result.message.content
        refreshed = await TodoList.new(todo_list.id)
        assert refreshed.spots == spots_before + 10, refreshed.spots
        user = await User.new(self.base_author.id)
        assert user.jenny == jenny_before - cost

