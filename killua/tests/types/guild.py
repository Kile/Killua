from __future__ import annotations

from discord import Guild, Asset

from .utils import get_random_discord_id, random_name

from typing import Union

class TestingGuild:
    """A class simulating a discord guild"""

    __class__ = Guild

    def __init__(self, **kwargs):
        self.id: int = kwargs.pop("id", get_random_discord_id())
        self.name: str = kwargs.pop("name", random_name())
        self.owner_id: int = kwargs.pop("owner_id", get_random_discord_id())
        self.region: str = kwargs.pop("region", "us")
        self.afk_channel_id: int = kwargs.pop("afk_channel_id", None)
        self.afk_timeout: int = kwargs.pop("afk_timeout", 1)
        self.verification_level: int = kwargs.pop("verification_level", 0)
        self.default_message_notifications: int = kwargs.pop("default_message_notifications", 0)
        self.explicit_content_filter: int = kwargs.pop("explicit_content_filter", 0)
        self.roles: list = kwargs.pop("roles", [])
        self.mfa_level: int = kwargs.pop("mfa_level", 0)
        self.nsfw_level: int = kwargs.pop("nsfw_level", 0)
        self.application_id: Union[int, None] = kwargs.pop("application_id", None)
        self.system_channel_id: Union[int, None] = kwargs.pop("system_channel_id", None)
        self.system_channel_flags: int = kwargs.pop("system_channel_flags", 0)
        self.rules_channel_id: Union[int, None] = kwargs.pop("rules_channel_id", None)
        self.vanity_url_code: Union[int, None] = kwargs.pop("vanity_url_code", None)
        self.banner: Union[Asset, None] = kwargs.pop("banner", None)
        self.premium_tier: int = kwargs.pop("premium_tier", 0)
        self.preferred_locale: str = kwargs.pop("preferred_locale", "us")
        self.public_updates_channel_id: Union[int, None] = kwargs.pop("public_updates_channel_id", None)
        self.stickers: list = kwargs.pop("stickers", [])
        self.stage_instances: list = kwargs.pop("stage_instances", [])
        self.guild_scheduled_events: list = kwargs.pop("guild_sceduled_events", [])