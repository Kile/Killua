from __future__ import annotations

from random import randint
from math import ceil
from datetime import datetime, timedelta
from unittest.mock import patch

from ..types import DiscordMember, Message, random_date
from ...utils.classes import User
from ..testing import Testing, test
from ...cogs.cards import Cards
from ...utils.classes.card import Card
from ...utils.paginator import Buttons
from ...static.constants import PRICES, DEF_SPELLS, VIEW_DEF_SPELLS

from ..fixtures import ensure_test_cards
from ..harnesses import embed_footer_page, press_paginator_button


class TestingCards(Testing):
    requires_command = True

    _cards_initialized = False

    def __init__(self):
        ensure_test_cards()

        super().__init__(cog=Cards)
        self._mock_cog_externals()

    def _mock_cog_externals(self):
        self.cog.reward_cache = {
            "item": Card.find(
                lambda c: c["type"] == "normal" and c["rank"] in ["A", "B", "C"]
            ),
            "spell": Card.find(
                lambda c: c["type"] == "spell" and c["rank"] in ["B", "C"]
            ),
            "monster": {
                "E": Card.find(
                    lambda c: c["type"] == "monster" and c["rank"] in ["E", "G", "H"]
                ),
                "D": Card.find(
                    lambda c: c["type"] == "monster" and c["rank"] in ["D", "E", "F"]
                ),
                "C": Card.find(
                    lambda c: c["type"] == "monster" and c["rank"] in ["C", "D", "E"]
                ),
            },
        }

        if not TestingCards._cards_initialized:
            from PIL import Image as PILImage
            from ...utils.classes.book import Book as BookClass

            async def _mock_create_image(self, data, restricted_slots, page):
                return PILImage.new("RGBA", (620 * 2, 400 * 2), (255, 255, 255, 255))

            BookClass.create_image = _mock_create_image
            TestingCards._cards_initialized = True


class Book(TestingCards):

    def __init__(self):
        super().__init__()

    @test
    async def test_with_no_cards(self) -> None:
        user = await User.new(self.base_context.author.id)
        await user.nuke_cards()

        await self.cog.book(self.cog, self.base_context)

        assert (
            self.base_context.result.message.content == "You don't have any cards yet!"
        ), self.base_context.result.message.content

    @test
    async def invalid_page_chosen(self) -> None:
        user = await User.new(self.base_author.id)
        await user.add_card(randint(1, 99))
        await self.cog.book(self.cog, self.base_context, page=8)

        assert (
            self.base_context.result.message.content
            == f"Please choose a page number between 1 and {6+ceil(len(user.fs_cards)/18)}"
        ), self.base_context.result.message.content

    @test
    async def page_below_one(self) -> None:
        user = await User.new(self.base_author.id)
        await user.add_card(randint(1, 99))
        await self.cog.book(self.cog, self.base_context, page=0)

        assert (
            self.base_context.result.message.content
            == f"Please choose a page number between 1 and {6+ceil(len(user.fs_cards)/18)}"
        ), self.base_context.result.message.content

    @test
    async def responds_with_valid_paginator(self) -> None:
        user = await User.new(self.base_author.id)
        await user.add_card(randint(1, 99))
        self.base_context.timeout_view = True
        await self.cog.book(self.cog, self.base_context)

        assert isinstance(self.base_context.current_view, Buttons), type(
            self.base_context.current_view
        )


