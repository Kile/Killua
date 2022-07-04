from __future__ import annotations

from discord import Guild
from discord.state import ConnectionState
from discord.flags import MemberCacheFlags

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord.types.guild import Guild as GuildPayload

from .utils import get_random_discord_id, random_name

class TestingGuild(Guild):
    """A class simulating a discord guild"""

    def __init__(self, **kwargs):
        payload = self.__get_payload(**kwargs)
        ConnectionState.__init__ = self.__nothing # This is too complicated to construct with no benefit of it being instantiated correctly
        state = ConnectionState()
        state.member_cache_flags = MemberCacheFlags()
        state.user = None
        state.shard_count = 1
        super().__init__(state=state, data=payload)

    def __nothing(self) -> None:
        ...

    def __get_payload(self, **kwargs) -> GuildPayload:
        """Gets the payload for a guild"""
        payload = {
            "id": kwargs.pop("id", get_random_discord_id()),
            "name": kwargs.pop("name", random_name()),
            "owner_id": kwargs.pop("owner_id", get_random_discord_id()),
            "region": kwargs.pop("region", "us"),
            "afk_channel_id": kwargs.pop("afk_channel_id", None),
            "afk_timeout": kwargs.pop("afk_timeout", 1),
            "verification_level": kwargs.pop("verification_level", 0),
            "default_message_notifications": kwargs.pop("default_message_notifications", 0),
            "explicit_content_filter": kwargs.pop("explicit_content_filter", 0),
            "roles": kwargs.pop("roles", []),
            "mfa_level": kwargs.pop("mfa_level", 0),
            "nsfw_level": kwargs.pop("nsfw_level", 0),
            "application_id": kwargs.pop("application_id", None),
            "system_channel_id": kwargs.pop("system_channel_id", None),
            "system_channel_flags": kwargs.pop("system_channel_flags", 0),
            "rules_channel_id": kwargs.pop("rules_channel_id", None),
            "vanity_url_code": kwargs.pop("vanity_url_code", None),
            "banner": kwargs.pop("banner", None),
            "premium_tier": kwargs.pop("premium_tier", 0),
            "preferred_locale": kwargs.pop("preferred_locale", "us"),
            "public_updates_channel_id": kwargs.pop("public_updates_channel_id", None),
            "stickers": kwargs.pop("stickers", []),
            "stage_instances": kwargs.pop("stage_instances", []),
            "guild_scheduled_events": kwargs.pop("guild_sceduled_events", [])            
        }

        for key, value in kwargs.items(): # From my understanding the other attributes being NotRequired
            # means that they not have to be added to the dictionary, however if they are they need to be valid.
            # So I am saving myself the effort of making defaults but still supporting them by adding this
            payload[key] = value

        return payload