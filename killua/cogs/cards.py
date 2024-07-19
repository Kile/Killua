import discord
import math
import random
from discord.ext import commands
from datetime import datetime, timedelta

from typing import (
    Union,
    List,
    Optional,
    Tuple,
    Optional,
    Dict,
    Literal,
    Any,
    cast,
    Type,
)

from killua.bot import BaseBot
from killua.utils.checks import check
from killua.utils.paginator import Paginator
from killua.utils.classes import User, CardNotFound, CheckFailure, Book, NoMatches
from killua.static.enums import Category, SellOptions
from killua.utils.interactions import ConfirmButton
from killua.static.cards import Card, CardNotFound, IndividualCard
from killua.static.constants import (
    ALLOWED_AMOUNT_MULTIPLE,
    FREE_SLOTS,
    DEF_SPELLS,
    VIEW_DEF_SPELLS,
    PRICES,
    BOOK_PAGES,
    LOOTBOXES,
    PRICE_INCREASE_FOR_SPELL,
    DB,
    BOOSTERS,
)


class Cards(commands.GroupCog, group_name="cards"):

    def __init__(self, client: BaseBot):
        self.client = client
        self.cardname_cache: Dict[int, Tuple[str, str]] = {}
        self._init_menus()

    def _init_menus(self) -> None:
        menus = []
        menus.append(
            discord.app_commands.ContextMenu(
                name="meet",
                callback=self.client.callback_from_command(self.meet, message=False),
                allowed_installs=discord.app_commands.AppInstallationType(guild=True),
            )
        )

        for menu in menus:
            try:
                self.client.tree.add_command(menu)
            except discord.app_commands.errors.CommandAlreadyRegistered:
                pass  # Ignoring this

    async def cog_load(self) -> None:
        self.reward_cache = {
            "item": [
                x["_id"]
                async for x in DB.items.find(
                    {"type": "normal", "rank": {"$in": ["A", "B", "C"]}}
                )
            ],
            "spell": [
                x["_id"]
                async for x in DB.items.find(
                    {"type": "spell", "rank": {"$in": ["B", "C"]}}
                )
            ],
            "monster": {
                "E": [
                    x["_id"]
                    async for x in DB.items.find(
                        {"type": "monster", "rank": {"$in": ["E", "G", "H"]}}
                    )
                ],
                "D": [
                    x["_id"]
                    async for x in DB.items.find(
                        {"type": "monster", "rank": {"$in": ["D", "E", "F"]}}
                    )
                ],
                "C": [
                    x["_id"]
                    async for x in DB.items.find(
                        {"type": "monster", "rank": {"$in": ["C", "D", "E"]}}
                    )
                ],
            },
        }

    async def all_cards_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[discord.app_commands.Choice[str]]:
        """Autocomplete for all cards"""
        if not self.cardname_cache:
            async for card in DB.items.find({}):
                self.cardname_cache[card["_id"]] = card["name"], card["type"]

        name_cards = [
            (x[0], self.cardname_cache[x[0]][0])
            for x in (await User.new(interaction.user.id)).all_cards
            if self.cardname_cache[x[0]][0].lower().startswith(current.lower())
        ]
        id_cards = [
            (x[0], self.cardname_cache[x[0]][0])
            for x in (await User.new(interaction.user.id)).all_cards
            if str(x[0]).startswith(current)
        ]
        name_cards = list(dict.fromkeys(name_cards))
        id_cards = list(
            dict.fromkeys(id_cards)
        )  # removing all duplicates from the list

        if current == "":  # No ids AND names if the user hasn"t typed anything yet
            return [
                discord.app_commands.Choice(name=x[1], value=str(x[0]))
                for x in name_cards
            ][0:25]
        return [
            *[discord.app_commands.Choice(name=n, value=str(i)) for i, n in name_cards],
            *[
                discord.app_commands.Choice(name=str(i), value=str(i))
                for i, _ in id_cards
            ],
        ][0:25]

    def _get_single_reward(self, score: int) -> Tuple[int, int]:
        if score == 1:
            if random.randint(1, 10) < 5:
                return 1, random.choice(self.reward_cache["item"])
            else:
                return 1, random.choice(self.reward_cache["spell"])

        if score < 3000 / 10000:
            rarities = "E"
        elif score < 7000 / 10000:
            rarities = "D"
        else:
            rarities = "C"

        amount = random.randint(1, math.ceil(score * 10))
        card = random.choice(self.reward_cache["monster"][rarities])
        return amount, card

    def _construct_rewards(self, score: int) -> List[Tuple[int, int]]:
        # reward_score will be minutes/10080 which equals a week. Max rewards will get returned once a user has hunted for a week
        rewards: List[Tuple[int, int]] = []

        if score >= 1:
            rewards.append(self._get_single_reward(1))
            score = 0.7

        for _ in range(math.ceil(random.randint(1, math.ceil(score * 10)) / 1.6)):
            r = self._get_single_reward(score)
            rewards.append(r)

        final_rewards: List[Tuple[int, int]] = []
        for reward in rewards:
            # This avoid duplicates e.g. 4xPaladins Necklace, 2xPaladins Necklace => 6xPaladins Necklace
            if reward[1] in (l := [y for _, y in final_rewards]):
                index = l.index(reward[1])
                final_rewards[index] = (
                    final_rewards[index][0] + reward[0],
                    final_rewards[index][1],
                )
            else:
                final_rewards.append(reward)
        return final_rewards

    async def _format_rewards(
        self, rewards: List[Tuple[int, int]], user: User
    ) -> Tuple[List[list], List[str], bool]:
        """Formats the generated rewards for further use"""
        formatted_rewards: List[List[int, Dict[str, bool]]] = []
        formatted_text: List[str] = []

        maxed = False
        for pos, reward in enumerate(rewards):
            for i in range(reward[0]):
                if len(
                    [
                        *user.fs_cards,
                        *[
                            x
                            for x in rewards
                            if x[1] > 99 and not user.has_rs_card(x[0])
                        ],
                    ]
                ) >= 40 and (
                    reward[1] > 99
                    or (not user.has_rs_card(reward[1]) and reward[1] < 100)
                ):
                    # return formatted_rewards, formatted_text, True # if the free slots are full the process stops
                    maxed = (
                        pos,
                        i,
                    )  # Returning the exact position where the cards are too much
                else:
                    formatted_rewards.append(
                        [reward[1], {"fake": False, "clone": False}]
                    )
            card = await Card.new(reward[1])
            if maxed:
                if (
                    not maxed[1] == 0
                ):  # If there isn"t 0 of that card that will be added
                    formatted_text.append(f"{maxed[1]}x **{card.name}**{card.emoji}")
            else:
                formatted_text.append(f"{reward[0]}x **{card.name}**{card.emoji}")

        return formatted_rewards, formatted_text, maxed

    @check(3)
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @commands.hybrid_command(
        extras={"category": Category.CARDS, "id": 13}, usage="book <page(optional)>"
    )
    @discord.app_commands.describe(page="The page of the book to see")
    async def book(self, ctx: commands.Context, page: int = 1):
        """Allows you to take a look at your cards"""
        user = await User.new(ctx.author.id)

        if len(user.all_cards) == 0:
            return await ctx.send("You don't have any cards yet!")

        if page:
            if page > 7 + math.ceil(len(user.fs_cards) / 18) or page < 1:
                return await ctx.send(
                    f"Please choose a page number between 1 and {6+math.ceil(len(user.fs_cards)/18)}"
                )

        async def make_embed(page, *_) -> Tuple[discord.Embed, discord.File]:
            return await Book(
                self.client.session, self.client.api_url(to_fetch=True)
            ).create(ctx.author, page, self.client)

        return await Paginator(
            ctx,
            page=page,
            func=make_embed,
            max_pages=6 + math.ceil(len(user.fs_cards) / 18),
            has_file=True,
        ).start()

    async def _gen_to_be_sold(self, user: User, sell_opt: SellOptions) -> List[Tuple[int, Any]]:
        """
        Decides which cards to be sold based on the sell option
        """
        to_be_sold = []
        if sell_opt == SellOptions.all:
            to_be_sold = [
                x for x in user.fs_cards if not x[1]["clone"] and not x[1]["fake"]
            ]
        elif sell_opt == SellOptions.spells:
            to_be_sold = [
                x
                for x in user.fs_cards
                if (await Card.new(x[0])).type == "spell"
                and not x[1]["clone"]
                and not x[1]["fake"]
            ]
        elif sell_opt == SellOptions.monsters:
            to_be_sold = [
                x
                for x in user.fs_cards
                if (await Card.new(x[0])).type == "monster"
                and not x[1]["clone"]
                and not x[1]["fake"]
            ]
        return to_be_sold
    
    async def _find_to_be_gained(self, to_be_sold: List[Tuple[int, Any]], entitled_to_double: bool) -> int:
        """Finds the money to be gained from selling the cards"""
        to_be_gained = 0
        for c, _ in to_be_sold:
            _price = PRICES[(await Card.new(c)).rank] + (
                PRICE_INCREASE_FOR_SPELL
                if (await Card.new(c)).type == "spell"
                else 0
            )
            j = int(_price / 10)
            if entitled_to_double:
                j *= 2
            to_be_gained += j
        return to_be_gained
    
    async def _sell_confirm_view(self, ctx: commands.Context, to_be_gained: int, selling_what: str) -> bool:
        """
        Asks the user if they want to sell the cards. 
        Returns True if the user wants to sell the cards, False if they don't
        """
        view = ConfirmButton(ctx.author.id, timeout=80)
        msg = await ctx.send(
            f"You will receive {to_be_gained} Jenny for selling {selling_what} cards, do you want to proceed?",
            view=view,
        )
        await view.wait()
        await view.disable(msg)

        if not view.value:
            if view.timed_out:
                await ctx.send("Timed out!")
            else:
                await ctx.send("Successfully canceled!")
            return False
        return True

    async def _sell_bulk(self, ctx: commands.Context, user: User, sell_opt: SellOptions) -> None:
        """
        Sells all cards based on the sell option
        """
        to_be_sold = await self._gen_to_be_sold(user, sell_opt)
        to_be_gained = await self._find_to_be_gained(to_be_sold, user.is_entitled_to_double_jenny)

        if to_be_gained == 0:
            return await ctx.send(
                "You don't have any cards of that type to sell!", ephemeral=True
            )

        confirmed = await self._sell_confirm_view(ctx, to_be_gained, "all " + (sell_opt.name if not sell_opt.name == 'all' else 'free slots') + " cards")
        if not confirmed:
            return
        
        await user.bulk_remove(to_be_sold)
        await user.add_jenny(to_be_gained)
        await ctx.send(
            f"You sold all your {sell_opt.name if not sell_opt.name == 'all' else 'free slots cards'} for {to_be_gained} Jenny!"
        )

    async def _sell_single(self, ctx: commands.Context, user: User, card: Card, amount: int) -> None:
        """
        Sells a single card (X times)
        """
        in_possesion = user.count_card(card.id, including_fakes=False)

        if in_possesion < amount:
            return await ctx.send(
                f"Seems you don't own enough copies of this card. You own {in_possesion} cop{'y' if in_possesion == 1 else 'ies'} of this card"
            )

        if card == 0:
            return await ctx.send("You cannot sell this card!")

        _price = PRICES[card.rank] + (
            PRICE_INCREASE_FOR_SPELL if card.type == "spell" else 0
        )
        jenny = int((_price * amount) / 10)
        if user.is_entitled_to_double_jenny:
            jenny *= 2

        confirmed = await self._sell_confirm_view(ctx, jenny, f"{amount} cop{'y' if amount == 1 else 'ies'} of card {card.id}")
        if not confirmed:
            return

        for _ in range(amount):
            await user.remove_card(card.id, False)
        await user.add_jenny(jenny)
        await ctx.send(
            f"Successfully sold {amount} cop{'y' if amount == 1 else 'ies'} of card {card.id} for {jenny} Jenny!"
        )

    @check(2)
    @commands.hybrid_command(
        extras={"category": Category.CARDS, "id": 14},
        usage="sell <card_id> <amount(optional)>",
    )
    @discord.app_commands.describe(
        card="The card to sell",
        sell_opt="The type of card to bulk sell",
        amount="The amount of the specified card to sell",
    )
    @discord.app_commands.autocomplete(card=all_cards_autocomplete)
    async def sell(
        self,
        ctx: commands.Context,
        card: str = None,
        amount: int = 1,
        sell_opt: Literal["all", "spells", "monsters"] = None,
    ):
        """Sell any amount of cards you own"""
        if sell_opt:
            sell_opt: SellOptions = getattr(
                SellOptions, type
            )  # I cannot use the enum directly due to a library limitation with enums as annotations in message commands

        user = await User.new(ctx.author.id)

        if not sell_opt and not card:
            return await ctx.send(
                "You need to specify what exactly to sell", ephemeral=True
            )

        if (
            sell_opt
        ):  # always prefers if a type argument was given. However if both a type argument and card argument was given,
            # both will be attempted to be executed.
            await self._sell_bulk(ctx, user, sell_opt)

        if not card:
            return

        if amount < 1:
            amount = 1
        if len(user.all_cards) == 0:
            return await ctx.send("You don't have any cards yet!")
        try:
            card: Card = await Card.new(card)
        except CardNotFound:
            return await ctx.send(
                f"A card with the id `{card}` does not exist",
                allowed_mentions=discord.AllowedMentions.none(),
            )

        await self._sell_single(ctx, user, card, amount)

    async def swap_cards_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[discord.app_commands.Choice[str]]:
        """Autocomplete for the swap command"""

        if not self.cardname_cache:
            async for card in DB.items.find({}):
                self.cardname_cache[card["_id"]] = card["name"], card["type"]

        user = await User.new(interaction.user.id)
        name_cards = [
            (x[0], self.cardname_cache[x[0]][0])
            for x in user.all_cards
            if self.cardname_cache[x[0]][0].lower().startswith(current.lower())
        ]
        id_cards = [
            (x[0], self.cardname_cache[x[0]][0])
            for x in user.all_cards
            if str(x[0]).startswith(current)
        ]

        name_duplicates = []
        id_duplicates = []
        for id, name in name_cards:
            if user.can_swap(id) and (id, name) not in name_duplicates:
                name_duplicates.append((id, name))

        for id, name in id_cards:
            if user.can_swap(id) and (id, name) not in id_duplicates:
                id_duplicates.append((id, name))

        if current == "":  # No ids AND names if the user hasn"t typed anything yet
            return [
                discord.app_commands.Choice(name=x[1], value=str(x[0]))
                for x in name_duplicates
            ]
        return [
            *[
                discord.app_commands.Choice(name=n, value=str(i))
                for i, n in name_duplicates
            ],
            *[
                discord.app_commands.Choice(name=str(i), value=str(i))
                for i, _ in id_duplicates
            ],
        ]

    @check(20)
    @commands.hybrid_command(
        extras={"category": Category.CARDS, "id": 15}, usage="swap <card_id>"
    )
    @discord.app_commands.describe(card="The card to swap out")
    @discord.app_commands.autocomplete(card=swap_cards_autocomplete)
    async def swap(self, ctx: commands.Context, card: str):
        """Allows you to swap cards from your free slots with the restricted slots and the other way around"""

        user = await User.new(ctx.author.id)
        if len(user.all_cards) == 0:
            return await ctx.send("You don't have any cards yet!")
        try:
            card: Card = await Card.new(card)
        except CardNotFound:
            return await ctx.send("Please use a valid card number!")

        if card.id == 0:
            return await ctx.send("You cannot swap out card No. 0!")

        sw = await user.swap(card.id)

        if sw is False:
            return await ctx.send(
                f"You don't own a fake and real copy of card `{card.name}` you can swap out!"
            )

        await ctx.send(f"Successfully swapped out card {card.name}")

    @check()
    @commands.hybrid_command(
        extras={"category": Category.CARDS, "id": 16}, usage="hunt <end/time(optional)>"
    )
    @discord.app_commands.describe(option="What to do with your hunt")
    async def hunt(
        self, ctx: commands.Context, option: Literal["end", "time", "start"] = "start"
    ):
        """Go on a hunt! The longer you are on the hunt, the better the rewards!"""

        user = await User.new(ctx.author.id)
        value: datetime  # Typehint since type is Any
        has_effect, value = user.has_effect("hunting")

        if option == "time":
            if not has_effect:
                return await ctx.send("You are not on a hunt yet!")

            return await ctx.send(
                f"You've started hunting <t:{int(value.timestamp())}:R>."
            )

        elif option == "end" and has_effect is True:
            difference: timedelta = datetime.now() - value
            if (
                int(difference.seconds / 60 / 60 + difference.days * 24 * 60 * 60) < 12
            ):  # I don't think timedelta has an hours or minutes property :c
                return await ctx.send("You must be at least hunting for twelve hours!")

            if ctx.interaction:
                await ctx.interaction.response.defer()  # The following part may take longer than 3 secons

            minutes = int(difference.seconds / 60 + difference.days * 24 * 60)
            score = (
                minutes / 10080
            )  # There are 10080 minutes in a week if I'm not completely wrong

            rewards = self._construct_rewards(score)
            formatted_rewards, formatted_text, hit_limit = await self._format_rewards(
                rewards, user
            )

            jenny = 0
            if hit_limit:
                c, n = hit_limit
                for pos, card in enumerate(rewards):
                    if pos == c:
                        jenny += PRICES[(await Card.new(card[1])).rank] * (card[0] - n)
                    elif pos >= c:
                        jenny += PRICES[(await Card.new(card[1])).rank] * card[0]

            text = f"You've started hunting <t:{int(value.timestamp())}:R>. You brought back the following items from your hunt: \n\n"

            if hit_limit:
                text += f":warning: Your free slot limit has been reached! Make sure you free it up before hunting again. The excess cards have been automatically sold bringing you `{jenny}` Jenny\n\n"

            embed = discord.Embed.from_dict(
                {
                    "title": "Hunt returned!",
                    "description": text + "\n".join(formatted_text),
                    "color": 0x3E4A78,
                }
            )
            await user.remove_effect("hunting")
            await user.add_multi(*formatted_rewards)
            await user.add_jenny(jenny)
            return await ctx.send(embed=embed)

        elif option == "end" and not has_effect:
            return await ctx.send(
                "You aren't on a hunt yet! Start one with `/cards hunt`",
                allowed_mentions=discord.AllowedMentions.none(),
            )

        if has_effect:
            return await ctx.send(
                "You are already on a hunt! Get the results with `/cards hunt end`",
                allowed_mentions=discord.AllowedMentions.none(),
            )
        await user.add_effect("hunting", datetime.now())
        await ctx.send(
            "You went hunting! Make sure to claim your rewards at least twelve hours from now, but remember, the longer you hunt, the more you get"
        )

    @check(120)
    @discord.app_commands.describe(
        user="The user to meet. Must have sent a message recently."
    )
    @commands.hybrid_command(
        aliases=["approach"],
        extras={"category": Category.CARDS, "id": 17},
        usage="meet <user>",
    )
    async def meet(self, ctx: commands.Context, user: discord.Member):
        """Meet a user who has recently sent a message in this channel to enable certain effects"""
        if hasattr(ctx, "invoked_by_context_menu"):
            user = await self.client.find_user(ctx, user)

        author = await User.new(ctx.author.id)
        past_users = []
        if user.bot:
            return await ctx.send(
                "You can't interact with bots with this command", ephemeral=True
            )
        async for message in ctx.channel.history(limit=20):
            if message.author.id not in past_users:
                past_users.append(message.author.id)

        if not user.id in past_users:
            return await ctx.send(
                "The user you tried to approach has not send a message in this channel recently",
                ephemeral=True,
            )

        if user.id in author.met_user:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass
            return await ctx.send(
                f"You already have `{user}` in the list of users you met, {ctx.author.name}",
                delete_after=2,
                allowed_mentions=discord.AllowedMentions.none(),
                ephemeral=True,
            )

        await author.add_met_user(user.id)
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
        return await ctx.send(
            f"Done {ctx.author.mention}! Successfully added `{user}` to the list of people you've met",
            delete_after=5,
            allowed_mentions=discord.AllowedMentions.none(),
            ephemeral=hasattr(ctx, "invoked_by_context_menu"),
        )

    @check()
    @commands.hybrid_command(
        extras={"category": Category.CARDS, "id": 18}, usage="discard <card_id>"
    )
    @discord.app_commands.describe(card="The card to discard")
    @discord.app_commands.autocomplete(card=all_cards_autocomplete)
    async def discard(self, ctx: commands.Context, card: str):
        """Discard a card you want to get rid of with this command. Make sure it's in the free slots"""

        user = await User.new(ctx.author.id)
        try:
            card: Card = await Card.new(card)
        except CardNotFound:
            return await ctx.send("This card does not exist!")

        if not user.has_any_card(card.id):
            return await ctx.send("You are not in possesion of this card!")

        if card.id == 0:
            return await ctx.send("You cannot discard this card!")

        view = ConfirmButton(ctx.author.id, timeout=20)
        msg = await ctx.send(
            f"Do you really want to throw this card away? (if you want to throw a fake aware, make sure it's in the free slots (unless it's the only copy you own. You can switch cards between free and restricted slots with `{(await self.client.command_prefix(self.client, ctx.message))[2]}swap <card_id>`)",
            view=view,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await view.wait()
        await view.disable(msg)

        if not view.value:
            if view.timed_out:
                return await ctx.send("Timed out!")
            else:
                return await ctx.send("Successfully cancelled!")

        try:
            await user.remove_card(card.id, remove_fake=True, restricted_slot=False)
            # essentially here it first looks for fakes in your free slots and tried to remove them. If it doesn't find any fakes in the free slots, it will remove the first match of the card it finds in free or restricted slots
        except NoMatches:
            await user.remove_card(card.id)
        await ctx.send(f"Successfully thrown away card No. `{card.id}`")

    @check()
    @commands.hybrid_command(
        aliases=["read"],
        extras={"category": Category.CARDS, "id": 19},
        usage="cardinfo <card_id>",
    )
    @discord.app_commands.describe(card="The card to get infos about")
    @discord.app_commands.autocomplete(card=all_cards_autocomplete)
    async def cardinfo(self, ctx: commands.Context, card: str):
        """Check card info out about any card you own"""
        try:
            c = await Card.new(card)
        except CardNotFound:
            return await ctx.send("Invalid card")

        author = await User.new(ctx.author.id)
        if not author.has_any_card(c.id):
            return await ctx.send(
                "You don't own a copy of this card so you can't view its infos"
            )

        embed, file = await c._get_analysis_embed(c.id, self.client)
        if c.type == "spell" and c.id not in [*DEF_SPELLS, *VIEW_DEF_SPELLS]:
            card_class: IndividualCard = next(
                (_c for _c in Card.__subclasses__() if _c.__name__ == f"Card{c.id}"),
                None,
            )
            usage = (
                f"`{(await self.client.command_prefix(self.client, ctx.message))[2]}use {card} "
                + " ".join(
                    [
                        f"[{k}: {v.__name__}]"
                        for k, v in card_class.exec.__annotations__.items()
                        if not str(k) == "return"
                    ]
                )
                + "`"
            )
            embed.add_field(name="Usage", value=usage, inline=False)

        await ctx.send(embed=embed, file=file)

    @check()
    @commands.hybrid_command(
        name="check",
        extras={"category": Category.CARDS, "id": 20},
        usage="check <card_id>",
    )
    @discord.app_commands.describe(card="The card to see how many fakes you own of it")
    @discord.app_commands.autocomplete(card=all_cards_autocomplete)
    async def _check(self, ctx: commands.Context, card: str):
        """Lets you see how many copies of the specified card are fakes"""
        try:
            card: Card = await Card.new(card)
        except CardNotFound:
            return await ctx.send("Invalid card")

        author = await User.new(ctx.author.id)

        if not author.has_any_card(card.id, only_allow_fakes=True):
            return await ctx.send(
                "You don't own any copies of this card which are fake"
            )

        text = ""

        if (
            len(
                [x for x in author.rs_cards if x[1]["fake"] is True and x[0] == card.id]
            )
            > 0
        ):
            text += f"The card in your restricted slots is fake"

        if (
            fs := len(
                [x for x in author.fs_cards if x[1]["fake"] is True and x[0] == card.id]
            )
        ) > 0:
            text += (
                (" and " if len(text) > 0 else "")
                + f"{fs} cop{'ies' if fs > 1 else 'y'} of this card in your free slots {'are' if fs > 1 else 'is'} fake"
            )

        await ctx.send(text)

    async def _member_converter(
        self, ctx: commands.Context, data: str
    ) -> Optional[discord.Member]:
        """Converts the data to a discord.Member if possible"""
        try:
            return await commands.MemberConverter().convert(ctx, data)
        except (commands.BadArgument, TypeError):
            return None

    async def _use_converter(
        self, ctx: commands.Context, args: Union[int, str, None]
    ) -> Union[discord.Member, int, str, None]:
        """Converts the args to a discord.Member, int or str if possible"""
        if not args:
            return None
        elif isinstance(args, int):
            return args
        elif m := await self._member_converter(ctx, args):
            return m
        elif args.isdigit():
            return int(args)
        else:
            return args

    async def _use_check(
        self,
        ctx: commands.Context,
        card: str,
        args: Optional[Union[discord.Member, int, str]],
        add_args: Optional[int],
    ) -> Card:
        """Makes sure the inputs are valid if they exist"""
        try:
            card: Card = await Card.new(card)
        except CardNotFound:
            raise CheckFailure("Invalid card id")

        if not card.id in [
            x[0] for x in (await User.new(ctx.author.id)).fs_cards
        ] and not card.id in [1036]:
            raise CheckFailure("You are not in possesion of this card!")

        if card.type != "spell":
            raise CheckFailure("You can only use spell cards!")

        if card.id in [*DEF_SPELLS, *VIEW_DEF_SPELLS]:
            raise CheckFailure("You can only use this card in response to an attack!")

        if args:
            if isinstance(args, discord.Member):
                if args.id == ctx.author.id:
                    raise CheckFailure("You can't use spell cards on yourself")
                elif args.bot:
                    raise CheckFailure("You can't use spell cards on bots")

            if isinstance(args, int) and int(args) < 1:
                    raise CheckFailure("You can't use an integer less than 1")

        if add_args and add_args < 1:
            raise CheckFailure("You can't use an integer less than 1")

        return card

    async def _use_core(self, ctx: commands.Context, card: Card, *args) -> None:
        """This passes the execution to the right class"""
        card_class: Type[IndividualCard] = next(
            (c for c in Card.__subclasses__() if c.__name__ == f"Card{card.id}")
        )

        l: List[Dict[str, Any]] = []
        for p, (k, v) in enumerate(
            [
                x
                for x in card_class.exec.__annotations__.items()
                if not str(x[0]) == "return"
            ]
        ):
            if len(args) > p and isinstance(args[p], v):
                l.append({k: args[p]})
            else:
                l.append(None)

        if None in l:
            return await ctx.send(
                f"Invalid arguments provided! Usage: `{(await self.client.command_prefix(self.client, ctx.message))[2]}use {card.id} "
                + " ".join(
                    [
                        f"[{k}: {v.__name__}]"
                        for k, v in card_class.exec.__annotations__.items()
                        if not str(k) == "return"
                    ]
                )
                + "`",
                allowed_mentions=discord.AllowedMentions.none(),
            )
        kwargs = {k: v for d in l for k, v in d.items()}
        try:
            await cast(
                IndividualCard, await card_class._new(name_or_id=str(card.id), ctx=ctx)
            ).exec(**kwargs)
            # It should be able to infert the type but for some reason it is not able to do so
        except CheckFailure as e:
            await ctx.send(e.message, allowed_mentions=discord.AllowedMentions.none())

    async def use_cards_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[discord.app_commands.Choice[str]]:
        if not self.cardname_cache:
            async for card in DB.items.find({}):
                self.cardname_cache[card["_id"]] = card["name"], card["type"]

        name_cards = [
            (x[0], self.cardname_cache[x[0]][0])
            for x in (await User.new(interaction.user.id)).all_cards
            if self.cardname_cache[x[0]][0].lower().startswith(current.lower())
            and self.cardname_cache[x[0]][1] == "spell"
        ]
        id_cards = [
            (x[0], self.cardname_cache[x[0]][0])
            for x in (await User.new(interaction.user.id)).all_cards
            if str(x[0]).startswith(current) and self.cardname_cache[x[0]][1] == "spell"
        ]
        name_cards = list(dict.fromkeys(name_cards))
        id_cards = list(
            dict.fromkeys(id_cards)
        )  # removing all duplicates from the list

        if current == "":  # No ids AND names if the user hasn"t typed anything yet
            res = [
                discord.app_commands.Choice(name=x[1], value=str(x[0]))
                for x in name_cards
            ]
        else:
            res = [
                *[
                    discord.app_commands.Choice(name=n, value=str(i))
                    for i, n in name_cards
                ],
                *[
                    discord.app_commands.Choice(name=str(i), value=str(i))
                    for i, _ in id_cards
                ],
            ]
        if "booklet".startswith(current):
            res.append(discord.app_commands.Choice(name="booklet", value="booklet"))

        return res

    @check()
    @commands.hybrid_command(
        extras={"category": Category.CARDS, "id": 21},
        usage="use <card_id> <required_arguments>",
    )
    @discord.app_commands.describe(
        item="The card or item to use",
        target="The target of the spell",
        args="Additional required arguments by the card",
    )
    @discord.app_commands.autocomplete(item=use_cards_autocomplete)
    async def use(
        self, ctx: commands.Context, item: str, target: str = None, args: int = None
    ):
        """Use spell cards you own with this command! Check with cardinfo what arguments are required."""

        if item.lower() == "booklet":

            def make_embed(page, embed: discord.Embed, pages):
                embed.title = "Introduction booklet"
                embed.description = pages[page - 1]
                embed.set_image(
                    url="https://cdn.discordapp.com/attachments/759863805567565925/834794115148546058/image0.jpg"
                )
                return embed

            return await Paginator(ctx, BOOK_PAGES, func=make_embed).start()

        try:
            card = await self._use_check(ctx, item, target, args)
        except CheckFailure as e:
            return await ctx.send(e.message)

        args = [
            x
            for x in [
                await self._use_converter(ctx, target),
                await self._use_converter(ctx, args),
            ]
            if x
        ]

        await self._use_core(ctx, card, *args)

    @commands.hybrid_command(
        extras={"category": Category.CARDS, "id": 22},
        usage="gain <type> <card_id/amount/lootbox>",
        hidden=True,
    )
    @discord.app_commands.describe(
        type="The type of item to gain", item="The amount/id of the item to get"
    )
    async def gain(
        self,
        ctx: commands.Context,
        type: Literal["jenny", "card", "lootbox", "booster"],
        item: str,
        amount: int = 1,
    ):
        """An owner restricted command allowing the user to obtain any card or amount of jenny or any lootbox"""
        if not self.client.is_dev and not await self.client.is_owner(ctx.author):
            return await ctx.send("You are not allowed to use this command")

        user = await User.new(ctx.author.id)
        if amount < 1:
            return await ctx.send("Invalid amount")

        if type == "card":
            try:
                card = await Card.new(item)
            except CardNotFound:
                return await ctx.send("Invalid card id")
            if card.id == 0:
                return await ctx.send("No")
            if len(card.owners) + amount > card.limit * ALLOWED_AMOUNT_MULTIPLE:
                return await ctx.send("Sorry! Global card limit reached!")
            if len(user.fs_cards) + amount > FREE_SLOTS and (
                card.id > 99 or card.id in [x[0] for x in user.rs_cards]
            ):
                return await ctx.send(
                    "Seems like you have no space left in your free slots!"
                )
            await user.add_multi(
                *[(card.id, {"fake": False, "clone": False}) for _ in range(amount)]
            )
            return await ctx.send(
                f"Added card '{card.name}' to your inventory"
                + (f" {amount} times " if amount > 1 else "")
            )

        if type == "jenny":
            if not item.isdigit():
                return await ctx.send("Please provide a valid amount of jenny!")
            item = int(item)
            if item < 1:
                return await ctx.send("Please provide a valid amount of jenny!")
            if item > 69420:
                return await ctx.send("Be reasonable.")
            await user.add_jenny(int(item))
            return await ctx.send(f"Added {item} Jenny to your account")

        if type == "lootbox":
            if not item.isdigit() or not int(item) in list(LOOTBOXES.keys()):
                return await ctx.send("Invalid lootbox!")
            for _ in range(amount):
                await user.add_lootbox(int(item))
            return await ctx.send(
                f"Done! Added lootbox \"{LOOTBOXES[int(item)]['name']}\" to your inventory"
                + (f" {amount} times " if amount > 1 else "")
            )

        if type == "booster":
            if not item.isdigit() or not int(item) in list(BOOSTERS.keys()):
                return await ctx.send("Invalid booster!")
            for _ in range(amount):
                await user.add_booster(int(item))
            return await ctx.send(
                f"Done! Added booster \"{BOOSTERS[int(item)]['name']}\" to your inventory"
                + (f" {amount} times " if amount > 1 else "")
            )


Cog = Cards
