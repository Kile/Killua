from __future__ import annotations

"""
This file comtains classes that are not specific to one group and are used across several files
"""

import io
import aiohttp
import pathlib
import random
import discord
import inspect

from dataclasses import dataclass, field
from discord.ext import commands
from datetime import datetime, timedelta
from PIL import Image, ImageFont, ImageDraw
from typing import Union, Tuple, List, Any, Optional, Literal, Dict, cast, ClassVar

from .paginator import View
from killua.bot import BaseBot
from killua.static.enums import Booster
from killua.static.constants import (
    FREE_SLOTS,
    PATREON_TIERS,
    LOOTBOXES,
    PREMIUM_ALIASES,
    DEF_SPELLS,
    DB,
    BOOSTERS,
    PRICES,
)


class NotInPossesion(Exception):
    pass


class CardLimitReached(Exception):
    pass


class TodoListNotFound(Exception):
    pass


class CardNotFound(Exception):
    pass


class NoMatches(Exception):
    pass


class CheckFailure(Exception):
    def __init__(self, message: str, **kwargs):
        self.message = message
        super().__init__(**kwargs)


class SuccessfullDefense(CheckFailure):
    pass


@dataclass
class PartialCard:
    """A class preventing a circular import by providing the bare minimum of methods and properties. Only used in this file"""

    id: int
    image_url: str
    owners: List[int]
    emoji: str
    limit: int
    rank: int
    type: str = "normal"

    @classmethod
    def from_dict(cls, raw: dict):
        return cls(
            **{k: v for k, v in raw.items() if k in inspect.signature(cls).parameters}
        )

    @classmethod
    async def new(cls, card_id) -> PartialCard:
        raw = dict(await DB.items.find_one({"_id": card_id}))
        if raw is None:
            raise CardNotFound
        raw["id"] = raw.pop("_id")
        raw["image_url"] = raw.pop("image")
        return cls.from_dict(raw)

    def formatted_image_url(self, client: BaseBot, *, to_fetch: bool) -> str:
        if to_fetch:
            return (
                f"http://{'api' if client.run_in_docker else '0.0.0.0'}:{client.dev_port}"
                + self.image_url
            )
        return client.url + self.image_url

    async def add_owner(self, user_id: int) -> None:
        """Adds an owner to a card entry in my db. Only used in User().add_card()"""
        self.owners.append(user_id)
        await DB.items.update_one({"_id": self.id}, {"$push": {"owners": user_id}})

    async def remove_owner(self, user_id: int) -> None:
        """Removes an owner from a card entry in my db. Only used in User().remove_card()"""
        self.owners.remove(user_id)
        await DB.items.update_one({"_id": self.id}, {"$set": {"owners": self.owners}})


class _BoosterSelect(discord.ui.Select):
    """A class letting users pick an option when trying to use a booster"""

    def __init__(self, used: List[int], inventory: Dict[str, int], **kwargs):
        super().__init__(
            min_values=1,
            max_values=1,
            placeholder="Chose what booster to use",
            **kwargs,
        )
        for booster in [k for k, v in inventory.items() if v > 0]:
            if (
                int(booster) in used and not BOOSTERS[int(booster)]["stackable"]
            ):  # If the booster cannot be used multiple times on the same lootbox
                continue
            self.add_option(
                label=BOOSTERS[int(booster)]["name"]
                + f" (left: {inventory[str(booster)]})",
                value=str(booster),
                emoji=BOOSTERS[int(booster)]["emoji"],
            )
        self.booster = None

    async def callback(self, _: discord.Interaction) -> None:
        """Callback for the select"""
        # Add booster to view
        booster = int(self.values[0])
        self.booster = booster
        self.view.stop()


class CancelButton(discord.ui.Button):
    """A class letting users cancel the booster choosing"""

    def __init__(self, **kwargs):
        super().__init__(
            label="Cancel", style=discord.ButtonStyle.red, custom_id="cancel", **kwargs
        )

    async def callback(self, _: discord.Interaction) -> None:
        """Callback for the button"""
        self.view.value = "cancel"
        self.view.stop()


