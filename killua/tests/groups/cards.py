from ..types import *
from ..testing import Testing
from ...cogs.cards import Cards
from ...static.cards import Card
from ...utils.paginator import Buttons
from ...static.constants import DB, PRICES
from killua.static.enums import Category, HuntOptions, Items, SellOptions

from random import randint
from math import ceil
from asyncio import wait_for

class TestingCards(Testing):

    def __init__(self):
        super().__init__(cog=Cards)

    async def book(self):

        # Test if user has no cards
        try:
            await self.cog.book(self.cog, self.base_context)
            if self.base_context.result.message.content == "You don't have any cards yet!":
                self.result.completed_test(self.cog.book, Result.passed)
            else:
                self.result.completed_test(self.cog.book, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.book, Result.errored, ResultData(error=e))

        # Test if the page chosen is invalid
        try:
            user = User(self.base_author.id)
            user.add_card(randint(1, 99)) # To prevent no cards error
            await self.cog.book(self.cog, self.base_context, page=8)
            if self.base_context.result.message.content == f"Please choose a page number between 1 and {6+ceil(len(user.fs_cards)/18)}":
                self.result.completed_test(self.book, Result.passed)
            else:
                self.result.completed_test(self.cog.book, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.book, Result.errored, ResultData(error=e))

        # Test it responds with a valid paginator
        try:
            user = User(self.base_author.id)
            user.add_card(randint(1, 99)) # To prevent no cards error
            self.base_context.timeout_view = True # Make the view instantly time out
            await self.cog.book(self.cog, self.base_context)
            if isinstance(self.base_context.result.message.view, Buttons):
                self.result.completed_test(self.cog.book, Result.passed)
            else:
                self.result.completed_test(self.cog.book, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.book, Result.errored, ResultData(error=e))

    async def sell(self):
        user = User(self.base_author.id)

        # Testing no arguments
        try:
            await self.cog.sell(self.cog, self.base_context)
            if self.base_context.result.message and \
                self.base_context.result.message.content == "You need to specify what exactly to sell":
                self.result.completed_test(self.cog.sell, Result.passed)
            else:
                self.result.completed_test(self.cog.sell, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.sell, Result.errored, ResultData(error=e))

        # Testing selling a card a user doesn't have
        try:
            await self.cog.sell(self.cog, self.base_context, "5")
            if self.base_context.result.message.content == "Seems you don't own enough copies of this card. You own 0 copies of this card":
                self.result.completed_test(self.cog.sell, Result.passed)
            else:
                self.result.completed_test(self.cog.sell, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.sell, Result.errored, ResultData(error=e))

        # Testing selling a single valid card
        try:
            self.base_context.timeout_view = False
            
            self.base_context.respond_to_view = Testing.press_confirm
            card = randint(1, 99)
            user.add_card(card)
            await wait_for(self.cog.sell(self.cog, self.base_context, card=str(card)), timeout=5)
            if self.base_context.result.message.content == f"Successfully sold 1 copy of card {card} for {int(PRICES[Card(card).rank] * 0.1)} Jenny!" and \
                User(self.base_author.id).count_card(card, including_fakes=False) == 0:
                self.result.completed_test(self.cog.sell, Result.passed)
            else:
                self.result.completed_test(self.cog.sell, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.sell, Result.errored, ResultData(error=e))

        # Testing selling a fake
        try:
            card = randint(1, 99)
            user.add_card(card, fake=True)
            await wait_for(self.cog.sell(self.cog, self.base_context, card=str(card)), timeout=5)
            if self.base_context.result.message.content == "Seems you don't own enough copies of this card. You own 0 copies of this card":
                self.result.completed_test(self.cog.sell, Result.passed)
            else:
                self.result.completed_test(self.cog.sell, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.sell, Result.errored, ResultData(error=e))

        # Testing attempting to sell more cards than in possession
        try:
            card = randint(1, 99)
            user.add_card(card)

            await wait_for(self.cog.sell(self.cog, self.base_context, card=str(card), amount=2), timeout=5)
            if self.base_context.result.message.content == "Seems you don't own enough copies of this card. You own 1 copy of this card":
                self.result.completed_test(self.cog.sell, Result.passed)
            else:
                self.result.completed_test(self.cog.sell, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.sell, Result.errored, ResultData(error=e))
        user.remove_card(card)

        # Testing selling multiple cards
        try:
            self.base_context.timeout_view = False
            
            self.base_context.respond_to_view = Testing.press_confirm
            card = randint(1, 99)
            for _ in range(2):
                user.add_card(card)
            await wait_for(self.cog.sell(self.cog, self.base_context, card=str(card), amount=2), timeout=5)
            if self.base_context.result.message.content == f"Successfully sold 2 copies of card {card} for {int(PRICES[Card(card).rank] * 0.2)} Jenny!" and \
                user.count_card(card, including_fakes=False) == 0:
                self.result.completed_test(self.cog.sell, Result.passed)
            else:
                self.result.completed_test(self.cog.sell, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.sell, Result.errored, ResultData(error=e))

        # Testing selling multiple cards with a fake
        try:
            card = randint(1, 99)
            user.add_card(card)
            user.add_card(card, fake=True)

            await wait_for(self.cog.sell(self.cog, self.base_context, card=str(card), amount=2), timeout=5)
            if self.base_context.result.message.content == "Seems you don't own enough copies of this card. You own 1 copy of this card":
                self.result.completed_test(self.cog.sell, Result.passed)
            else:
                self.result.completed_test(self.cog.sell, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.sell, Result.errored, ResultData(error=e))

        user.remove_card(card, remove_fake=True) and user.remove_card(card)

        # Testing selling all cards of a category when ownung none of them
        try:
            user.add_card(1) # So there won't be the generic "you have no cards" error message
            await wait_for(self.cog.sell(self.cog, self.base_context, type=SellOptions.monsters), timeout=5)
            if self.base_context.result.message.content == "You don't have any cards of that type to sell!":
                self.result.completed_test(self.cog.sell, Result.passed)
            else:
                self.result.completed_test(self.cog.sell, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.sell, Result.errored, ResultData(error=e))

        # Testing selling all cards of a category
        try:
            user.add_card(572)
            user.add_card(697)

            await wait_for(self.cog.sell(self.cog, self.base_context, type=SellOptions.monsters), timeout=5)
            if self.base_context.result.message.content == f"You sold all your monsters for {int((PRICES[Card(572).rank] + PRICES[Card(697).rank]) * 0.1)} Jenny!" and \
                user.count_card(572, including_fakes=False) == 0 and user.count_card(697, including_fakes=False) == 0:
                self.result.completed_test(self.cog.sell, Result.passed)
            else:
                self.result.completed_test(self.cog.sell, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.sell, Result.errored, ResultData(error=e))

        # Testing selling all cards of a category with a fake
        try:
            user.add_card(572)
            user.add_card(697, fake=True)

            await wait_for(self.cog.sell(self.cog, self.base_context, type=SellOptions.monsters), timeout=5)
            if self.base_context.result.message.content == f"You sold all your monsters for {int(PRICES[Card(572).rank] * 0.1)} Jenny!" and \
                user.count_card(572, including_fakes=False) == 0 and user.count_card(697, including_fakes=True) == 1:
                self.result.completed_test(self.cog.sell, Result.passed)
            else:
                self.result.completed_test(self.cog.sell, Result.failed, self.base_context.result)
        except Exception as e:
            self.result.completed_test(self.cog.sell, Result.errored, ResultData(error=e))
        user.remove_card(697, remove_fake=True)