class Sell(TestingCards):

    def __init__(self):
        super().__init__()

    @test
    async def no_arguments(self) -> None:
        await self.command(self.cog, self.base_context)

        assert self.base_context.result.message, self.base_context.result.message
        assert (
            self.base_context.result.message.content
            == "You need to specify what exactly to sell"
        ), self.base_context.result.message.content

    @test
    async def invalid_card_id(self) -> None:
        user = await User.new(self.base_author.id)
        await user.add_card(1)
        await self.command(self.cog, self.base_context, "99999")

        assert (
            self.base_context.result.message.content
            == "A card with the id `99999` does not exist"
        ), self.base_context.result.message.content

    @test
    async def cancel_sell(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        card = randint(1, 99)
        await user.add_card(card)

        await self.command(self.cog, self.base_context, card=str(card))

        assert (
            self.base_context.result.message.content == "Successfully canceled!"
        ), self.base_context.result.message.content
        assert (
            user.count_card(card, including_fakes=False) == 1
        ), user.count_card(card, including_fakes=False)

    @test
    async def sell_without_any_cards(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content == "You don't have any cards yet!"
        ), self.base_context.result.message.content

    @test
    async def selling_a_card_not_in_possession(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(6)

        await self.command(self.cog, self.base_context, "5")

        assert (
            self.base_context.result.message.content
            == "Seems you don't own enough copies of this card. You own 0 copies of this card"
        ), self.base_context.result.message.content

    @test
    async def sell_single_valid_card(self) -> None:
        self.base_context.timeout_view = False
        self.base_context.respond_to_view = Testing.press_confirm
        card = randint(1, 99)
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(card)
        await self.command(self.cog, self.base_context, card=str(card))

        assert (
            self.base_context.result.message.content
            == f"Successfully sold 1 copy of card {card} for {int(PRICES[Card(card).rank] * 0.1)} Jenny!"
        ), self.base_context.result.message.content
        assert (
            user.count_card(card, including_fakes=False) == 0
        ), user.count_card(card, including_fakes=False)

    @test
    async def sell_single_fake(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        card = randint(1, 99)
        await user.add_card(card, fake=True)
        await self.command(self.cog, self.base_context, card=str(card))

        assert (
            self.base_context.result.message.content
            == "Seems you don't own enough copies of this card. You own 0 copies of this card"
        ), self.base_context.result.message.content

    @test
    async def sell_more_cards_than_in_posession(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        card = randint(1, 99)
        await user.add_card(card)

        await self.command(self.cog, self.base_context, card=str(card), amount=2)
        assert (
            self.base_context.result.message.content
            == "Seems you don't own enough copies of this card. You own 1 copy of this card"
        ), self.base_context.result.message.content

    @test
    async def selling_multiple_cards(self) -> None:
        self.base_context.timeout_view = False
        self.base_context.respond_to_view = Testing.press_confirm
        user = await User.new(self.base_author.id)
        card = randint(1, 99)
        for _ in range(2):
            await user.add_card(card)
        await self.command(self.cog, self.base_context, card=str(card), amount=2)

        assert (
            self.base_context.result.message.content
            == f"Successfully sold 2 copies of card {card} for {int(PRICES[Card(card).rank] * 0.2)} Jenny!"
        ), self.base_context.result.message.content
        assert (
            user.count_card(card, including_fakes=False) == 0
        ), user.count_card(card, including_fakes=False)

    @test
    async def selling_multiple_cards_with_fake(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        card = randint(1, 99)
        await user.add_card(card)
        await user.add_card(card, fake=True)

        await self.command(self.cog, self.base_context, card=str(card), amount=2)

        assert (
            self.base_context.result.message.content
            == "Seems you don't own enough copies of this card. You own 1 copy of this card"
        ), self.base_context.result.message.content

        await user.remove_card(card, remove_fake=True)
        await user.remove_card(card)

    @test
    async def sell_all_of_category_when_owning_none(self) -> None:
        user = await User.new(self.base_author.id)
        await user.add_card(1)
        self.base_context.respond_to_view = self.press_confirm
        await self.command(self.cog, self.base_context, sell_opt="monsters")

        assert (
            self.base_context.result.message.content
            == "You don't have any cards of that type to sell!"
        ), self.base_context.result.message.content

    @test
    async def sell_all_of_category(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(572)
        await user.add_card(697)

        self.base_context.respond_to_view = self.press_confirm
        await self.command(self.cog, self.base_context, sell_opt="monsters")

        assert (
            self.base_context.result.message.content
            == f"You sold all your monsters for {int((PRICES[Card(572).rank] + PRICES[Card(697).rank]) * 0.1)} Jenny!"
        ), self.base_context.result.message.content
        assert (
            user.count_card(572, including_fakes=False) == 0
            and user.count_card(697, including_fakes=False) == 0
        ), (
            user.count_card(572, including_fakes=False) == 0
            and user.count_card(697, including_fakes=False) == 0
        )

    @test
    async def sell_all_of_category_with_fake(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(572)
        await user.add_card(697, fake=True)

        self.base_context.respond_to_view = self.press_confirm
        await self.command(self.cog, self.base_context, sell_opt="monsters")

        assert (
            self.base_context.result.message.content
            == f"You sold all your monsters for {int(PRICES[Card(572).rank] * 0.1)} Jenny!"
        ), self.base_context.result.message.content
        assert (
            user.count_card(572, including_fakes=False) == 0
            and user.count_card(697, including_fakes=True) == 1
        ), (
            user.count_card(572, including_fakes=False) == 0
            and user.count_card(697, including_fakes=True) == 1
        )


class Swap(TestingCards):

    def __init__(self):
        super().__init__()

    @test
    async def swap_when_none_owned(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")

        await self.command(self.cog, self.base_context, card=str(randint(1, 99)))
        assert (
            self.base_context.result.message.content == "You don't have any cards yet!"
        ), self.base_context.result.message.content

    @test
    async def invalid_card(self) -> None:
        await self.command(self.cog, self.base_context, card="10000")

        assert (
            self.base_context.result.message.content
            == "Please use a valid card number!"
        ), self.base_context.result.message.content

    @test
    async def swap_card_0(self) -> None:
        await self.command(self.cog, self.base_context, card="0")

        assert (
            self.base_context.result.message.content
            == "You cannot swap out card No. 0!"
        ), self.base_context.result.message.content

    @test
    async def swap_non_owned_card(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(1)

        await self.command(self.cog, self.base_context, card="2")

        assert (
            self.base_context.result.message.content
            == f"You don't own a fake and real copy of card `{Card('2').name}` you can swap out!"
        ), self.base_context.result.message.content

    @test
    async def swap_single_owned_card(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(1)

        await self.command(self.cog, self.base_context, card="1")

        assert (
            self.base_context.result.message.content
            == f"You don't own a fake and real copy of card `{Card('1').name}` you can swap out!"
        ), self.base_context.result.message.content

    @test
    async def swap_two_non_fakes(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")

        await user.add_card(1)
        await user.add_card(1)

        await self.command(self.cog, self.base_context, card="1")

        assert (
            self.base_context.result.message.content
            == f"You don't own a fake and real copy of card `{Card('1').name}` you can swap out!"
        ), self.base_context.result.message.content

    @test
    async def correct_usage(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")

        await user.add_card(1, fake=True)
        await user.add_card(1)

        await self.command(self.cog, self.base_context, card="1")

        assert (
            self.base_context.result.message.content
            == f"Successfully swapped out card {Card('1').name}"
        ), self.base_context.result.message.content
        assert not user.rs_cards[0][1]["fake"], user.rs_cards[0][1]["fake"]
        assert user.fs_cards[0][1]["fake"], user.fs_cards[0][1]["fake"]


class Hunt(TestingCards):
    def __init__(self):
        super().__init__()

    @test
    async def hunt_time_when_not_hunting(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("effects")
        await self.command(self.cog, self.base_context, option="time")

        assert (
            self.base_context.result.message.content == "You are not on a hunt yet!"
        ), self.base_context.result.message.content

    @test
    async def hunt_time_when_hunting(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("effects")

        started_at = random_date()
        await user.add_effect("hunting", started_at)

        await self.command(self.cog, self.base_context, option="time")

        assert (
            self.base_context.result.message.content
            == f"You've started hunting <t:{int(started_at.timestamp())}:R>."
        ), self.base_context.result.message.content

    @test
    async def hunt_end_when_not_hunting(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("effects")
        await self.command(self.cog, self.base_context, option="end")

        assert (
            self.base_context.result.message.content
            == "You aren't on a hunt yet! Start one with `/cards hunt`"
        ), self.base_context.result.message.content

    @test
    async def end_hunt_below_12h(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("effects")

        started_at = datetime.now() - timedelta(minutes=10)
        await user.add_effect("hunting", started_at)

        await self.command(self.cog, self.base_context, option="end")

        assert (
            self.base_context.result.message.content
            == "You must be at least hunting for twelve hours!"
        ), self.base_context.result.message.content

    @test
    async def end_hunt_correctly(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")

        started_at = datetime.now() - timedelta(hours=20)
        await user.add_effect("hunting", started_at)

        await self.command(self.cog, self.base_context, option="end")

        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert (
            self.base_context.result.message.embeds[0].title == "Hunt returned!"
        ), self.base_context.result.message.embeds[0].title
        assert self.base_context.result.message.embeds[0].description.startswith(
            f"You've started hunting <t:{int(started_at.timestamp())}:R>. You brought back the following items from your hunt: \n\n"
        ), self.base_context.result.message.embeds[0].description
        assert not user.has_effect("hunting")[0], user.has_effect("hunting")
        assert len(user.all_cards) > 0, user.all_cards

    @test
    async def start_hunting_when_on_hunt(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("effects")

        started_at = random_date()
        await user.add_effect("hunting", started_at)

        await self.command(self.cog, self.base_context, option="start")

        assert (
            self.base_context.result.message.content
            == "You are already on a hunt! Get the results with `/cards hunt end`"
        ), self.base_context.result.message.content

    @test
    async def start_hunting_correctly(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("effects")

        await self.command(self.cog, self.base_context, option="start")

        assert (
            self.base_context.result.message.content
            == "You went hunting! Make sure to claim your rewards at least twelve hours from now, but remember, the longer you hunt, the more you get"
        ), self.base_context.result.message.content
        assert user.has_effect("hunting")[0], user.has_effect("hunting")[0]
        assert datetime.now() - user.effects["hunting"] < timedelta(
            minutes=1
        ), user.effects["hunting"]


class Meet(TestingCards):
    def __init__(self):
        super().__init__()

    @test
    async def target_is_bot(self) -> None:
        other = DiscordMember(bot=True)

        await self.command(self.cog, self.base_context, other)

        assert (
            self.base_context.result.message.content
            == "You can't interact with bots with this command"
        ), self.base_context.result.message.content

    @test
    async def no_recent_messages(self) -> None:
        other = DiscordMember()

        messages = [
            Message(author=DiscordMember(), channel=self.base_context.channel)
            for _ in range(10)
        ]
        self.base_context.channel.history_return = messages

        await self.command(self.cog, self.base_context, other)

        assert (
            self.base_context.result.message.content
            == "The user you tried to approach has not send a message in this channel recently"
        ), self.base_context.result.message.content

    @test
    async def already_met(self) -> None:
        user = await User.new(self.base_author.id)
        other = DiscordMember()

        messages = [
            Message(author=DiscordMember(), channel=self.base_context.channel)
            for _ in range(10)
        ]
        messages.extend(
            [Message(author=other, channel=self.base_context.channel)]
        )
        self.base_context.channel.history_return = messages
        self.base_channel.history_return = messages

        await user.add_met_user(other.id)

        await self.command(self.cog, self.base_context, other)

        assert (
            self.base_context.result.message.content
            == f"You already have `{other}` in the list of users you met, {self.base_author.display_name}"
        ), self.base_context.result.message.content

    @test
    async def meet_correctly(self) -> None:
        user = await User.new(self.base_author.id)
        other = DiscordMember()

        messages = [
            Message(author=DiscordMember(), channel=self.base_context.channel)
            for _ in range(10)
        ]
        messages.extend(
            [Message(author=other, channel=self.base_context.channel)]
        )
        self.base_context.channel.history_return = messages
        self.base_channel.history_return = messages

        await self.command(self.cog, self.base_context, other)

        assert (
            self.base_context.result.message.content
            == f"Done {self.base_author.mention}! Successfully added `{other}` to the list of people you've met"
        ), self.base_context.result.message.content
        assert user.has_met(other.id), user.met_user


class Discard(TestingCards):

    def __init__(self):
        super().__init__()

    @test
    async def discord_non_existent_card(self) -> None:
        await self.command(self.cog, self.base_context, "non_existent_card")

        assert (
            self.base_context.result.message.content == "This card does not exist!"
        ), self.base_context.result.message.content

    @test
    async def discard_not_in_posession_card(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == "You are not in possession of this card!"
        ), self.base_context.result.message.content

    @test
    async def discard_card_0(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(0)

        await self.command(self.cog, self.base_context, "0")

        assert (
            self.base_context.result.message.content == "You cannot discard this card!"
        ), self.base_context.result.message.content

    @test
    async def cancel_discard(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(1)

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content == "Successfully cancelled!"
        ), self.base_context.result.message.content

    @test
    async def discard_correctly(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(1)

        self.base_context.respond_to_view = self.press_confirm

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == "Successfully thrown away card No. `1`"
        ), self.base_context.result.message.content
        assert not user.has_any_card(1), user.has_any_card(1)


class Cardinfo(TestingCards):

    def __init__(self):
        super().__init__()

    @test
    async def invalid_card(self) -> None:
        await self.command(self.cog, self.base_context, "invalid")

        assert (
            self.base_context.result.message.content == "Invalid card"
        ), self.base_context.result.message.content

    @test
    async def card_not_owned(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == "You don't own a copy of this card so you can't view its infos"
        ), self.base_context.result.message.content

    @test
    async def correct_usage(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(1)

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert (
            self.base_context.result.message.embeds[0].title == "Info about card 1"
        ), self.base_context.result.message.embeds[0].title
        assert (
            self.base_context.result.message.embeds[0].description
            == Card("1").description
        ), self.base_context.result.message.embeds[0].description


class Check(TestingCards):

    def __init__(self):
        super().__init__()

    @test
    async def invalid_card(self) -> None:
        await self.command(self.cog, self.base_context, "invalid")

        assert (
            self.base_context.result.message.content == "Invalid card"
        ), self.base_context.result.message.content

    @test
    async def card_not_owned(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == "You don't own any copies of this card which are fake"
        ), self.base_context.result.message.content

    @test
    async def owned_but_not_fake(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(1)

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == "You don't own any copies of this card which are fake"
        ), self.base_context.result.message.content

    @test
    async def restricted_slots_fake(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(1, fake=True)
        await user.add_card(1)

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == "The card in your restricted slots is fake"
        ), self.base_context.result.message.content

    @test
    async def free_slots_fake(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(1)
        await user.add_card(1, fake=True)

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == "1 copy of this card in your free slots is fake"
        ), self.base_context.result.message.content

    @test
    async def restricted_slots_and_free_slots_fake(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(1, fake=True)
        await user.add_card(1, fake=True)
        await user.add_card(1, fake=True)

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == "The card in your restricted slots is fake and 2 copies of this card in your free slots are fake"
        ), self.base_context.result.message.content


class TestingUseSpell(TestingCards):
    """Base for per-spell ``use`` integration tests."""

    command_name = "use"

    def __init__(self):
        super().__init__()

        async def _test_prefix(bot, message):
            return ("!", "!", "killua ")

        self.base_context.bot.command_prefix = _test_prefix


class Use(TestingUseSpell):

    def __init__(self):
        super().__init__()

    @test
    async def invalid_card(self) -> None:
        await self.command(self.cog, self.base_context, item="invalid")

        assert (
            self.base_context.result.message.content == "Invalid card id"
        ), self.base_context.result.message.content

    @test
    async def not_in_possession(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")

        await self.command(self.cog, self.base_context, item="1011")

        assert (
            self.base_context.result.message.content
            == "You are not in possesion of this card!"
        ), self.base_context.result.message.content

    @test
    async def non_spell_card(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(572)

        await self.command(self.cog, self.base_context, item="572")

        assert (
            self.base_context.result.message.content
            == "You can only use spell cards!"
        ), self.base_context.result.message.content

    @test
    async def defense_spell(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(DEF_SPELLS[0])

        await self.command(self.cog, self.base_context, item=str(DEF_SPELLS[0]))

        assert (
            self.base_context.result.message.content
            == "You can only use this card in response to an attack!"
        ), self.base_context.result.message.content

    @test
    async def view_defense_spell(self) -> None:
        user = await User.new(self.base_author.id)
        await user.nuke_cards("all")
        await user.add_card(VIEW_DEF_SPELLS[0])

        await self.command(self.cog, self.base_context, item=str(VIEW_DEF_SPELLS[0]))

        assert (
            self.base_context.result.message.content
            == "You can only use this card in response to an attack!"
        ), self.base_context.result.message.content

    @test
    async def booklet_paginator_next_page(self) -> None:
        """Path A: `use booklet` embed paginator advances with next (not `book`, which uses has_file)."""
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
            with patch("killua.bot.randint", return_value=100):
                await self.command(self.cog, self.base_context, item="booklet")
        finally:
            self.base_context.respond_to_view = _prev_rtv
        emb = self.base_context.result.message.embeds[0]
        fp = embed_footer_page(emb)
        assert fp == (2, 6), fp
        assert "**rank**" in (emb.description or ""), emb.description


from . import cards_use_spells  # noqa: E402, F401 — register per-spell use tests