class _OptionView(View):
    def __init__(self, used: List[int], **kwargs):
        self.used = used
        super().__init__(**kwargs)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green)
    async def save(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        """Saves the options"""
        await interaction.message.delete()
        self.value = "save"
        self.stop()

    @discord.ui.button(
        label="Use booster",
        style=discord.ButtonStyle.blurple,
        emoji="<:powerup:1091112046210330724",
    )
    async def booster(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        """Lets the user pick a booster"""
        user = await User.new(self.user_id)
        if not [v for v in user.boosters.values() if v > 0]:
            return await interaction.response.edit_message(
                content="You don't have any remaining boosters! Please select an option.",
                view=_OptionView(self.used, user_id=self.user_id, timeout=None),
            )

        view = View(user_id=self.user_id, timeout=200)
        select = _BoosterSelect(self.used, user.boosters)
        cancel = CancelButton()
        view.add_item(select).add_item(cancel)
        await interaction.response.edit_message(view=view)
        await view.wait()

        if view.value == "cancel":
            await view.interaction.response.defer()
            return await view.interaction.message.delete()

        elif view.timed_out:
            return await view.disable()

        if (
            select.booster in self.used and not BOOSTERS[select.booster]["stackable"]
        ):  # This should not be necessary as users should not be able to select a booster they already used in the first place
            return await view.interaction.response.edit_message(
                content="You already used this booster on this booster. Please select an option.",
                view=_OptionView(self.used, user_id=self.user_id, timeout=None),
            )

        await view.interaction.response.send_message(
            f"successfully applied `{BOOSTERS[select.booster]['name']}` booster!",
            ephemeral=True,
        )
        await view.interaction.message.delete()
        self.value = select.booster
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        """Cancels the menu"""
        await interaction.message.delete()
        self.stop()


class _LootBoxButton(discord.ui.Button):
    """A class used for lootbox buttons"""

    def __init__(
        self,
        index: int,
        rewards: List[Union[PartialCard, Booster, int, None]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.index = index
        self.custom_id = str(index)
        self._rewards = rewards
        # if self.index != 24:
        #     self.reward = self.view.rewards[self.index]
        #     self.has_reward = not not self.reward
        self.bomb = "<:bomb:1091111339226824776>"

    @property
    def rewards(self) -> List[Union[PartialCard, Booster, int, None]]:
        """Returns the rewards"""
        return self._rewards or self.view.rewards

    @property
    def reward(self) -> Union[PartialCard, Booster, int, None]:
        """Returns the reward of this button"""
        if self.index == 24:
            return None
        return self.rewards[self.index]

    @property
    def has_reward(self) -> bool:
        """Returns if this button has a reward"""
        if self.index == 24:
            return False
        return not not self.reward

    def _create_view(self) -> View:
        """Creates a new view after the callback depending on if this button has a reward"""
        for c in self.view.children:
            if c.index == self.index and not c.index == 24:
                c.disabled = True
                c.label = (
                    (
                        ""
                        if isinstance(self.reward, PartialCard)
                        else (
                            "" if isinstance(self.reward, Booster) else str(self.reward)
                        )
                    )
                    if self.has_reward
                    else ""
                )
                c.style = (
                    discord.ButtonStyle.success
                    if self.has_reward
                    else discord.ButtonStyle.red
                )
                c.emoji = (
                    (
                        self.reward.emoji
                        if isinstance(self.reward, PartialCard)
                        else (
                            BOOSTERS[int(self.reward.value)]["emoji"]
                            if isinstance(self.reward, Booster)
                            else None
                        )
                    )
                    if self.has_reward
                    else self.bomb
                )
            elif c.index == 24:
                c.disabled = not self.has_reward
            else:
                c.disabled = c.disabled if self.has_reward else True
                c.label = (
                    (
                        (
                            ""
                            if isinstance(c.reward, PartialCard)
                            else (
                                "" if isinstance(c.reward, Booster) else str(c.reward)
                            )
                        )
                        if c.has_reward
                        else ""
                    )
                    if not self.has_reward
                    else c.label
                )
                c.emoji = (
                    (
                        (
                            c.reward.emoji
                            if isinstance(c.reward, PartialCard)
                            else (
                                BOOSTERS[int(c.reward.value)]["emoji"]
                                if isinstance(c.reward, Booster)
                                else None
                            )
                        )
                        if c.has_reward
                        else self.bomb
                    )
                    if not self.has_reward
                    else c.emoji
                )

        return self.view

    async def _respond(
        self, correct: bool, last: bool, view: View, interaction: discord.Interaction
    ) -> discord.Message:
        """Responds with the new view"""
        if correct and last:
            return await interaction.response.edit_message(
                content="Congrats, you move on to the next level!", view=view
            )
        if not correct:
            return await interaction.response.edit_message(
                content="Oh no! This was not the right order! Better luck next time",
                view=view,
            )
        if not last:
            return await interaction.response.edit_message(
                content="Can you remember?", view=view
            )

    def _format_rewards(self) -> str:
        """Creates a readable string from rewards"""
        jenny = 0
        for rew in self.view.claimed:
            if isinstance(rew, int):
                jenny += rew

        rewards = (
            (
                "cards " + ", ".join(cards) + (" and " if jenny > 0 else "")
                if len(
                    cards := [
                        c.emoji for c in self.view.claimed if isinstance(c, PartialCard)
                    ]
                )
                > 0
                else ""
            )
            + (
                "boosters " + ", ".join(boosters) + (" and " if jenny > 0 else "")
                if len(
                    boosters := [
                        BOOSTERS[int(b.value)]["emoji"]
                        for b in self.view.claimed
                        if isinstance(b, Booster)
                    ]
                )
                > 0
                else ""
            )
            + (str(jenny) + " jenny" if jenny > 0 else "")
        )
        return rewards

    def _use_booster(self, booster: int) -> None:
        if booster == 1:
            # Treasure map. Find most valuable reward and highlight it by looking in self.rewards
            # and self.view.claimed
            def _monetary_value(x: Union[PartialCard, Booster, int, None]) -> int:
                """Returns the monetary value of a reward"""
                if isinstance(x, PartialCard):
                    return PRICES[x.rank]
                elif isinstance(x, Booster):
                    return (20 - BOOSTERS[x.value]["probability"]) * 100
                elif isinstance(x, int):
                    return x
                else:
                    return 0

            # Get the most valuable and unclaimed reward
            most_valuable = max(
                [
                    (p, _LootBoxButton(p, self.rewards))
                    for p, b in enumerate(self.view.children)
                    if p != 24
                    and _LootBoxButton(p, self.rewards).has_reward
                    and not cast(discord.ui.Button, b).disabled
                ],
                key=lambda x: _monetary_value(x[1].reward),
            )
            # Highlight the most valuable reward
            self.view.children[most_valuable[0]].style = discord.ButtonStyle.blurple
            self.view.children[most_valuable[0]].emoji = "\U0000274c"

        elif booster == 2:
            # 2x booster. Double all jenny rewards of hidden fields
            self.view.rewards = [
                (r * 2 if isinstance(r, int) else r) for r in self.rewards
            ]

        elif booster == 3:
            # Highlight half of the bombs and disable those fields
            bombs = [
                i
                for i, c in enumerate(self.view.children)
                if hasattr(c, "has_reward")
                and not c.has_reward
                and not c.disabled
                and i != 24
            ]  # Get list of all still active bombs
            for i in random.sample(bombs, len(bombs) // 2):
                self.view.children[i].style = discord.ButtonStyle.blurple
                self.view.children[i].emoji = "<:bomb_no:1091111155667324938>"
                self.view.children[i].disabled = True

    async def _options_button(
        self, interaction: discord.Interaction
    ) -> Union[None, discord.Message]:
        """Handles the "options" button"""
        # Create a new view with options "save" and "use booster"
        view = _OptionView(self.view.used, user_id=interaction.user.id, timeout=None)
        await interaction.response.send_message(
            content="What do you want to do?", view=view
        )
        await view.wait()

        # Handle the response
        if not view.value:
            return await view.interaction.response.defer()

        if self.view.children[-1].disabled:
            return await view.interaction.response.send_message(
                content="The box has already been opened!", ephemeral=True
            )

        if view.value == "save":
            if (
                len(self.view.claimed) == 0
            ):  # User cannot click save not having clicked any button yet
                return await view.interaction.response.send_message(
                    content="You can't save with no rewards!", ephemeral=True
                )

            # self.has_reward = False # important for _create_view
            view = self._create_view()
            self.view.saved = True

            await interaction.message.edit(
                content=f"Successfully claimed the following rewards from the box: {self._format_rewards()}",
                view=view,
            )
            self.view.stop()

        elif isinstance(view.value, int):
            user = await User.new(interaction.user.id)

            await user.use_booster(view.value)
            self._use_booster(view.value)
            self.view.used.append(view.value)
            await interaction.message.edit(view=self.view)  # sketchy

    async def _handle_incorrect(self, interaction: discord.Interaction) -> None:
        """Handles an incorrect button click"""
        view = self._create_view()
        await interaction.response.edit_message(
            content="Oh no! You lost all rewards! Better luck next time. You lost: "
            + (r if len((r := self._format_rewards())) > 1 else "no rewards"),
            view=view,
        )
        self.view.stop()

    async def _handle_correct(self, interaction: discord.Interaction) -> None:
        """Handles a correct button click"""
        view = self._create_view()
        self.view.claimed.append(self.reward)
        await interaction.response.edit_message(
            content="Correct! To save your current rewards and exit, press save. Current rewards: "
            + (r if len((r := self._format_rewards())) > 1 else "no rewards"),
            view=view,
        )

    async def callback(
        self, interaction: discord.Interaction
    ) -> Union[None, discord.Message]:
        """The callback of the button which calls the right method depending on the reward and index"""
        if self.index == 24:
            return await self._options_button(interaction)

        if not self.has_reward:
            await self._handle_incorrect(interaction)

        else:
            await self._handle_correct(interaction)


class LootBox:
    """A class which contains infos about a lootbox and can open one"""

    def __init__(
        self, ctx: commands.Context, rewards: List[Union[None, PartialCard, int]]
    ):
        self.ctx = ctx
        self.rewards = rewards

    def _assign_until_unique(self, taken: List[int]) -> int:
        if taken[(res := random.randint(0, 23))]:
            return self._assign_until_unique(taken)
        return res

    def _create_view(self) -> discord.ui.View:
        l = [None for _ in range(24)]  # creating a list of no rewards as the base
        for rew in self.rewards:
            l[self._assign_until_unique(l)] = rew

        view = View(self.ctx.author.id)
        view.rewards = l
        view.saved = False
        view.claimed = []
        view.used = []
        for i in range(24):
            view.add_item(
                _LootBoxButton(index=i, style=discord.ButtonStyle.grey, label="\u200b")
            )
        view.add_item(
            _LootBoxButton(index=24, style=discord.ButtonStyle.blurple, label="Options")
        )

        return view

    @staticmethod
    def get_lootbox_from_sku(sku: discord.SKU) -> Tuple[int, int]:
        """Gets a lootbox from a sku"""
        lootbox_amount = {
            7: 3,
            9: 3,
            10: 2,
        }
        keywords = {"titans": 7, "diamond": 9, "legends": 10}
        box_id = next((v for k, v in keywords.items() if k in sku.name.lower()), None)
        return box_id, lootbox_amount[box_id]

    @staticmethod
    def get_random_lootbox() -> int:
        """Gets a random lootbox from the LOOTBOXES constant"""
        return random.choices(
            list(LOOTBOXES.keys()), [x["probability"] for x in LOOTBOXES.values()]
        )[0]

    @classmethod
    async def generate_rewards(self, box: int) -> List[Union[PartialCard, int]]:
        """Generates a list of rewards that can be used to pass to this class"""
        data = LOOTBOXES[box]
        rew = []

        for _ in range((cards := random.randint(*data["cards_total"]))):
            skip = False
            if data["rewards"][
                "guaranteed"
            ]:  # if a card is guaranteed it is added here, it will count as one of the total_cards though
                for card, amount in data["rewards"]["guaranteed"].items():
                    if [r.id for r in rew].count(card) < amount:
                        rew.append(
                            PartialCard.new((await DB.items.find_one(card))["_id"])
                        )
                        skip = True
                        break

            if skip:
                continue
            r = [
                x["_id"]
                async for x in DB.items.find(
                    {
                        "rank": {"$in": data["rewards"]["cards"]["rarities"]},
                        "type": {"$in": data["rewards"]["cards"]["types"]},
                        "available": True,
                    }
                )
                if x["_id"] != 0
            ]
            rew.append(await PartialCard.new(random.choice(r)))

        for _ in range(boosters := random.randint(*data["boosters_total"])):
            if isinstance(data["rewards"]["boosters"], int):
                rew.append(Booster(data["rewards"]["boosters"]))
            else:
                rew.append(
                    Booster(
                        random.choices(
                            data["rewards"]["boosters"],
                            [
                                BOOSTERS[int(x)]["probability"]
                                for x in data["rewards"]["boosters"]
                            ],
                        )[0]
                    )
                )

        for _ in range(data["rewards_total"] - cards - boosters):
            rew.append(random.randint(*data["rewards"]["jenny"]))

        return rew

    async def open(self) -> None:
        """Opens a lootbox"""
        view = self._create_view()
        msg = await self.ctx.send(
            f"There are {len(self.rewards)} rewards hidden in this box. Click a button to reveal a reward. You can reveal buttons as much as you like, but careful, if you hit a bomb you loose all rewards! If you are happy with your rewards and don't want to risk anything, hit save to claim them",
            view=view,
        )
        await view.wait()
        await view.disable(msg)

        if not view.saved:
            return

        user = await User.new(self.ctx.author.id)
        for r in view.claimed:
            if isinstance(r, PartialCard):
                await user.add_card(r.id)
            elif isinstance(r, Booster):
                await user.add_booster(r.value)
            else:
                if user.is_entitled_to_double_jenny:
                    r *= 2
                await user.add_jenny(r)


# pillow logic contributed by DerUSBstick (Thank you!)
class Book:

    background_cache = {}
    card_cache = {}

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def _imagefunction(
        self, data: list, restricted_slots: bool, page: int
    ) -> Image.Image:
        """Creates the book image of the current page and returns it"""
        background = await self._getbackground(0 if len(data) == 10 else 1)
        if len(data) == 18 and restricted_slots:
            background = await self._numbers(background, data, page)
        background = await self._cards(background, data, 0 if len(data) == 10 else 1)
        background = self._setpage(background, page)
        return background

    def _get_from_cache(self, types: int) -> Union[Image.Image, None]:
        """Gets background from the cache if it exists, otherwise returns None"""
        if types == 0:
            if "first_page" in self.background_cache:
                return self.background_cache["first_page"]
            return
        else:
            if "default_background" in self.background_cache:
                return self.background_cache["default_background"]
            return

    def _set_cache(self, data: Image, first_page: bool) -> None:
        """Sets the background cache"""
        self.background_cache["first_page" if first_page else "default_background"] = (
            data
        )

    async def _getbackground(self, types: int) -> Image.Image:
        """Gets the background image of the book"""
        url = [
            "https://alekeagle.me/XdYUt-P8Xv.png",
            "https://alekeagle.me/wp2mKvzvCD.png",
        ]
        if res := self._get_from_cache(types):
            return res.convert("RGBA")

        async with self.session.get(url[types]) as res:
            image_bytes = await res.read()
            background = (img := Image.open(io.BytesIO(image_bytes))).convert("RGBA")

        self._set_cache(img, types == 0)
        return background

    async def _getcard(self, url: str) -> Image.Image:
        """Gets a card image from the url"""
        async with self.session.get(url) as res:
            image_bytes = await res.read()
            image_card = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
            image_card = image_card.resize((84, 115), Image.LANCZOS)
        # await asyncio.sleep(0.4) # This is to hopefully prevent aiohttp"s "Response payload is not completed" bug
        return image_card

    def _setpage(self, image: Image.Image, page: int) -> Image.Image:
        """Gets the plain page background and sets the page number"""
        font = self._getfont(20)
        draw = ImageDraw.Draw(image)
        draw.text((5, 385), f"{page*2-1}", (0, 0, 0), font=font)
        draw.text((595, 385), f"{page*2}", (0, 0, 0), font=font)
        return image

    def _getfont(self, size: int) -> ImageFont.ImageFont:
        font = ImageFont.truetype(
            str(pathlib.Path(__file__).parent.parent) + "/static/font.ttf",
            size,
            encoding="unic",
        )
        return font

    async def _cards(self, image: Image.Image, data: list, option: int) -> Image.Image:
        """Puts the cards on the background if there are any"""
        card_pos: list = [
            [
                (112, 143),
                (318, 15),
                (418, 15),
                (513, 15),
                (318, 142),
                (418, 142),
                (514, 142),
                (318, 269),
                (418, 269),
                (514, 269),
            ],
            [
                (12, 14),
                (112, 14),
                (207, 14),
                (12, 141),
                (112, 143),
                (208, 143),
                (13, 271),
                (112, 272),
                (209, 272),
                (318, 15),
                (417, 15),
                (513, 15),
                (318, 142),
                (418, 142),
                (514, 142),
                (318, 269),
                (418, 269),
                (514, 269),
            ],
        ]
        for n, i in enumerate(data):
            if i:
                if i[1]:
                    if not str(i[0]) in self.card_cache:
                        self.card_cache[str(i[0])] = await self._getcard(i[1])

                    card = self.card_cache[str(i[0])]
                    image.paste(card, (card_pos[option][n]), card)
        return image

    async def _numbers(self, image: Image.Image, data: list, page: int) -> Image.Image:
        """Puts the numbers on the restricted slots in the book"""
        page -= 2
        numbers_pos: list = [
            [
                (35, 60),
                (138, 60),
                (230, 60),
                (35, 188),
                (138, 188),
                (230, 188),
                (36, 317),
                (134, 317),
                (232, 317),
                (338, 60),
                (436, 60),
                (536, 60),
                (338, 188),
                (436, 188),
                (536, 188),
                (338, 317),
                (436, 317),
                (536, 317),
            ],
            [
                (30, 60),
                (132, 60),
                (224, 60),
                (34, 188),
                (131, 188),
                (227, 188),
                (32, 317),
                (130, 317),
                (228, 317),
                (338, 60),
                (436, 60),
                (533, 60),
                (338, 188),
                (436, 188),
                (533, 188),
                (338, 317),
                (436, 317),
                (533, 317),
            ],
            [
                (30, 60),
                (130, 60),
                (224, 60),
                (31, 188),
                (131, 188),
                (230, 188),
                (32, 317),
                (130, 317),
                (228, 317),
                (338, 60),
                (436, 60),
                (533, 60),
                (338, 188),
                (436, 188),
                (533, 188),
                (340, 317),
                (436, 317),
                (533, 317),
            ],
            [
                (30, 60),
                (130, 60),
                (224, 60),
                (31, 188),
                (131, 188),
                (230, 188),
                (32, 317),
                (133, 317),
                (228, 317),
                (338, 60),
                (436, 60),
                (533, 60),
                (338, 188),
                (436, 188),
                (533, 188),
                (338, 317),
                (436, 317),
                (535, 317),
            ],
            [
                (30, 60),
                (130, 60),
                (224, 60),
                (31, 188),
                (131, 188),
                (230, 188),
                (32, 317),
                (133, 317),
                (228, 317),
                (342, 60),
                (436, 60),
                (533, 60),
                (338, 188),
                (436, 188),
                (533, 188),
                (338, 317),
                (436, 317),
                (535, 317),
            ],
            [
                (30, 60),
                (130, 60),
                (224, 60),
                (31, 188),
                (131, 188),
                (230, 188),
                (32, 317),
                (133, 317),
                (228, 317),
                (342, 60),
                (436, 60),
                (533, 60),
                (338, 188),
                (436, 188),
                (533, 188),
                (338, 317),
                (436, 317),
                (535, 317),
            ],
        ]

        font = self._getfont(35)
        draw = ImageDraw.Draw(image)
        for n, i in enumerate(data):
            if i[1] is None:
                draw.text(numbers_pos[page][n], f"0{i[0]}", (165, 165, 165), font=font)
        return image

    async def _get_book(
        self,
        user: discord.Member,
        page: int,
        client: BaseBot,
        just_fs_cards: bool = False,
    ) -> Tuple[discord.Embed, discord.File]:
        """Gets a formatted embed containing the book for the user"""
        rs_cards = []
        fs_cards = []
        person = await User.new(user.id)
        if just_fs_cards:
            page += 6

        # Bringing the list in the right format for the image generator
        if page < 7:
            if page == 1:
                i = 0
            else:
                i = 10 + ((page - 2) * 18)
                # By calculating where the list should start, I make the code faster because I don't need to
                # make a list of all cards and I also don't need to deal with a problem I had when trying to get
                # the right part out of the list. It also saves me lines!
            while not len(rs_cards) % 18 == 0 or len(rs_cards) == 0:
                # I killed my pc multiple times while testing, don't use while loops!
                if not i in [x[0] for x in person.rs_cards]:
                    rs_cards.append([i, None])
                else:
                    rs_cards.append(
                        [
                            i,
                            (await PartialCard.new(i)).formatted_image_url(
                                client, to_fetch=True
                            ),
                        ]
                    )
                if page == 1 and len(rs_cards) == 10:
                    break
                i = i + 1
        else:
            i = (page - 7) * 18
            while (len(fs_cards) % 18 == 0) == False or (len(fs_cards) == 0) == True:
                try:
                    fs_cards.append(
                        [
                            person.fs_cards[i][0],
                            (
                                await PartialCard.new(person.fs_cards[i][0])
                            ).formatted_image_url(client, to_fetch=True),
                        ]
                    )
                except IndexError:
                    fs_cards.append(None)
                i = i + 1

        image = await self._imagefunction(
            rs_cards if (page <= 6 and not just_fs_cards) else fs_cards,
            (page <= 6 and not just_fs_cards),
            page,
        )

        buffer = io.BytesIO()
        image.save(buffer, "png")
        buffer.seek(0)

        f = discord.File(buffer, filename="image.png")
        embed = discord.Embed.from_dict(
            {
                "title": f"{user.display_name}'s book",
                "color": 0x2F3136,  # making the boarder "invisible" (assuming there are no light mode users)
                "image": {"url": "attachment://image.png"},
                "footer": {"text": ""},
            }
        )
        return embed, f

    async def create(
        self,
        user: discord.Member,
        page: int,
        client: BaseBot,
        just_fs_cards: bool = False,
    ) -> Tuple[discord.Embed, discord.File]:
        return await self._get_book(user, page, client, just_fs_cards)


@dataclass
class User:
    """This class allows me to handle a lot of user related actions more easily"""

    id: int
    jenny: int
    daily_cooldown: datetime
    met_user: List[int]
    effects: Dict[str, Any]
    rs_cards: List[List[int, Dict[str, Any]]]
    fs_cards: List[List[int, Dict[str, Any]]]
    _badges: List[str]
    rps_stats: Dict[str, Dict[str, int]]
    counting_highscore: Dict[str, int]
    trivia_stats: Dict[str, Dict[str, int]]
    achievements: List[str]
    votes: int
    voting_streak: Dict[str, int]
    voting_reminder: bool
    premium_guilds: Dict[str, int]
    lootboxes: List[int]
    boosters: Dict[str, int]
    weekly_cooldown: Optional[datetime]
    action_settings: Dict[str, Any]
    action_stats: Dict[str, Any]
    locale: str
    cache: ClassVar[Dict[int, User]] = {}

    @classmethod
    async def new(cls, user_id: int):
        """Creates a new user object"""
        # return cached obj if it exists
        if user_id in cls.cache:
            return cls.cache[user_id]

        data = await DB.teams.find_one({"id": user_id})
        if data is None:
            await cls.add_empty(user_id, cards=False)
            data = await DB.teams.find_one({"id": user_id})

        data = dict(data)
        data["stats"] = data.get("stats", {})

        instance = User(
            id=user_id,
            jenny=data["points"],
            daily_cooldown=data["cooldowndaily"],
            met_user=data["met_user"],
            effects=data["cards"]["effects"],
            rs_cards=data["cards"]["rs"],
            fs_cards=data["cards"]["fs"],
            _badges=data["badges"],
            rps_stats=cast(dict, data["stats"]).get(
                "rps",
                {
                    "pvp": {"won": 0, "lost": 0, "tied": 0},
                    "pve": {"won": 0, "lost": 0, "tied": 0},
                },
            ),
            counting_highscore=cast(dict, data["stats"]).get(
                "counting_highscore", {"easy": 0, "hard": 0}
            ),
            trivia_stats=cast(dict, data["stats"]).get(
                "trivia",
                {
                    "easy": {"right": 0, "wrong": 0},
                    "medium": {"right": 0, "wrong": 0},
                    "hard": {"right": 0, "wrong": 0},
                },
            ),
            achievements=data.get("achievements", []),
            votes=data.get("votes", 0),
            voting_streak=data.get("voting_streak", {}),
            voting_reminder=data.get("voting_reminder", False),
            premium_guilds=data.get("premium_guilds", {}),
            lootboxes=data.get("lootboxes", []),
            boosters=data.get("boosters", {}),
            weekly_cooldown=data.get("weekly_cooldown", None),
            action_settings=data.get("action_settings", {}),
            action_stats=data.get("action_stats", {}),
            locale=data.get("locale", None),
        )

        cls.cache[user_id] = instance
        return instance

    @property
    def badges(self) -> List[str]:
        badges = (
            self._badges.copy()
        )  # We do not want the badges added to _badges every time we call this property else it would add the same badge multiple times

        if self.action_stats.get("hug", {}).get("used", 0) >= 1000:
            badges.append("pro_hugger")

        if self.action_stats.get("hug", {}).get("targeted", 0) >= 500:
            badges.append("pro_hugged")

        if len([x for x in self.rs_cards if not x[1]["fake"]]) == 99:
            badges.append("greed_island_badge")

        if "rps_master" in self.achievements:
            badges.append("rps_master")

        return badges

    @property
    def all_cards(self) -> List[int, dict]:
        return [*self.rs_cards, *self.fs_cards]

    @property
    def is_premium(self) -> bool:
        if [x for x in self.badges if x in PREMIUM_ALIASES.keys()]:
            return True
        return len([x for x in self.badges if x in PATREON_TIERS.keys()]) > 0

    @property
    def premium_tier(self) -> Union[str, None]:
        if len((res := [x for x in self.badges if x in PREMIUM_ALIASES.keys()])) > 0:
            return PREMIUM_ALIASES[res]
        return (
            next((x for x in self.badges if x in PATREON_TIERS.keys()), None)
            if self.is_premium
            else None
        )

    @property
    def is_entitled_to_double_jenny(self) -> bool:
        return self.is_premium and self.premium_tier in list(PATREON_TIERS.keys())[2:]

    @all_cards.setter
    def all_cards(self, other):
        """The only time I"d realistically call this is to remove all cards"""
        if not isinstance(other, list) or len(other) != 0:
            raise TypeError(
                "Can only set this property to an empty list"
            )  # setting this to something else by accident could be fatal
        self.fs_cards = []
        self.rs_cards = []

    @classmethod
    async def remove_all(cls) -> str:
        """Removes all cards etc from every user. Only used for testing"""
        start = datetime.now()
        user = []
        async for u in DB.teams.find({}):
            if "cards" in u:
                user.append(u["id"])
            if "id" in u and u["id"] in cls.cache:
                cls.cache[u["id"]].all_cards = []
                cls.cache[u["id"]].effects = {}

        await DB.teams.update_many(
            {"$or": [{"id": x} for x in user]},
            {"$set": {"cards": {"rs": [], "fs": [], "effects": {}}, "met_user": []}},
        )
        cards = [
            x
            async for x in await DB.items.find({})
            if "owners" in x and len(x["owners"]) > 0
        ]
        await DB.items.update_many(
            {"_id": {"$in": [x["_id"] for x in DB.items.find()]}},
            {"$set": {"owners": []}},
        )

        return f"Removed all cards from {len(user)} user{'s' if len(user) > 1 else ''} and all owners from {len(cards)} card{'s' if len(cards) != 1 else ''} in {(datetime.now() - start).seconds} second{'s' if (datetime.now() - start).seconds > 1 else ''}"

    @classmethod
    async def is_registered(cls, user_id: int) -> bool:
        """Checks if the "cards" dictionary is in the database entry of the user"""
        u = await DB.teams.find_one({"id": user_id})
        if u is None:
            return False
        if not "cards" in u:
            return False

        return True

    @classmethod  # The reason for this being a classmethod is that User(user_id) automatically calls this function,
    # so while I will also never use this, it at least makes more sense
    async def add_empty(cls, user_id: int, cards: bool = True) -> None:
        """Can be called when the user does not have an entry to make the class return empty objects instead of None"""
        if cards:
            await DB.teams.update_one(
                {"id": user_id},
                {
                    "$set": {
                        "cards": {"rs": [], "fs": [], "effects": {}},
                        "met_user": [],
                        "votes": 0,
                    }
                },
            )
        else:
            data = await DB.teams.insert_one(
                {
                    "id": user_id,
                    "points": 0,
                    "badges": [],
                    "cooldowndaily": "",
                    "cards": {"rs": [], "fs": [], "effects": {}},
                    "met_user": [],
                    "votes": 0,
                    "voting_streak": {
                        "topgg": {"streak": 0, "last_vote": None},
                        "discordbotlist": {"streak": 0, "last_vote": None},
                    },
                    "voting_reminder": False,
                    "premium_guilds": {},
                    "lootboxes": [],
                    "weekly_cooldown": None,
                    "action_settings": {},
                    "action_stats": {},
                    "achivements": [],
                    "stats": {
                        "rps": {
                            "pvp": {"won": 0, "lost": 0, "tied": 0},
                            "pve": {"won": 0, "lost": 0, "tied": 0},
                        },
                        "counting": {"easy": 0, "hard": 0},
                        "trivia": {
                            "easy": {"right": 0, "wrong": 0},
                            "medium": {"right": 0, "wrong": 0},
                            "hard": {"right": 0, "wrong": 0},
                        },
                    },
                }
            )

    async def _update_val(self, key: str, value: Any, operator: str = "$set") -> None:
        """An easier way to update a value"""
        await DB.teams.update_one({"id": self.id}, {operator: {key: value}})

    async def add_badge(self, badge: str) -> None:
        """Adds a badge to a user"""
        if badge.lower() in self.badges:
            raise TypeError("Badge already in possesion of user")

        self._badges.append(badge.lower())
        await self._update_val("badges", badge.lower(), "$push")

    async def remove_badge(self, badge: str) -> None:
        """Removes a badge from a user"""
        if not badge.lower() in self.badges:
            return  # don't really care if that happens
        self._badges.remove(badge.lower())
        await self._update_val("badges", badge.lower(), "$pull")

    async def set_badges(self, badges: List[str]) -> None:
        """Sets badges to anything"""
        self._badges = badges
        await self._update_val("badges", self._badges)

    async def clear_premium_guilds(self) -> None:
        """Removes all premium guilds from a user"""
        self.premium_guilds = {}
        await self._update_val("premium_guilds", {})

    async def add_vote(self, site) -> None:
        """Keeps track of how many times a user has voted for Killua to increase the rewards over time"""
        self.votes += 1
        if site not in self.voting_streak:
            self.voting_streak[site] = {"streak": 0, "last_vote": None}
        self.voting_streak[site]["streak"] += 1
        if (
            site in self.voting_streak
            and self.voting_streak[site]["last_vote"] is not None
        ):
            if (datetime.now() - self.voting_streak[site]["last_vote"]).days > 1:
                self.voting_streak[site]["streak"] = 1

        self.voting_streak[site]["last_vote"] = datetime.now()
        await self._update_val("voting_streak", self.voting_streak)
        await self._update_val("votes", 1, "$inc")

    async def add_premium_guild(self, guild_id: int) -> None:
        """Adds a guild to a users premium guilds"""
        self.premium_guilds[str(guild_id)] = datetime.now()
        await self._update_val("premium_guilds", self.premium_guilds)

    async def remove_premium_guild(self, guild_id: int) -> None:
        """Removes a guild from a users premium guilds"""
        del self.premium_guilds[str(guild_id)]
        await self._update_val("premium_guilds", self.premium_guilds)

    async def claim_weekly(self) -> None:
        """Sets the weekly cooldown new"""
        self.weekly_cooldown = datetime.now() + timedelta(days=7)
        await self._update_val("weekly_cooldown", self.weekly_cooldown)

    async def claim_daily(self) -> None:
        """Sets the daily cooldown new"""
        self.daily_cooldown = datetime.now() + timedelta(days=1)
        await self._update_val("cooldowndaily", self.daily_cooldown)

    def has_lootbox(self, box: int) -> bool:
        """Returns wether the user has the lootbox specified"""
        return box in self.lootboxes

    async def add_lootbox(self, box: int) -> None:
        """Adds a lootbox to a users inventory"""
        self.lootboxes.append(box)
        await self._update_val("lootboxes", box, "$push")

    async def remove_lootbox(self, box: int) -> None:
        """Removes a lootbox from a user"""
        self.lootboxes.remove(box)
        await self._update_val("lootboxes", self.lootboxes, "$set")

    async def add_booster(self, booster: int) -> None:
        """Adds a booster to a users inventory"""
        self.boosters[str(booster)] = self.boosters.get(str(booster), 0) + 1
        await self._update_val("boosters", self.boosters, "$set")

    async def use_booster(self, booster: int) -> None:
        """Uses a booster from a users inventory"""
        self.boosters[str(booster)] -= 1
        await self._update_val("boosters", self.boosters, "$set")

    async def set_action_settings(self, settings: dict) -> None:
        """Sets the action settings for a user"""
        self.action_settings = settings
        await self._update_val("action_settings", settings)

    async def add_action(
        self, action: str, was_target: bool = False, amount: int = 1
    ) -> Optional[str]:
        """Adds an action to the action stats. If a badge was a added, returns the name of the badge."""
        if not action in self.action_stats:
            self.action_stats[action] = {
                "used": 0 if was_target else amount,
                "targeted": 1 if was_target else 0,
            }
        else:
            self.action_stats[action]["used"] += amount if not was_target else 0
            self.action_stats[action]["targeted"] += 1 if was_target else 0

        await self._update_val("action_stats", self.action_stats)

        # Check if action of a certain type are more than x and if so, add a badge. TODO these are subject to change along with the requirements
        if (
            self.action_stats[action]["used"] - amount < 1000
            and self.action_stats[action]["used"] >= 1000
            and action == "hug"
        ):
            return "pro_hugger"

        if self.action_stats[action]["targeted"] == 500:
            return "pro_hugged"

    def _has_card(
        self,
        cards: List[list],
        card_id: int,
        fake_allowed: bool,
        only_allow_fakes: bool,
    ) -> bool:
        counter = 0
        while counter != len(
            cards
        ):  # I use a while loop because it has c bindings and is thus faster than a for loop which is good for this
            id, data = cards[counter]
            if (id == card_id) and (
                (only_allow_fakes and data["fake"])
                or (
                    (not data["fake"] and not only_allow_fakes)
                    or (data["fake"] and fake_allowed)
                )
            ):
                return True

            counter += 1
        return False

    def has_rs_card(
        self, card_id: int, fake_allowed: bool = True, only_allow_fakes: bool = False
    ) -> bool:
        """Checking if the user has a card specified in their restricted slots"""
        return self._has_card(self.rs_cards, card_id, fake_allowed, only_allow_fakes)

    def has_fs_card(
        self, card_id: int, fake_allowed: bool = True, only_allow_fakes: bool = False
    ) -> bool:
        """Checking if the user has a card specified in their free slots"""
        return self._has_card(self.fs_cards, card_id, fake_allowed, only_allow_fakes)

    def has_any_card(
        self, card_id: int, fake_allowed: bool = True, only_allow_fakes: bool = False
    ) -> bool:
        """Checks if the user has the card"""
        return self._has_card(self.all_cards, card_id, fake_allowed, only_allow_fakes)

    async def remove_jenny(self, amount: int) -> None:
        """Removes x Jenny from a user"""
        if self.jenny < amount:
            raise Exception("Trying to remove more Jenny than the user has")
        self.jenny -= amount
        await self._update_val("points", -amount, "$inc")

    async def add_jenny(self, amount: int) -> None:
        """Adds x Jenny to a users balance"""
        self.jenny += amount
        await self._update_val("points", amount, "$inc")

    async def set_jenny(self, amount: int) -> None:
        """Sets the users jenny to the specified value. Only used for testing"""
        self.jenny = amount
        await self._update_val("points", amount)

    async def _find_match(
        self,
        cards: List[list],
        card_id: int,
        fake: Optional[bool],
        clone: Optional[bool],
    ) -> Tuple[Union[List[List[int, dict]], None], Union[List[int, dict], None]]:
        counter = 0
        while counter != len(
            cards
        ):  # I use a while loop because it has c bindings and is thus faster than a for loop which is good for this
            id, data = cards[counter]
            if (
                (id == card_id)
                and ((data["clone"] == clone) if not clone is None else True)
                and ((data["fake"] == fake) if not fake is None else True)
            ):

                if not data["fake"]:
                    await (await PartialCard.new(id)).remove_owner(self.id)

                del cards[
                    counter
                ]  # instead of returning the match I delete it because in theory there can be multiple matches and that would break stuff
                return cards, [id, data]
            counter += 1
        return None, None

    async def _remove_logic(
        self,
        card_type: str,
        card_id: int,
        remove_fake: bool,
        clone: bool,
        no_exception: bool = False,
    ) -> List[int, dict]:
        """Handles the logic of the remove_card method"""
        attr = getattr(self, f"{card_type}_cards")
        cards, match = await self._find_match(attr, card_id, remove_fake, clone)
        if not match:
            if no_exception:
                return await self._remove_logic("rs", card_id, remove_fake, clone)
            else:
                raise NoMatches
        before = len([x for x in cards if not x[1]["fake"]])
        await self._update_val(f"cards.{card_type}", cards)
        after = len([x for x in cards if not x[1]["fake"]])
        if before == 100 and after < 100:
            # If the book was complete before and now
            # isn't anymore, remove card 0 with it
            await self.remove_card(0)
        return match

    async def remove_card(
        self,
        card_id: int,
        remove_fake: bool = None,
        restricted_slot: bool = None,
        clone: bool = None,
    ) -> List[int, dict]:
        """Removes a card from a user"""
        if self.has_any_card(card_id) is False:
            raise NotInPossesion("This card is not in possesion of the specified user!")

        if restricted_slot:
            return await self._remove_logic("rs", card_id, remove_fake, clone)

        elif restricted_slot is False:
            return await self._remove_logic("fs", card_id, remove_fake, clone)

        else:  # if it wasn't specified it first tries to find it in the free slots, then restricted slots
            return await self._remove_logic(
                "fs", card_id, remove_fake, clone, no_exception=True
            )

    async def bulk_remove(
        self,
        cards: List[List[int, dict]],
        fs_slots: bool = True,
        raise_if_failed: bool = False,
    ) -> None:
        """Removes a list of cards from a user"""
        if fs_slots:
            for c in cards:
                try:
                    self.fs_cards.remove(c)
                except Exception:
                    if raise_if_failed:
                        raise NotInPossesion(
                            "This card is not in possesion of the specified user!"
                        )
            await self._update_val("cards.fs", self.fs_cards)
        else:
            for c in cards:
                try:
                    self.rs_cards.remove(c)
                except Exception:
                    if raise_if_failed:
                        raise NotInPossesion(
                            "This card is not in possesion of the specified user!"
                        )
            await self._update_val("cards.rs", self.rs_cards)

    async def _add_card_owner(self, card: int, fake: bool) -> None:
        if not fake:
            await (await PartialCard.new(card)).add_owner(self.id)

    async def add_card(self, card_id: int, fake: bool = False, clone: bool = False):
        """Adds a card to the the user"""
        data = [card_id, {"fake": fake, "clone": clone}]

        if self.has_rs_card(card_id) is False:
            if card_id < 100:
                self.rs_cards.append(data)
                await self._add_card_owner(card_id, fake)
                await self._update_val("cards.rs", data, "$push")
                if len([x for x in self.rs_cards if not x[1]["fake"]]) == 99:
                    await self.add_card(0)
                    await self.add_achievement("full_house")
                return

        if len(self.fs_cards) >= FREE_SLOTS:
            raise CardLimitReached("User reached card limit for free slots")
        self.fs_cards.append(data)
        await self._add_card_owner(card_id, fake)
        await self._update_val("cards.fs", data, "$push")

    def count_card(self, card_id: int, including_fakes: bool = True) -> int:
        "Counts how many copies of a card someone has"
        return len(
            [
                x
                for x in self.all_cards
                if (including_fakes or not x[1]["fake"]) and x[0] == card_id
            ]
        )

    async def add_multi(self, *args) -> None:
        """The purpose of this function is to be a faster alternative when adding multiple cards than for loop with add_card"""
        fs_cards = []
        rs_cards = []

        def fs_append(item: list):
            if len([*self.fs_cards, *fs_cards]) >= 40:
                return fs_cards
            fs_cards.append(item)
            return fs_cards

        for item in args:
            if not item[1]["fake"]:
                await (await PartialCard.new(item[0])).add_owner(self.id)
            if item[0] < 100:
                if not self.has_rs_card(item[0]):
                    if not item[0] in [x[0] for x in rs_cards]:
                        rs_cards.append(item)
                        continue
            fs_append(item)

        self.rs_cards = [*self.rs_cards, *rs_cards]
        self.fs_cards = [*self.fs_cards, *fs_cards]
        await DB.teams.update_one(
            {"id": self.id},
            {"$set": {"cards.rs": self.rs_cards, "cards.fs": self.fs_cards}},
        )

    def has_defense(self) -> bool:
        """Checks if a user holds on to a defense spell card"""
        for x in DEF_SPELLS:
            if x in [x[0] for x in self.fs_cards]:
                if self.has_any_card(x, False):
                    return True
        return False

    def can_swap(self, card_id: int) -> bool:
        """Checks if `swap` would return `False` without performing the actual swap"""
        if True in [
            x[1]["fake"] for x in self.rs_cards if x[0] == card_id
        ] and False in [x[1]["fake"] for x in self.fs_cards if x[0] == card_id]:
            return True

        elif True in [
            x[1]["fake"] for x in self.fs_cards if x[0] == card_id
        ] and False in [x[1]["fake"] for x in self.rs_cards if x[0] == card_id]:
            return True

        else:
            return False  # Returned if the requirements haven't been met

    async def swap(self, card_id: int) -> Union[bool, None]:
        """
        Swaps a card from the free slots with one from the restricted slots.
        Usecase: swapping fake and real card
        """

        if True in [
            x[1]["fake"] for x in self.rs_cards if x[0] == card_id
        ] and False in [x[1]["fake"] for x in self.fs_cards if x[0] == card_id]:
            r = await self.remove_card(card_id, remove_fake=True, restricted_slot=True)
            r2 = await self.remove_card(
                card_id, remove_fake=False, restricted_slot=False
            )
            await self.add_card(card_id, False, r[1]["clone"])
            await self.add_card(card_id, True, r2[1]["clone"])

        elif True in [
            x[1]["fake"] for x in self.fs_cards if x[0] == card_id
        ] and False in [x[1]["fake"] for x in self.rs_cards if x[0] == card_id]:
            r = await self.remove_card(card_id, remove_fake=True, restricted_slot=False)
            r2 = await self.remove_card(
                card_id, remove_fake=False, restricted_slot=True
            )
            await self.add_card(card_id, True, r[1]["clone"])
            await self.add_card(card_id, False, r2[1]["clone"])

        else:
            return False  # Returned if the requirements haven't been met

    async def add_effect(self, effect: str, value: Any):
        """Adds a card with specified value, easier than checking for appropriate value with effect name"""
        self.effects[effect] = value
        await self._update_val("cards.effects", self.effects)

    async def remove_effect(self, effect: str):
        """Remove effect provided"""
        self.effects.pop(effect, None)
        await self._update_val("cards.effects", self.effects)

    def has_effect(self, effect: str) -> Tuple[bool, Any]:
        """Checks if a user has an effect and returns what effect if the user has it"""
        if effect in self.effects:
            return True, self.effects[effect]
        else:
            return False, None

    async def add_met_user(self, user_id: int) -> None:
        """Adds a user to a "previously met" list which is a parameter in some spell cards"""
        if not user_id in self.met_user:
            self.met_user.append(user_id)
            await self._update_val("met_user", user_id, "$push")

    def has_met(self, user_id: int) -> bool:
        """Checks if the user id provided has been met by the self.id user"""
        return user_id in self.met_user

    async def _remove(self, cards: str) -> None:
        for card in [x[0] for x in getattr(self, cards)]:
            try:
                await (await PartialCard.new(card)).remove_owner(self.id)
            except Exception:
                pass

        setattr(self, cards, [])

    async def nuke_cards(self, t: str = "all") -> bool:
        """A function only intended to be used by bot owners, not in any actual command, that"s why it returns True, so the owner can see if it succeeded"""
        if t == "all":
            await self._remove("all_cards")
            self.effects = {}
            await DB.teams.update_one(
                {"id": self.id},
                {"$set": {"cards": {"rs": [], "fs": [], "effects": {}}}},
            )
        if t == "fs":
            await self._remove("fs_cards")
            await DB.teams.update_one({"id": self.id}, {"$set": {"cards.fs": []}})
        if t == "rs":
            await self._remove("rs_cards")
            await DB.teams.update_one({"id": self.id}, {"$set": {"cards.rs": []}})
        if t == "effects":
            self.effects = {}
            await DB.teams.update_one({"id": self.id}, {"$set": {"cards.effects": {}}})

        return True

    async def add_rps_stat(
        self, stat: Literal["won", "tied", "lost"], against_bot: bool, val: int = 1
    ) -> None:
        """Adds a stat to the user's rps stats"""
        if stat in self.rps_stats["pvp" if not against_bot else "pve"]:
            self.rps_stats["pvp" if not against_bot else "pve"][stat] += val
        else:
            self.rps_stats["pvp" if not against_bot else "pve"][stat] = val
        await self._update_val(f"stats.rps", self.rps_stats)

    async def add_trivia_stat(
        self,
        stat: Literal["right", "wrong"],
        difficulty: Literal["easy", "medium", "hard"],
    ) -> None:
        """Adds a stat to the user's trivia stats"""
        if difficulty in self.trivia_stats and stat in self.trivia_stats[difficulty]:
            self.trivia_stats[difficulty][stat] += 1
        else:
            self.trivia_stats[difficulty][stat] = 1
        await self._update_val(f"stats.trivia", self.trivia_stats)

    async def set_counting_highscore(
        self, difficulty: Literal["easy", "hard"], score: int
    ) -> None:
        """Sets the highscore for counting"""
        if score > self.counting_highscore[difficulty]:
            self.counting_highscore[difficulty] = score
            await self._update_val(f"stats.counting_highscore", self.counting_highscore)

    async def add_achievement(self, achievement: str) -> None:
        """Adds an achievement to the user's achievements"""
        if not achievement in self.achievements:
            self.achievements.append(achievement)
            await self._update_val("achievements", achievement, "$push")

    async def log_locale(self, locale: str) -> Optional[str]:
        """Logs the locale of the user. Returns the old locale if it was different from the new one, else None"""
        if not self.locale or self.locale != locale:
            old = self.locale
            self.locale = locale
            await self._update_val("locale", locale)
            return old


@dataclass
class TodoList:
    id: int
    owner: int
    name: str
    _custom_id: Optional[str]
    status: str
    delete_done: bool
    viewer: List[int]
    editor: List[int]
    created_at: Union[str, datetime]
    spots: int
    views: int
    todos: List[dict]
    _bought: List[str]
    thumbnail: Optional[str]
    color: Optional[int]
    description: Optional[str]

    cache: ClassVar[Dict[int, TodoList]] = {}
    custom_id_cache: ClassVar[Dict[str, int]] = {}

    @classmethod
    def __get_cache(cls, list_id: Union[int, str]):
        """Returns a cached object"""
        if isinstance(list_id, str) and not list_id.isdigit():
            if not list_id in cls.custom_id_cache:
                return None
            list_id = cls.custom_id_cache[list_id]
        return cls.cache[int(list_id)] if list_id in cls.cache else None

    @classmethod
    async def new(cls, list_id: Union[int, str]) -> TodoList:
        cached = cls.__get_cache(list_id)
        if cached is not None:
            return cached

        raw = await DB.todo.find_one(
            {
                (
                    "_id"
                    if (isinstance(list_id, int) or list_id.isdigit())
                    else "custom_id"
                ): (
                    int(list_id)
                    if (isinstance(list_id, int) or list_id.isdigit())
                    else list_id.lower()
                )
            }
        )

        if raw is None:
            raise TodoListNotFound()

        td_list = TodoList(
            id=raw["_id"],
            owner=raw["owner"],
            name=raw["name"],
            _custom_id=raw["custom_id"],
            status=raw["status"],
            delete_done=raw["delete_done"],
            viewer=raw["viewer"],
            editor=raw["editor"],
            created_at=raw["created_at"],
            spots=raw["spots"],
            views=raw["views"],
            todos=raw["todos"],
            _bought=raw.get("bought", []),
            thumbnail=raw.get("thumbnail", None),
            color=raw.get("color", None),
            description=raw.get("description", None),
        )

        if td_list.custom_id:
            td_list.custom_id_cache[td_list.custom_id] = td_list.id
        td_list.cache[td_list.id] = td_list

        return td_list

    @property
    def custom_id(self) -> Union[str, None]:
        return self._custom_id

    @custom_id.setter
    def custom_id(self, value: str) -> None:
        del self.custom_id_cache[self._custom_id]
        self._custom_id = value
        self.custom_id_cache[value] = self.id

    def __len__(self) -> int:
        """Makes it nicer to get the "length" of a todo list, or rather the length of its todo"s"""
        return len(self.todos)

    @staticmethod
    async def _generate_id() -> int:
        l = []
        while len(l) != 6:
            l.append(str(random.randint(0, 9)))

        todo_id = await DB.todo.find_one({"_id": "".join(l)})

        if todo_id is None:
            return int("".join(l))
        else:
            return TodoList._generate_id()

    @staticmethod
    async def create(
        owner: int, title: str, status: str, done_delete: bool, custom_id: str = None
    ) -> TodoList:
        """Creates a todo list and returns a TodoList class"""
        list_id = await TodoList._generate_id()
        await DB.todo.insert_one(
            {
                "_id": list_id,
                "name": title,
                "owner": owner,
                "custom_id": custom_id,
                "status": status,
                "delete_done": done_delete,
                "viewer": [],
                "editor": [],
                "todos": [
                    {
                        "todo": "add todos",
                        "marked": None,
                        "added_by": 756206646396452975,
                        "added_on": datetime.now(),
                        "views": 0,
                        "assigned_to": [],
                        "mark_log": [],
                    }
                ],
                "marks": [],
                "created_at": (datetime.now()).strftime("%b %d %Y %H:%M:%S"),
                "spots": 10,
                "views": 0,
            }
        )
        return TodoList(list_id)

    async def delete(self) -> None:
        """Deletes a todo list"""
        del self.cache[self.id]
        if self.custom_id:
            del self.custom_id_cache[self.custom_id]
        await DB.todo.delete_one({"_id": self.id})

    def has_view_permission(self, user_id: int) -> bool:
        """Checks if someone has permission to view a todo list"""
        if self.status == "private":
            if not (
                user_id in self.viewer
                or user_id in self.editor
                or user_id == self.owner
            ):
                return False
        return True

    def has_edit_permission(self, user_id: int) -> bool:
        """Checks if someone has permission to edit a todo list"""
        if not (user_id in self.editor or user_id == self.owner):
            return False
        return True

    async def _update_val(self, key: str, value: Any, operator: str = "$set") -> None:
        """An easier way to update a value"""
        await DB.todo.update_one({"_id": self.id}, {operator: {key: value}})

    async def set_property(self, prop: str, value: Any) -> None:
        """Sets any property and updates the db as well"""
        setattr(self, prop, value)
        await self._update_val(prop, value)

    async def add_view(self, viewer: int) -> None:
        """Adds a view to a todo lists viewcount"""
        if (
            not viewer == self.owner
            and not viewer in self.viewer
            and viewer in self.editor
        ):
            self.views += 1
            await self._update_val("views", 1, "$inc")

    async def add_task_view(self, viewer: int, task_id: int) -> None:
        """Adds a view to a todo task"""
        if (
            not viewer == self.todos[task_id - 1]["added_by"]
            and not viewer in self.todos[task_id - 1]["assigned_to"]
        ):
            self.todos[task_id - 1]["views"] += 1
            await self._update_val("todos", self.todos)

    async def add_spots(self, spots: int) -> None:
        """Easy way to add max spots"""
        self.spots += spots
        await self._update_val("spots", spots, "$inc")

    async def add_editor(self, user: int) -> None:
        """Easy way to add an editor"""
        self.editor.append(user)
        await self._update_val("editor", user, "$push")

    async def add_viewer(self, user: int) -> None:
        """Easy way to add a viewer"""
        self.viewer.append(user)
        await self._update_val("viewer", user, "$push")

    async def kick_editor(self, editor: int) -> None:
        """Easy way to kick an editor"""
        self.editor.remove(editor)
        await self._update_val("editor", editor, "$pull")

    async def kick_viewer(self, viewer: int) -> None:
        """Easy way to kick a viewer"""
        self.viewer.remove(viewer)
        await self._update_val("viewer", viewer, "$pull")

    def has_todo(self, task: int) -> bool:
        """Checks if a list contains a certain todo task"""
        try:
            if task < 1:
                return False
            self.todos[task - 1]
        except Exception:
            return False
        return True

    async def clear(self) -> None:
        """Removes all todos from a todo list"""
        self.todos = []
        await self._update_val("todos", [])

    async def enable_addon(self, addon: str) -> None:
        """Adds an attribute to the bought list to be able to be used"""
        if not addon.lower() in self._bought:
            await self._update_val("bought", addon.lower(), "$push")
            self._bought.append(addon.lower())

    def has_addon(self, addon: str) -> bool:
        """Checks if a todo list can be customized with the gived attribute"""
        return addon.lower() in self._bought


@dataclass
class Todo:
    position: int
    todo: str
    marked: str
    added_by: int
    added_on: Union[str, datetime]
    views: int
    assigned_to: List[int]
    mark_log: List[dict]
    due_at: datetime = None
    notified: bool = None

    @classmethod
    async def new(cls, position: Union[int, str], list_id: Union[int, str]) -> Todo:
        parent = await TodoList.new(list_id)
        task = parent.todos[int(position) - 1]

        return Todo(position=position, **task)


@dataclass
class Guild:
    """A class to handle basic guild data"""

    id: int
    prefix: str
    badges: List[str] = field(default_factory=list)
    commands: dict = field(
        default_factory=dict
    )  # The logic behind this is not used and needs to be rewritten
    polls: dict = field(default_factory=dict)
    tags: List[dict] = field(default_factory=list)
    cache: ClassVar[Dict[int, Guild]] = {}

    @classmethod
    def from_dict(cls, raw: dict):
        return cls(
            **{k: v for k, v in raw.items() if k in inspect.signature(cls).parameters}
        )

    @classmethod
    async def new(cls, guild_id: int) -> Guild:
        raw = await DB.guilds.find_one({"id": guild_id})
        if not raw:
            await cls.add_default(guild_id)
            raw = await DB.guilds.find_one({"id": guild_id})
        del raw["_id"]
        guild = cls.from_dict(raw)
        cls.cache[guild_id] = guild
        return guild

    @property
    def is_premium(self) -> bool:
        return ("partner" in self.badges) or ("premium" in self.badges)

    @classmethod
    async def add_default(self, guild_id: int) -> None:
        """Adds a guild to the database"""
        await DB.guilds.insert_one(
            {"id": guild_id, "points": 0, "items": "", "badges": [], "prefix": "k!"}
        )

    @classmethod
    async def bullk_remove_premium(cls, guild_ids: List[int]) -> None:
        """Removes premium from all guilds specified, if possible"""
        for guild in guild_ids:
            try:
                User.cache[guild].badges.remove("premium")
            except Exception:
                guild_ids.remove(
                    guild
                )  # in case something got messed up it removes the guild id before making the db interaction

        await DB.guilds.update_many(
            {"id": {"$in": guild_ids}}, {"$pull": {"badges": "premium"}}
        )

    async def _update_val(self, key: str, value: Any, operator: str = "$set") -> None:
        """An easier way to update a value"""
        await DB.guilds.update_one({"id": self.id}, {operator: {key: value}})

    async def delete(self) -> None:
        """Deletes a guild from the database"""
        del self.cache[self.id]
        await DB.guilds.delete_one({"id": self.id})

    async def change_prefix(self, prefix: str) -> None:
        "Changes the prefix of a guild"
        self.prefix = prefix
        await self._update_val("prefix", self.prefix)

    async def add_premium(self) -> None:
        """Adds premium to a guild"""
        self.badges.append("premium")
        await self._update_val("badges", "premium", "$push")

    async def remove_premium(self) -> None:
        """ "Removes premium from a guild"""
        self.badges.remove("premium")
        await self._update_val("badges", "premium", "$pull")

    async def add_poll(self, id: int, poll_data: dict) -> None:
        """Adds a poll to a guild"""
        self.polls[id] = poll_data
        await self._update_val("polls", self.polls)

    async def close_poll(self, id: int) -> None:
        """Closes a poll"""
        del self.polls[id]
        await self._update_val("polls", self.polls)

    async def update_poll_votes(self, id: int, updated: dict) -> None:
        """Updates the votes of a poll"""
        self.polls[str(id)]["votes"] = updated
        await self._update_val(f"polls.{id}.votes", updated)
