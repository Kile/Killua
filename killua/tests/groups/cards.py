from ..types import *
from ...utils.classes import *
from ..testing import Testing, test
from ...cogs.cards import Cards
from ...static.cards import Card
from ...utils.paginator import Buttons
from ...static.constants import PRICES
from killua.static.enums import SellOptions

from random import randint
from math import ceil
from datetime import datetime, timedelta


class TestingCards(Testing):

    def __init__(self):
        super().__init__(cog=Cards)


class Book(TestingCards):

    def __init__(self):
        super().__init__()

    @test
    async def test_with_no_cards(self) -> None:
        User(self.base_context.author.id).nuke_cards()

        await self.cog.book(self.cog, self.base_context)

        assert (
            self.base_context.result.message.content == "You don't have any cards yet!"
        ), self.base_context.result.message.content

    @test
    async def invalid_page_chosen(self) -> None:
        user = User(self.base_author.id)
        user.add_card(
            randint(1, 99)
        )  # To prevent no cards error as that check is before this one
        await self.cog.book(self.cog, self.base_context, page=8)

        assert (
            self.base_context.result.message.content
            == f"Please choose a page number between 1 and {6+ceil(len(user.fs_cards)/18)}"
        ), self.base_context.result.message.content

    @test
    async def responds_with_valid_paginator(self) -> None:
        user = User(self.base_author.id)
        user.add_card(
            randint(1, 99)
        )  # To prevent no cards error as that check is before this one
        self.base_context.timeout_view = (
            True  # Make the view instantly time out to prevent long wait
        )
        await self.cog.book(self.cog, self.base_context)

        assert isinstance(self.base_context.result.message.view, Buttons), isinstance(
            self.base_context.result.message.view, Buttons
        )


