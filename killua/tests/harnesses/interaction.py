"""
Minimal interaction-shaped objects for Path B tests (cog `on_interaction` listeners).

`BaseBot.send_message` treats instances with `_killua_test_send_as_interaction` like interactions.
"""

from __future__ import annotations

from discord import InteractionType
from typing import Any

from ..types.interaction import InteractionResponded, StrictInteractionResponse


class MockFollowup:
    def __init__(self, owner: Any) -> None:
        self._owner = owner

    async def send(self, *args: Any, **kwargs: Any) -> Any:
        await self._owner.context.send(*args, **kwargs)
        return self._owner.context.result.message


class MockInteractionResponse(StrictInteractionResponse):
    async def send_message(self, *args: Any, **kwargs: Any) -> Any:
        self._mark_responded("send_message")
        await self._owner.context.send(*args, **kwargs)
        self._owner._response_message = self._owner.context.result.message
        return self._owner._response_message

    async def edit_message(self, *args: Any, **kwargs: Any) -> None:
        self._mark_responded("edit_message")
        msg = self._owner.message
        embed = kwargs.get("embed")
        view = kwargs.get("view")
        if msg is None:
            return
        if embed is not None and hasattr(msg, "embeds"):
            msg.embeds = [embed]
        if view is not None and hasattr(msg, "components"):
            msg.components = [
                type("_Row", (), {"children": list(view.children)})()
            ]

    async def send_modal(self, *args: Any, **kwargs: Any) -> None:
        self._mark_responded("send_modal")
        await self._owner.context.send_modal(*args, **kwargs)


class MockCommandInteraction:
    """Slash/context-menu interaction attached to a command TestingContext."""

    def __init__(self, context: Any) -> None:
        self.context = context
        self.channel = context.channel
        self.user = context.author
        self.message = getattr(context, "message", None)
        self.response = MockInteractionResponse(self)
        self.followup = MockFollowup(self)
        self._response_message: Any | None = None

    async def original_response(self) -> Any:
        if self._response_message is not None:
            return self._response_message
        return self.message


def attach_command_interaction(context: Any) -> MockCommandInteraction:
    """Attach a tracked interaction to *context* (for slash/context-menu command tests)."""
    interaction = MockCommandInteraction(context)
    context.interaction = interaction
    return interaction


async def invoke_interaction_command(
    cog: Any,
    command: Any,
    context: Any,
    *args: Any,
    **kwargs: Any,
) -> MockCommandInteraction:
    """Run *command* as a deferred slash interaction (mirrors global before_invoke defer)."""
    from ..types import Bot

    interaction = attach_command_interaction(context)
    if command is not None and not command.extras.get("no_interaction_defer"):
        await Bot._defer_interaction_command(context)
    await command(cog, context, *args, **kwargs)
    return interaction


class MockComponentInteraction:
    """Component interaction with `context`, `data`, `user`, `message` for cog listeners."""

    _killua_test_send_as_interaction = True

    def __init__(
        self,
        *,
        context: Any,
        custom_id: str,
        user: Any,
        message: Any,
        client: Any,
    ) -> None:
        self.type = InteractionType.component
        self.data: dict = {"custom_id": custom_id}
        self.context = context
        self.user = user
        self.author = user
        self.command = getattr(context, "command", None)
        self.message = message
        self.client = client
        self.channel = context.channel
        self.guild_id = getattr(context.guild, "id", None)
        self.response = MockInteractionResponse(self)
        self.followup = MockFollowup(self)
        self._response_message: Any | None = None
        self.interaction = None

    async def send(self, *args: Any, **kwargs: Any) -> Any:
        return await self.context.send(*args, **kwargs)

    def is_user_integration(self) -> bool:
        return False

    async def original_response(self) -> Any:
        if self._response_message is not None:
            return self._response_message
        return self.message


__all__ = [
    "InteractionResponded",
    "MockCommandInteraction",
    "MockComponentInteraction",
    "MockFollowup",
    "MockInteractionResponse",
    "attach_command_interaction",
    "invoke_interaction_command",
]
