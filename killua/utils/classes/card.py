from __future__ import annotations

from typing import List, ClassVar, Dict, Tuple, Union, Tuple, TYPE_CHECKING, Type

from killua.static.constants import DB
from killua.bot import BaseBot

import discord
from io import BytesIO
from discord.ext import commands
from typing import List, Tuple, Optional, Callable

from killua.static.constants import (
    ALLOWED_AMOUNT_MULTIPLE,
    DEF_SPELLS,
    VIEW_DEF_SPELLS,
    FREE_SLOTS,
    DB,
)
from killua.bot import BaseBot


from killua.utils.classes import User
from killua.utils.interactions import Select, View, Button


class CheckFailure(Exception):
    def __init__(self, message: str, **kwargs):
        self.message = message
        super().__init__(**kwargs)


class SuccessfulDefense(CheckFailure):
    pass


class CardNotFound(Exception):
    pass


class Card:
    """A class preventing a circular import by providing the bare minimum of methods and properties. Only used in this module"""

    raw: ClassVar[List[Dict[str, Union[str, int, bool]]]] = []  # Raw data from API

    id: int
    name: str
    image_url: str
    description: str
    emoji: str
    rank: str
    limit: int
    available: bool
    type: str = "normal"
    range: Optional[str] = None
    ctx: Optional[commands.Context] = None
    _cls: Optional[List[str]] = None

    cache: ClassVar[Dict[int, Card]] = {}  # Cached objects
    cached_raw: ClassVar[List[Tuple[str, int]]] = []  # String to int ID mapping

    @classmethod
    def _should_ignore(cls, cached: Type[Card]) -> bool:
        """
        In this case a card is cached but a spell is requested. Cache spell instead
        because a spell has all the class has but not the other way around
        """
        return isinstance(cached, Card) and (
            issubclass(type(cls), type(cached)) or not isinstance(cls, type(cached))
        )

    @classmethod
    def __get_cache(cls, cards_id: int):
        """Returns a cached object"""
        if cards_id in cls.cache and not cls._should_ignore(cls.cache[cards_id]):
            return cls.cache[cards_id]

    def __new__(cls, name_or_id: int, *args, **kwargs):
        existing = cls.__get_cache(name_or_id)
        if existing:
            return existing
        return super().__new__(cls)

    @classmethod
    def _find_card(cls, name_or_id: Union[int, str]) -> Union[int, None]:

        # This could be solved much easier but this allows the user to
        # have case insensitivity when looking for a card
        if not cls.cached_raw:
            cls.cached_raw = [(c["name"], c["id"]) for c in cls.raw]

        for c in cls.cached_raw:

            if not isinstance(name_or_id, int) and not name_or_id.isdigit():
                if c[0].lower() == name_or_id.lower():
                    return c[1]
            elif isinstance(name_or_id, int):
                if c[1] == name_or_id:
                    return c[1]
            else:
                if c[1] == int(name_or_id):
                    return c[1]

    def __init__(self, name_or_id: Union[str, int], ctx: Optional[commands.Context] = None):
        cards_id = self._find_card(name_or_id)

        if cards_id in self.cache and not self._should_ignore(self.cache[cards_id]):
            self.ctx = ctx
            return

        if not cards_id:
            raise CardNotFound

        raw = next(c for c in self.raw if c["id"] == cards_id)

        self.id = cards_id
        self.name = raw["name"]
        self.image_url = raw["image"]
        self.description = raw["description"]
        self.emoji = raw["emoji"]
        self.rank = raw["rank"]
        self.limit = raw["limit"]
        self.available = raw.get("available", True)
        self.type = raw.get("type", "normal")
        self.range = raw.get("range", None)
        self._cls = raw.get("class", None)
        self.ctx = ctx

        self.cache[cards_id] = self

    @classmethod
    def find(cls, conditions: Callable[dict, bool]) -> List[Card]:  # type: ignore
        """
        Finds all cards that match the given conditions, replacing mongo's find method.
        Already parses the cards to Card classes in the return value
        """
        return [cls(c["id"]) for c in cls.raw if conditions(c)]

    async def owners(self) -> List[int]:
        return [
            entry["id"]
            async for entry in DB.teams.find(
                {
                    "$or": [
                        {
                            "cards.fs": {
                                "$elemMatch": {
                                    "0": self.id,  # Match the first element of the subarray
                                    "1.fake": False,  # Match the 'fake' field in the second element
                                }
                            }
                        },
                        {"cards.rs": {"$elemMatch": {"0": self.id, "1.fake": False}}},
                    ]
                }
            )
        ]

    def formatted_image_url(self, client: BaseBot, *, to_fetch: bool) -> str:
        endpoint = self.image_url.split("image/")[1]
        token, expiry = client.sha256_for_api(endpoint, 60 * 60 * 24)
        if to_fetch:
            return f"http://{'api' if client.run_in_docker else '0.0.0.0'}:{client.dev_port}{self.image_url}?token={token}&expiry={expiry}"

        return client.url + self.image_url + f"?token={token}&expiry={expiry}"

    async def _wait_for_defense(
        self, ctx: commands.Context, other: "User", effects: list
    ) -> None:

        if len(effects) == 0:
            return

        effect_instances: List["Card"] = [Card(c) for c in effects]
        view = View(other.id, timeout=20)
        view.add_item(
            Select(
                options=[
                    discord.SelectOption(label=c.name, emoji=c.emoji, value=str(c.id))
                    for c in effect_instances
                ]
            )
        )
        view.add_item(
            Button(label="Ignore", style=discord.ButtonStyle.red, custom_id="ignore")
        )

        msg = await ctx.send(
            f"<@{other.id}> {ctx.author} has used the spell `{self.id}` on you! You have {len(effect_instances)} spells to defend yourself. You can either choose one of them to defend yourself with or let the attack go through",
            view=view,
        )
        await view.wait()
        await view.disable(msg)

        if not view.value:
            if view.timed_out:
                await ctx.send(
                    f"No response from the attacked user, the attack goes through!",
                    reference=msg,
                )
            else:
                await ctx.send(
                    "You decided not to use a defense spell, the attack goes through!",
                    reference=msg,
                )
            return

        if isinstance(view.value, int):
            await other.remove_card(view.value)
            raise SuccessfulDefense(
                f"<@{other.id}> successfully defended against your attack"
            )
        else:
            await ctx.send(
                "You decided not to use a defense spell, the attack goes through!",
                reference=msg,
            )

    async def _view_defense_check(self, ctx: commands.Context, other: "User") -> None:
        effects = []
        for c in other.fs_cards:
            if c[0] in VIEW_DEF_SPELLS and not c[0] in effects:
                effects.append(c[0])

        await self._wait_for_defense(ctx, other, effects)

    async def _attack_defense_check(
        self, ctx: commands.Context, other: "User", target_card: int
    ) -> None:
        if target_card in [
            x[0] for x in other.rs_cards
        ]:  # A list of cards that steal from restricted slots
            if (
                f"page_protection_{int((target_card-10)/18+2)}" in other.effects
                and not target_card in [x[0] for x in other.fs_cards]
            ):
                raise SuccessfulDefense(
                    "The user has protected the page this card is in against spells!"
                )

        if other.has_effect("1026")[0]:
            if 1026 in [
                x[0] for x in other.all_cards
            ]:  # Card has to remain in posession
                if other.effects["1026"] - 1 == 0:
                    await other.remove_effect("1026")
                    await other.remove_card(1026)
                else:
                    await other.add_effect("1026", other.effects["1026"] - 1)
                raise SuccessfulDefense(
                    "The user had remaining protection from card 1026 thus your attack failed"
                )

        effects = []
        for c in other.fs_cards:
            if c[0] in DEF_SPELLS and not c[0] in effects:
                if c[0] == 1019 and not self.range == "SR":
                    continue
                if c[0] == 1004 and self.ctx.author.id not in other.met_user:
                    continue
                effects.append(c[0])

        await self._wait_for_defense(ctx, other, effects)

    def _permission_check(self, ctx: commands.Context, member: discord.Member) -> None:
        perms = ctx.channel.permissions_for(member)
        if not perms.send_messages or not perms.read_messages:
            raise CheckFailure(
                f"You can only attack a user in a channel they have read and write permissions to which isn't the case with {self.Member.display_name}"
            )

    def _has_cards_check(
        self,
        cards: List[list],
        card_type: str = "",
        is_self: bool = False,
        uses_up: bool = False,
    ) -> None:
        if len(cards) == 0:
            raise CheckFailure(
                (
                    f"You do not have cards{card_type}!"
                    if is_self
                    else f"This user does not have any cards{card_type}!"
                )
                + (f" This information uses up card {self.name}." if uses_up else "")
            )

    def _has_any_card(self, card_id: int, user: "User") -> None:
        if not user.has_any_card(card_id):
            raise CheckFailure("The specified user doesn't have this card")

    def _has_met_check(
        self, prefix: str, author: "User", other: discord.Member
    ) -> None:
        if not author.has_met(other.id):
            raise CheckFailure(
                f"You haven't met this user yet! Use `{prefix}meet <@someone>` if they send a message in a channel to be able to use this card on them"
            )

    def _has_other_card_check(self, cards: List[list]) -> None:
        if len(cards) < 2:
            raise CheckFailure(f"You don't have any cards other than card {self.name}!")

    async def _is_maxed_check(self, card: int) -> None:
        c = Card(card)
        if len(await c.owners()) >= c.limit * ALLOWED_AMOUNT_MULTIPLE:
            raise CheckFailure(
                f"The maximum amount of existing cards with id {card} is reached!"
            )

    def _is_full_check(self, user: "User") -> None:
        if len(user.fs_cards) >= FREE_SLOTS:
            raise CheckFailure("You don't have any space in your free slots left!")

    async def _is_valid_card_check(self, card_id: int) -> None:
        try:
            Card(card_id)
        except CardNotFound:
            raise CheckFailure("Specified card is invalid!")

    def _has_effect_check(self, user: "User", effect: str) -> None:
        if user.has_effect(effect)[0]:
            raise CheckFailure("You already have this effect in place!")

    async def _get_analysis_embed(
        self, card_id: int, client: BaseBot
    ) -> Tuple[discord.Embed, Optional[discord.File]]:
        card = Card(card_id)
        fields = [
            {"name": "Name", "value": card.name + " " + card.emoji, "inline": True},
            {
                "name": "Type",
                "value": card.type.replace("normal", "item"),
                "inline": True,
            },
            {"name": "Rank", "value": card.rank, "inline": True},
            {
                "name": "Limit",
                "value": str(card.limit * ALLOWED_AMOUNT_MULTIPLE),
                "inline": True,
            },
            {
                "name": "Available",
                "value": "Yes" if card.available else "No",
                "inline": True,
            },
        ]
        if card.type == "spell":
            fields.append(
                {"name": "Class", "value": ", ".join(card._cls), "inline": True}
            )
            fields.append({"name": "Range", "value": card.range, "inline": True})

        embed = discord.Embed.from_dict(
            {
                "title": f"Info about card {card_id}",
                "color": 0x3E4A78,
                "description": card.description,
                "fields": fields,
            }
        )
        return await client.make_embed_from_api(
            card.formatted_image_url(client, to_fetch=client.is_dev), embed, no_token=True, thumbnail=True
        )

    async def _get_list_embed(
        self, card_id: int, client: BaseBot
    ) -> Tuple[discord.Embed, Optional[discord.File]]:
        card = Card(card_id)

        real_owners = []
        for o in await card.owners():
            # Get the total number of owners
            if o not in real_owners:
                real_owners.append(o)
        embed = discord.Embed.from_dict(
            {
                "title": f"Infos about card {card.name}",
                "description": f"**Total copies in circulation**: {len(await card.owners())}\n\n**Total owners**: {len(real_owners)}",
                "color": 0x3E4A78,
            }
        )
        return await client.make_embed_from_api(
            card.formatted_image_url(client, to_fetch=client.is_dev), embed, no_token=True
        )