class Sell(TestingCards):

    def __init__(self):
        super().__init__()
        self.user = User(self.base_author.id)

    @test
    async def no_arguments(self) -> None:
        await self.command(self.cog, self.base_context)

        assert self.base_context.result.message, self.base_context.result.message
        assert (
            self.base_context.result.message.content
            == "You need to specify what exactly to sell"
        ), self.base_context.result.message.content

    @test
    async def sell_without_any_cards(self) -> None:
        self.user.nuke_cards("all")
        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content == "You don't have any cards yet!"
        ), self.base_context.result.message.content

    @test
    async def selling_a_card_not_in_possession(self) -> None:
        self.user.add_card(
            6
        )  # Add a card to avoid "You don't have any cards yet!" error

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
        self.user.nuke_cards("all")
        self.user.add_card(card)
        await self.command(self.cog, self.base_context, card=str(card))

        assert (
            self.base_context.result.message.content
            == f"Successfully sold 1 copy of card {card} for {int(PRICES[Card(card).rank] * 0.1)} Jenny!"
        ), self.base_context.result.message.content
        assert (
            self.user.count_card(card, including_fakes=False) == 0
        ), self.user.count_card(card, including_fakes=False)

    @test
    async def sell_single_fake(self) -> None:
        card = randint(1, 99)
        self.user.add_card(card, fake=True)
        await self.command(self.cog, self.base_context, card=str(card))

        assert (
            self.base_context.result.message.content
            == "Seems you don't own enough copies of this card. You own 0 copies of this card"
        ), self.base_context.result.message.content

    @test
    async def sell_more_cards_than_in_posession(self) -> None:
        card = randint(1, 99)
        self.user.add_card(card)

        await self.command(self.cog, self.base_context, card=str(card), amount=2)
        assert (
            self.base_context.result.message.content
            == "Seems you don't own enough copies of this card. You own 1 copy of this card"
        ), self.base_context.result.message.content

    @test
    async def selling_multiple_cards(self) -> None:
        self.base_context.timeout_view = False

        self.base_context.respond_to_view = Testing.press_confirm
        card = randint(1, 99)
        for _ in range(2):
            self.user.add_card(card)
        await self.command(self.cog, self.base_context, card=str(card), amount=2)

        assert (
            self.base_context.result.message.content
            == f"Successfully sold 2 copies of card {card} for {int(PRICES[Card(card).rank] * 0.2)} Jenny!"
        ), self.base_context.result.message.content
        assert (
            self.user.count_card(card, including_fakes=False) == 0
        ), self.user.count_card(card, including_fakes=False)

    @test
    async def selling_multiple_cards_with_fake(self) -> None:
        card = randint(1, 99)
        self.user.add_card(card)
        self.user.add_card(card, fake=True)

        await self.command(self.cog, self.base_context, card=str(card), amount=2)

        assert (
            self.base_context.result.message.content
            == "Seems you don't own enough copies of this card. You own 1 copy of this card"
        ), self.base_context.result.message.content

        self.user.remove_card(card, remove_fake=True) and self.user.remove_card(card)

    @test
    async def sell_all_of_category_when_owning_none(self) -> None:
        self.user.add_card(
            1
        )  # So there won't be the generic "you have no cards" error message
        self.base_context.respond_to_view = self.press_confirm
        await self.command(self.cog, self.base_context, type=SellOptions.monsters)

        assert (
            self.base_context.result.message.content
            == "You don't have any cards of that type to sell!"
        ), self.base_context.result.message.content

    @test
    async def sell_all_of_category(self) -> None:
        self.user.add_card(572)
        self.user.add_card(697)

        self.base_context.respond_to_view = self.press_confirm
        await self.command(self.cog, self.base_context, type=SellOptions.monsters)

        assert (
            self.base_context.result.message.content
            == f"You sold all your monsters for {int((PRICES[Card(572).rank] + PRICES[Card(697).rank]) * 0.1)} Jenny!"
        ), self.base_context.result.message.content
        assert (
            self.user.count_card(572, including_fakes=False) == 0
            and self.user.count_card(697, including_fakes=False) == 0
        ), (
            self.user.count_card(572, including_fakes=False) == 0
            and self.user.count_card(697, including_fakes=False) == 0
        )

    @test
    async def sell_all_of_category_with_fake(self) -> None:
        self.user.add_card(572)
        self.user.add_card(697, fake=True)

        self.base_context.respond_to_view = self.press_confirm
        await self.command(self.cog, self.base_context, type=SellOptions.monsters)

        assert (
            self.base_context.result.message.content
            == f"You sold all your monsters for {int(PRICES[Card(572).rank] * 0.1)} Jenny!"
        ), self.base_context.result.message.content
        assert (
            self.user.count_card(572, including_fakes=False) == 0
            and self.user.count_card(697, including_fakes=True) == 1
        ), (
            self.user.count_card(572, including_fakes=False) == 0
            and self.user.count_card(697, including_fakes=True) == 1
        )


class Swap(TestingCards):

    def __init__(self):
        super().__init__()
        self.user = User(self.base_author.id)

    @test
    async def swap_when_none_owned(self) -> None:
        self.user.nuke_cards("all")

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
        self.user.nuke_cards("all")
        self.user.add_card(1)

        await self.command(self.cog, self.base_context, card="2")

        assert (
            self.base_context.result.message.content
            == f"You don't own a fake and real copy of card `{Card('2').name}` you can swap out!"
        ), self.base_context.result.message.content

    @test
    async def swap_single_owned_card(self) -> None:
        self.user.nuke_cards("all")
        self.user.add_card(1)

        await self.command(self.cog, self.base_context, card="1")

        assert (
            self.base_context.result.message.content
            == f"You don't own a fake and real copy of card `{Card('1').name}` you can swap out!"
        ), self.base_context.result.message.content

    @test
    async def swap_two_non_fakes(self) -> None:
        self.user.nuke_cards("all")

        self.user.add_card(1)
        self.user.add_card(1)

        await self.command(self.cog, self.base_context, card="1")

        assert (
            self.base_context.result.message.content
            == f"You don't own a fake and real copy of card `{Card('1').name}` you can swap out!"
        ), self.base_context.result.message.content

    @test
    async def correct_usage(self) -> None:
        self.user.nuke_cards("all")

        self.user.add_card(1, fake=True)
        self.user.add_card(1)

        await self.command(self.cog, self.base_context, card="1")

        assert (
            self.base_context.result.message.content
            == f"Successfully swapped out card {Card('1').name}"
        ), self.base_context.result.message.content
        assert not self.user.rs_cards[0][1]["fake"], self.user.rs_cards[0][1]["fake"]
        assert self.user.fs_cards[0][1]["fake"], self.user.fs_cards[0][1]["fake"]


