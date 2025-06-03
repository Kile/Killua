from __future__ import annotations

from typing import List, Dict, Any, ClassVar, Optional
from dataclasses import dataclass, field
from inspect import signature
from datetime import datetime

from killua.static.constants import DB
from killua.utils.classes.user import User

@dataclass
class Guild:
    """A class to handle basic guild data"""

    id: int
    prefix: str
    approximate_member_count: int = 0
    badges: List[str] = field(default_factory=list)
    commands: dict = field(
        default_factory=dict
    )  # The logic behind this is not used and needs to be rewritten
    polls: dict = field(default_factory=dict)
    tags: List[dict] = field(default_factory=list)
    added_on: Optional[datetime] = None
    cache: ClassVar[Dict[int, Guild]] = {}

    @classmethod
    def from_dict(cls, raw: dict):
        return cls(
            **{k: v for k, v in raw.items() if k in signature(cls).parameters}
        )
    
    @classmethod
    async def update_member_count(cls, guild_id: int, old_member_count: Optional[int], member_count: int) -> Optional[int]:
        """If saved member count is inaccurate by > 5%, update it"""
        old_member_count = old_member_count or 0
        if member_count > old_member_count * 1.05 or member_count < old_member_count * 0.95:
            await DB.guilds.update_one(
                {"id": guild_id}, {"$set": {"approximate_member_count": member_count}}
            )
            return member_count
        return None
    
    @classmethod
    async def _member_count_helper(cls, guild_id: int, approximate_member_count: Optional[int], member_count: Optional[int]) -> int:
        """Helper function to get the member count"""
        if member_count:
            return await cls.update_member_count(
                guild_id, approximate_member_count, member_count
            ) or approximate_member_count or member_count or 0
        return approximate_member_count or 0

    @classmethod
    async def new(cls, guild_id: int, member_count: Optional[int] = None) -> Guild:
        if guild_id in cls.cache:
            cls.cache[guild_id].approximate_member_count = await cls._member_count_helper(
                guild_id, cls.cache[guild_id].approximate_member_count, member_count
            )
            return cls.cache[guild_id]
    
        raw: Optional[dict] = await DB.guilds.find_one({"id": guild_id}) # type: ignore
        if raw is None:
            await cls.add_default(guild_id, member_count)
            raw: dict = await DB.guilds.find_one({"id": guild_id}) # type: ignore

        del raw["_id"]
        raw["approximate_member_count"] = await cls._member_count_helper(
            guild_id, raw.get("approximate_member_count", None), member_count
        )
        guild = cls.from_dict(raw)
        cls.cache[guild_id] = guild

        return guild

    @property
    def is_premium(self) -> bool:
        return ("partner" in self.badges) or ("premium" in self.badges)

    @classmethod
    async def add_default(cls, guild_id: int, member_count: Optional[int]) -> None:
        """Adds a guild to the database"""
        await DB.guilds.insert_one(
            {"id": guild_id, "points": 0, "items": "", "badges": [], "prefix": "k!", "approximate_member_count": member_count or 0, "added_on": datetime.now()}
        )

    @classmethod
    async def bulk_remove_premium(cls, guild_ids: List[int]) -> None:
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
