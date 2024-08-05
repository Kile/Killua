from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, ClassVar, Dict, List, Optional, Union, cast, Literal, Tuple
from dataclasses import dataclass

from killua.static.constants import (
    DB,
    FREE_SLOTS,
    DEF_SPELLS,
    PREMIUM_ALIASES,
    PATREON_TIERS,
)
from killua.utils.classes.card import Card
from killua.utils.classes.exceptions import NoMatches, NotInPossession, CardLimitReached

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
            await DB.teams.insert_one(
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
            if (
                cast(
                    timedelta, datetime.now() - self.voting_streak[site]["last_vote"]
                ).days
                > 1
            ):
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
                    await (await Card.new(id)).remove_owner(self.id)

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
            raise NotInPossession(
                "This card is not in possesion of the specified user!"
            )

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
                        raise NotInPossession(
                            "This card is not in possesion of the specified user!"
                        )
            await self._update_val("cards.fs", self.fs_cards)
        else:
            for c in cards:
                try:
                    self.rs_cards.remove(c)
                except Exception:
                    if raise_if_failed:
                        raise NotInPossession(
                            "This card is not in possesion of the specified user!"
                        )
            await self._update_val("cards.rs", self.rs_cards)

    async def _add_card_owner(self, card: int, fake: bool) -> None:
        if not fake:
            await (await Card.new(card)).add_owner(self.id)

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
                await (await Card.new(item[0])).add_owner(self.id)
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
                await (await Card.new(card)).remove_owner(self.id)
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