class Hunt(TestingCards):
    def __init__(self):
        super().__init__()
        self.user = User(self.base_author.id)

    @test
    async def hunt_time_when_not_hunting(self) -> None:
        self.user.nuke_cards("effects")
        await self.command(self.cog, self.base_context, option=HuntOptions.time)

        assert (
            self.base_context.result.message.content == "You are not on a hunt yet!"
        ), self.base_context.result.message.content

    @test
    async def hunt_time_when_hunting(self) -> None:
        self.user.nuke_cards("effects")

        started_at = random_date()
        self.user.add_effect("hunting", started_at)

        await self.command(self.cog, self.base_context, option=HuntOptions.time)

        assert (
            self.base_context.result.message.content
            == f"You've started hunting <t:{int(started_at.timestamp())}:R>."
        ), self.base_context.result.message.content

    @test
    async def hunt_end_when_not_hunting(self) -> None:
        self.user.nuke_cards("effects")
        await self.command(self.cog, self.base_context, option=HuntOptions.end)

        assert (
            self.base_context.result.message.content
            == f"You aren't on a hunt yet! Start one with `k!hunt`"
        ), self.base_context.result.message.content

    @test
    async def end_hunt_below_12h(self) -> None:
        self.user.nuke_cards("effects")

        started_at = datetime.now() - timedelta(minutes=10)
        self.user.add_effect("hunting", started_at)

        await self.command(self.cog, self.base_context, option=HuntOptions.end)

        assert (
            self.base_context.result.message.content
            == "You must be at least hunting for twelve hours!"
        ), self.base_context.result.message.content

    @test
    async def end_hunt_correctly(self) -> None:
        self.user.nuke_cards("all")

        started_at = datetime.now() - timedelta(hours=20)
        self.user.add_effect("hunting", started_at)

        await self.command(self.cog, self.base_context, option=HuntOptions.end)

        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert (
            self.base_context.result.message.embeds[0].title == "Hunt returned!"
        ), self.base_context.result.message.embeds[0].title
        assert self.base_context.result.message.embeds[0].description.startswith(
            f"You've started hunting <t:{int(started_at.timestamp())}:R>. You brought back the following items from your hunt: \n\n"
        ), self.base_context.result.message.embeds[0].description
        assert not self.user.has_effect("hunting")[0], self.user.has_effect("hunting")
        assert len(self.user.all_cards) > 0, self.user.all_cards

    @test
    async def start_hunting_when_on_hunt(self) -> None:
        self.user.nuke_cards("effects")

        started_at = random_date()
        self.user.add_effect("hunting", started_at)

        await self.command(self.cog, self.base_context, option=HuntOptions.start)

        assert (
            self.base_context.result.message.content
            == f"You are already on a hunt! Get the results with `k!hunt end`"
        ), self.base_context.result.message.content

    @test
    async def start_hunting_correctly(self) -> None:
        self.user.nuke_cards("effects")

        await self.command(self.cog, self.base_context, option=HuntOptions.start)

        assert (
            self.base_context.result.message.content
            == f"You went hunting! Make sure to claim your rewards at least twelve hours from now, but remember, the longer you hunt, the more you get"
        ), self.base_context.result.message.content
        assert self.user.has_effect("hunting")[0], self.user.has_effect("hunting")[0]
        assert datetime.now() - self.user.effects["hunting"] < timedelta(
            minutes=1
        ), self.user.effects["hunting"]


