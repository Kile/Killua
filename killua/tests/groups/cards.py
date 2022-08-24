from ..types import *
from ..testing import Testing, test
from ...cogs.cards import Cards
from ...static.cards import Card
from ...utils.paginator import Buttons
from ...static.constants import DB, PRICES
from killua.static.enums import Category, HuntOptions, Items, SellOptions

from random import randint
from math import ceil

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

        assert self.base_context.result.message.content == "You don't have any cards yet!", self.base_context.result.message.content

    @test
    async def invalid_page_chosen(self) -> None:
        user = User(self.base_author.id)
        user.add_card(randint(1, 99)) # To prevent no cards error as that check is before this one
        await self.cog.book(self.cog, self.base_context, page=8)

        assert self.base_context.result.message.content == f"Please choose a page number between 1 and {6+ceil(len(user.fs_cards)/18)}", self.base_context.result.message.content

    @test
    async def responds_with_valid_paginator(self) -> None:
        user = User(self.base_author.id)
        user.add_card(randint(1, 99)) # To prevent no cards error as that check is before this one
        self.base_context.timeout_view = True # Make the view instantly time out to prevent long wait
        await self.cog.book(self.cog, self.base_context)

        assert isinstance(self.base_context.result.message.view, Buttons), isinstance(self.base_context.result.message.view, Buttons)

class Sell(TestingCards):

    def __init__(self):
        super().__init__()
        self.user = User(self.base_author.id)

    @test
    async def no_arguments(self) -> None:
        await self.cog.sell(self.cog, self.base_context)
        
        assert self.base_context.result.message, self.base_context.result.message
        assert self.base_context.result.message.content == "You need to specify what exactly to sell", self.base_context.result.message.content

    @test
    async def selling_a_card_not_in_possession(self) -> None:
        await self.cog.sell(self.cog, self.base_context, "5")

        assert self.base_context.result.message.content == "Seems you don't own enough copies of this card. You own 0 copies of this card", self.base_context.result.message.content

    @test
    async def sell_single_valid_card(self) -> None:
        self.base_context.timeout_view = False
            
        self.base_context.respond_to_view = Testing.press_confirm
        card = randint(1, 99)
        self.user.add_card(card)
        await self.cog.sell(self.cog, self.base_context, card=str(card))

        assert self.base_context.result.message.content == f"Successfully sold 1 copy of card {card} for {int(PRICES[Card(card).rank] * 0.1)} Jenny!", self.base_context.result.message.content
        assert self.user.count_card(card, including_fakes=False) == 0, self.user.count_card(card, including_fakes=False)

    @test
    async def sell_single_fake(self) -> None:
        card = randint(1, 99)
        self.user.add_card(card, fake=True)
        await self.cog.sell(self.cog, self.base_context, card=str(card))

        assert self.base_context.result.message.content == "Seems you don't own enough copies of this card. You own 0 copies of this card", self.base_context.result.message.content

    @test
    async def sell_more_cards_than_in_posession(self) -> None:
        card = randint(1, 99)
        self.user.add_card(card)

        await self.cog.sell(self.cog, self.base_context, card=str(card), amount=2)
        assert self.base_context.result.message.content == "Seems you don't own enough copies of this card. You own 1 copy of this card", self.base_context.result.message.content

    @test
    async def selling_multiple_cards(self) -> None:
        self.base_context.timeout_view = False
            
        self.base_context.respond_to_view = Testing.press_confirm
        card = randint(1, 99)
        for _ in range(2):
            self.user.add_card(card)
        await self.cog.sell(self.cog, self.base_context, card=str(card), amount=2)
        
        assert self.base_context.result.message.content == f"Successfully sold 2 copies of card {card} for {int(PRICES[Card(card).rank] * 0.2)} Jenny!", self.base_context.result.message.content
        assert self.user.count_card(card, including_fakes=False) == 0, self.user.count_card(card, including_fakes=False)

    @test
    async def selling_multiple_cards_with_fake(self) -> None:
        card = randint(1, 99)
        self.user.add_card(card)
        self.user.add_card(card, fake=True)

        await self.cog.sell(self.cog, self.base_context, card=str(card), amount=2)
        
        assert self.base_context.result.message.content == "Seems you don't own enough copies of this card. You own 1 copy of this card", self.base_context.result.message.content 

        self.user.remove_card(card, remove_fake=True) and self.user.remove_card(card)

    @test
    async def sell_all_of_category_when_owning_none(self) -> None:
        self.user.add_card(1) # So there won't be the generic "you have no cards" error message
        self.base_context.respond_to_view = self.press_confirm
        await self.cog.sell(self.cog, self.base_context, type=SellOptions.monsters)

        assert self.base_context.result.message.content == "You don't have any cards of that type to sell!", self.base_context.result.message.content

    @test
    async def sell_all_of_category(self) -> None:
        self.user.add_card(572)
        self.user.add_card(697)

        self.base_context.respond_to_view = self.press_confirm
        await self.cog.sell(self.cog, self.base_context, type=SellOptions.monsters)

        assert self.base_context.result.message.content == f"You sold all your monsters for {int((PRICES[Card(572).rank] + PRICES[Card(697).rank]) * 0.1)} Jenny!", self.base_context.result.message.content
        assert self.user.count_card(572, including_fakes=False) == 0 and self.user.count_card(697, including_fakes=False) == 0, self.user.count_card(572, including_fakes=False) == 0 and self.user.count_card(697, including_fakes=False) == 0

    @test
    async def sell_all_of_category_with_fake(self) -> None:
        self.user.add_card(572)
        self.user.add_card(697, fake=True)

        self.base_context.respond_to_view = self.press_confirm
        await self.cog.sell(self.cog, self.base_context, type=SellOptions.monsters)

        assert self.base_context.result.message.content == f"You sold all your monsters for {int(PRICES[Card(572).rank] * 0.1)} Jenny!", self.base_context.result.message.content
        assert self.user.count_card(572, including_fakes=False) == 0 and self.user.count_card(697, including_fakes=True) == 1, self.user.count_card(572, including_fakes=False) == 0 and self.user.count_card(697, including_fakes=True) == 1