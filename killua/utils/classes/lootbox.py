from __future__ import annotations

import discord
from discord.ext import commands
from random import sample, randint, choices, choice
from typing import List, Dict, Union, cast, Tuple

from killua.static.constants import DB
from killua.static.enums import Booster
from killua.static.constants import BOOSTERS, LOOTBOXES, PRICES
from killua.utils.classes.user import User
from killua.utils.interactions import View
from killua.utils.classes.card import PartialCard


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
                (r * 2 if isinstance(r, int) and not self.view.children[p].disabled else r)
                for p, r in enumerate(self.rewards)
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
            for i in sample(bombs, len(bombs) // 2):
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
        if taken[(res := randint(0, 23))]:
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
        return choices(
            list(LOOTBOXES.keys()), [x["probability"] for x in LOOTBOXES.values()]
        )[0]

    @classmethod
    async def generate_rewards(self, box: int) -> List[Union[PartialCard, int]]:
        """Generates a list of rewards that can be used to pass to this class"""
        data = LOOTBOXES[box]
        rew = []

        for _ in range((cards := randint(*data["cards_total"]))):
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
            rew.append(await PartialCard.new(choice(r)))

        for _ in range(boosters := randint(*data["boosters_total"])):
            if isinstance(data["rewards"]["boosters"], int):
                rew.append(Booster(data["rewards"]["boosters"]))
            else:
                rew.append(
                    Booster(
                        choices(
                            data["rewards"]["boosters"],
                            [
                                BOOSTERS[int(x)]["probability"]
                                for x in data["rewards"]["boosters"]
                            ],
                        )[0]
                    )
                )

        for _ in range(data["rewards_total"] - cards - boosters):
            rew.append(randint(*data["rewards"]["jenny"]))

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