class Meet(TestingCards):
    def __init__(self):
        super().__init__()
        self.user = User(self.base_author.id)

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
        other = DiscordMember()

        messages = [
            Message(author=DiscordMember(), channel=self.base_context.channel)
            for _ in range(10)
        ]
        messages.extend(
            [Message(author=other, channel=self.base_context.channel)]
        )  # Add argument to recent messages
        self.base_context.channel.history_return = messages
        self.base_channel.history_return = messages

        self.user.add_met_user(other.id)

        await self.command(self.cog, self.base_context, other)

        assert (
            self.base_context.result.message.content
            == f"You already have `{other}` in the list of users you met, {self.base_author.name}"
        ), self.base_context.result.message.content

    @test
    async def meet_correctly(self) -> None:
        other = DiscordMember()

        messages = [
            Message(author=DiscordMember(), channel=self.base_context.channel)
            for _ in range(10)
        ]
        messages.extend(
            [Message(author=other, channel=self.base_context.channel)]
        )  # Add argument to recent messages
        self.base_context.channel.history_return = messages
        self.base_channel.history_return = messages

        await self.command(self.cog, self.base_context, other)

        assert (
            self.base_context.result.message.content
            == f"Done {self.base_author.mention}! Successfully added `{other}` to the list of people you've met"
        ), self.base_context.result.message.content
        assert self.user.has_met(other.id), self.user.met_user


class Discard(TestingCards):

    def __init__(self):
        super().__init__()
        self.user = User(self.base_author.id)

    @test
    async def discord_non_existent_card(self) -> None:
        await self.command(self.cog, self.base_context, "non_existent_card")

        assert (
            self.base_context.result.message.content == "This card does not exist!"
        ), self.base_context.result.message.content

    @test
    async def discard_not_in_posession_card(self) -> None:
        self.user.nuke_cards("all")

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == "You are not in possesion of this card!"
        ), self.base_context.result.message.content

    @test
    async def discard_card_0(self) -> None:
        self.user.nuke_cards("all")
        self.user.add_card(0)

        await self.command(self.cog, self.base_context, "0")

        assert (
            self.base_context.result.message.content == "You cannot discard this card!"
        ), self.base_context.result.message.content

    @test
    async def cancel_discard(self) -> None:
        self.user.nuke_cards("all")
        self.user.add_card(1)

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content == "Successfully cancelled!"
        ), self.base_context.result.message.content

    @test
    async def discard_correctly(self) -> None:
        self.user.nuke_cards("all")
        self.user.add_card(1)

        self.base_context.respond_to_view = self.press_confirm

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == f"Successfully thrown away card No. `1`"
        ), self.base_context.result.message.content
        assert not self.user.has_any_card("1"), self.user.has_any_card("1")


