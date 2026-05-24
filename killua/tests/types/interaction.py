from __future__ import annotations

from discord import Interaction
from discord.ext.commands import Context

from typing import Literal, Any
from .utils import get_random_discord_id, random_name


class InteractionResponded(Exception):
    """Raised when a mock interaction response is used more than once (mirrors discord.py)."""


class StrictInteractionResponse:
    """Single-use interaction response mock; errors on a second defer or initial response."""

    def __init__(self, owner: Any) -> None:
        self._owner = owner
        self._done = False
        self._deferred = False

    @property
    def deferred(self) -> bool:
        return self._deferred

    def is_done(self) -> bool:
        return self._done

    def _mark_responded(self, action: str, *, deferred: bool = False) -> None:
        if self._done:
            raise InteractionResponded(
                f"This interaction has already been responded to; cannot {action}."
            )
        self._done = True
        if deferred:
            self._deferred = True

    async def defer(self, *args: Any, **kwargs: Any) -> None:
        self._mark_responded("defer", deferred=True)


class ArgumentResponseInteraction(StrictInteractionResponse):
    def __init__(self, interaction: ArgumentInteraction) -> None:
        super().__init__(interaction)

    @property
    def interaction(self) -> ArgumentInteraction:
        return self._owner

    async def send_message(self, *args, **kwargs) -> None:
        self._mark_responded("send_message")
        view = kwargs.pop(
            "view", self.interaction.context.current_view
        )  # If no new view is responded we want the old one still as the current view
        await self.interaction.context.send(view=view, *args, **kwargs)

    async def edit_message(self, *args, **kwargs) -> None:
        self._mark_responded("edit_message")
        msg = getattr(self.interaction, "message", None)
        if msg is not None and hasattr(msg, "edit"):
            await msg.edit(*args, **kwargs)

    async def send_modal(self, *args, **kwargs) -> None:
        self._mark_responded("send_modal")
        await self.interaction.context.send_modal(*args, **kwargs)


class ArgumentInteraction:
    """Supplied to View item callbacks (buttons/selects). Optional user/message match Discord interaction shape."""

    def __init__(
        self,
        context: Context,
        *,
        user: Any = None,
        message: Any = None,
        **kwargs: Any,
    ) -> None:
        self.context = context
        self.user = user if user is not None else context.author
        if message is not None:
            self.message = message
        elif context.result is not None and getattr(context.result, "message", None):
            self.message = context.result.message
        else:
            self.message = None
        self.data = kwargs.pop("data", {})
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.response = ArgumentResponseInteraction(self)


class TestingInteraction(Interaction):
    """A testing class mocking an interaction class"""

    @classmethod
    def base_interaction(cls, **kwargs) -> dict:
        return {
            "id": kwargs.pop("id", get_random_discord_id()),
            "application_id": kwargs.pop("application_id", get_random_discord_id()),
            "token": kwargs.pop("token", ""),
            "version": 1,
        }

    @classmethod
    def context_menus_interaction(
        cls, type: Literal[2, 4], menu_type: Literal[2, 3], *kwargs
    ) -> TestingInteraction:
        """Creates a testing interaction for the app command"""
        base = cls.base_interaction(**kwargs)
        base["type"] = type
        base["data"] = {
            "type": menu_type,  # User: 2, Message: 3
            "target": kwargs.pop("target", get_random_discord_id()),
            "id": kwargs.pop("data_id", get_random_discord_id()),
            "name": kwargs.pop("name", random_name()),
            "guild_id": kwargs.pop("guild_id", get_random_discord_id()),
        }
        return TestingInteraction(**base)

    @classmethod
    def app_command_interaction(
        cls, type: Literal[2, 4], **kwargs
    ) -> TestingInteraction:
        """Creates a testing interaction for the app command"""
        base = cls.base_interaction(**kwargs)
        base["type"] = type
        base["data"] = {
            "type": 1,
            "id": kwargs.pop("data_id", get_random_discord_id()),
            "name": kwargs.pop("name", random_name()),
        }
        return TestingInteraction(**base)

    @classmethod
    def button_interaction(cls, **kwargs) -> TestingInteraction:
        """Creates a testing interaction for the button message component"""
        base = cls.base_interaction(**kwargs)
        base["type"] = 3
        base["data"] = {
            "component_type": 2,
            "custom_id": kwargs.pop("custom_id", get_random_discord_id()),
        }
        return TestingInteraction(**base)

    @classmethod
    def select_interaction(cls, **kwargs) -> TestingInteraction:
        """Creates a testing interaction for the select message component"""
        base = cls.base_interaction(**kwargs)
        base["type"] = 3
        base["data"] = {
            "component_type": 3,
            "values": kwargs.pop("values", []),
            "custom_id": kwargs.pop("custom_id", get_random_discord_id()),
        }
        return TestingInteraction(**base)

    @classmethod
    def modal_interaction(cls, **kwargs) -> TestingInteraction:
        """Creates a testing interaction for the modal message component"""
        base = cls.base_interaction(**kwargs)
        base["type"] = 5
        base["data"] = {
            "custom_id": kwargs.pop("custom_id", get_random_discord_id()),
            "components": kwargs.pop("components", []),
        }
        # Components are in the structure either:
        # {
        #     "type": 1,
        #     "components": [
        #         {
        #             "type": 4,
        #             "custom_id": str,
        #             "value": str
        #         }
        #     ]
        # }
        # Or just
        # {
        #     "type": 4,
        #     "custom_id": str,
        #     "value": str
        # }
        # Source: https://github.com/Rapptz/discord.py/blob/b0cb458f9f76072db3d9e40a33b70ce5349b0235/discord/types/interactions.py#L184
        return TestingInteraction(**base)
