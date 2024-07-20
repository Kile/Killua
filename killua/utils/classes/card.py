from __future__ import annotations

from typing import List, ClassVar, Dict, Tuple, Union, Tuple, Type
from dataclasses import dataclass

from killua.static.constants import DB
from killua.utils.classes.exceptions import CardNotFound
from killua.bot import BaseBot


# Unfortunately, for the Card class that provides useful methods for spell cards
# needs to import the User class which in turn needs to import the Card class.
# The actual methods of that spell card base class are not needed in the User class,
# so I created a partial class that only contains the necessary methods and properties
# to prevent a circular import. This is only used in this module.
#
# Circular import:
#             ⏤⏤⏤⏤⏤⏤
#           /             ↘︎
#       User                Card
#           ↖︎             /
#             ⏤⏤⏤⏤⏤⏤

@dataclass
class PartialCard:
    """A class preventing a circular import by providing the bare minimum of methods and properties. Only used in this module"""

    id: int
    name: str
    image_url: str
    owners: List[int]
    description: str
    emoji: str
    rank: str
    limit: int
    available: bool
    type: str = "normal"
    range: str = None
    _cls: List[str] = None

    cache: ClassVar[Dict[int, PartialCard]] = {}
    cached_raw: ClassVar[List[Tuple[str, int]]] = []

    @classmethod
    async def _find_card(cls, name_or_id: Union[int, str]) -> Union[int, None]:

        # This could be solved much easier but this allows the user to
        # have case insensitivity when looking for a card
        if not cls.cached_raw:
            cls.cached_raw = [(c["name"], c["_id"]) async for c in DB.items.find({})]
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

    @classmethod
    async def new(cls, name_or_id: str) -> Type[PartialCard]:
        cards_id = await cls._find_card(name_or_id)

        if cards_id in cls.cache:
            return cls.cache[cards_id]

        if not cards_id:
            raise CardNotFound

        raw = dict(await DB.items.find_one({"_id": cards_id}))

        card = cls(
            id=cards_id,
            name=raw["name"],
            image_url=raw["image"],
            owners=raw["owners"],
            description=raw["description"],
            emoji=raw["emoji"],
            rank=raw["rank"],
            limit=raw["limit"],
            available=raw.get("available", True),
            type=raw.get("type", "normal"),
            range=raw.get("range", None),
            _cls=raw.get("class", None),
        )

        cls.cache[cards_id] = card
        return card

    def formatted_image_url(self, client: BaseBot, *, to_fetch: bool) -> str:
        if to_fetch:
            return (
                f"http://{'api' if client.run_in_docker else '0.0.0.0'}:{client.dev_port}"
                + self.image_url
            )
        return client.url + self.image_url

    async def add_owner(self, user_id: int):
        """Adds an owner to a card entry in my db. Only used in Card().add_card()"""
        self.owners.append(user_id)
        await DB.items.update_one({"_id": self.id}, {"$set": {"owners": self.owners}})

    async def remove_owner(self, user_id: int):
        """Removes an owner from a card entry in my db. Only used in Card().remove_card()"""
        self.owners.remove(user_id)
        await DB.items.update_one({"_id": self.id}, {"$set": {"owners": self.owners}})