class Cardinfo(TestingCards):

    def __init__(self):
        super().__init__()
        self.user = User(self.base_author.id)

    @test
    async def invalid_card(self) -> None:
        await self.command(self.cog, self.base_context, "invalid")

        assert (
            self.base_context.result.message.content == "Invalid card"
        ), self.base_context.result.message.content

    @test
    async def card_not_owned(self) -> None:
        self.user.nuke_cards("all")

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == "You don't own a copy of this card so you can't view its infos"
        ), self.base_context.result.message.content

    @test
    async def correct_usage(self) -> None:
        self.user.nuke_cards("all")
        self.user.add_card(1)

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
        self.user = User(self.base_author.id)

    @test
    async def invalid_card(self) -> None:
        await self.command(self.cog, self.base_context, "invalid")

        assert (
            self.base_context.result.message.content == "Invalid card"
        ), self.base_context.result.message.content

    @test
    async def card_not_owned(self) -> None:
        self.user.nuke_cards("all")

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == "You don't own any copies of this card which are fake"
        ), self.base_context.result.message.content

    @test
    async def owned_but_not_fake(self) -> None:
        self.user.nuke_cards("all")
        self.user.add_card(1)

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == "You don't own any copies of this card which are fake"
        ), self.base_context.result.message.content

    @test
    async def restricted_slots_fake(self) -> None:
        self.user.nuke_cards("all")
        self.user.add_card(1, fake=True)
        self.user.add_card(1)

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == "The card in your restricted slots is fake"
        ), self.base_context.result.message.content

    @test
    async def free_slots_fake(self) -> None:
        self.user.nuke_cards("all")
        self.user.add_card(1)
        self.user.add_card(1, fake=True)

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == "1 copy of this card in your free slots is fake"
        ), self.base_context.result.message.content

    @test
    async def restricted_slots_and_free_slots_fake(self) -> None:
        self.user.nuke_cards("all")
        self.user.add_card(1, fake=True)
        self.user.add_card(1, fake=True)
        self.user.add_card(1, fake=True)

        await self.command(self.cog, self.base_context, "1")

        assert (
            self.base_context.result.message.content
            == "The card in your restricted slots is fake and 2 copies of this card in your free slots are fake"
        ), self.base_context.result.message.content


# class Use(TestingCards):

#     def __init__(self):
#         super().__init__()
#         self.user = User(self.base_author.id)

#     async def test_command(self) -> None:
#         """Runs all tests of a command"""

#         for method in test.tests(self):
#             await method(self)

#         for subclass in self.__class__.__subclasses__():
#             sub = subclass()
#             for method in test.tests(sub):
#                 await method(sub)

#     @test
#     async def invalid_card(self) -> None:
#         await self.command(self.cog, self.base_context, "invalid", "irrelevant")

#         assert self.base_context.result.message.content == "Invalid card id", self.base_context.result.message.content

#     @test
#     async def not_in_posession(self) -> None:
#         self.user.nuke_cards("all")
#         self.user.add_card(1)

#         await self.command(self.cog, self.base_context, "1", "irrelevant")

#         assert self.base_context.result.message.content == "You are not in possesion of this card!", self.base_context.result.message.content

#     @test
#     async def non_spell(self) -> None:
#         self.user.nuke_cards("all")
#         self.user.add_card(1)

#         await self.command(self.cog, self.base_context, "1", "irrelevant")

#         assert self.base_context.result.message.content == "You can only use spell cards!", self.base_context.result.message.content

#     @test
#     async def defense_spell(self) -> None:
#         self.user.nuke_cards("all")

#         await self.command(self.cog, self.base_context, "1003", "irrelevant")

#         assert self.base_context.result.message.content == "You can only use this card in response to an attack!", self.base_context.result.message.content

# class Card1001(Use):

#     def __init__(self):
#         super().__init__()

#     @test
#     async def has_not_met(self) -> None:
#         self.user.nuke_cards("all")
#         self.user.add_card(1001)
#         other = DiscordMember()
#         self.user.met_user = []

#         await self.command(self.cog, self.base_context, "1001", other)

#         assert self.base_context.result.message.content == "You haven't met this user yet! Use `k!meet <@someone>` if they send a message in a channel to be able to use this card on them", self.base_context.result.message.content

#     @test
#     async def no_permissions(self) -> None:
#         self.user.nuke_cards("all")
#         self.user.add_card(1001)
#         self.base_channel._has_permissions = False
#         other = DiscordMember()
#         self.user.add_met_user(other)

#         await self.command(self.cog, self.base_context, "1001", other)

#         assert self.base_context.result.message.content == f"You can only attack a user in a channel they have read and write permissions to which isn't the case with {other.name}", self.base_context.result.message.content
