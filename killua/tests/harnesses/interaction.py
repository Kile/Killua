"""
Minimal interaction-shaped objects for Path B tests (cog `on_interaction` listeners).

`BaseBot.send_message` treats instances with `_killua_test_send_as_interaction` like interactions.
"""

from __future__ import annotations

import discord
from discord import InteractionType
from typing import Any, Optional


class _MockFollowup:
    def __init__(self, owner: "MockComponentInteraction") -> None:
        self._owner = owner

    async def send(self, *args: Any, **kwargs: Any) -> Any:
        await self._owner.context.send(*args, **kwargs)
        return self._owner.context.result.message


class _MockInteractionResponse:
    def __init__(self, owner: "MockComponentInteraction") -> None:
        self._owner = owner
        self._done = False

    def is_done(self) -> bool:
        return self._done

    async def send_message(self, *args: Any, **kwargs: Any) -> Any:
        if self._done:
            raise RuntimeError("Interaction response already done")
        self._done = True
        await self._owner.context.send(*args, **kwargs)
        self._owner._response_message = self._owner.context.result.message
        return self._owner._response_message

    async def edit_message(self, *args: Any, **kwargs: Any) -> None:
        if self._done:
            raise RuntimeError("Interaction response already done")
        self._done = True
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
        self.response = _MockInteractionResponse(self)
        self.followup = _MockFollowup(self)
        self._response_message: Optional[Any] = None
        self.interaction = None

    async def send(self, *args: Any, **kwargs: Any) -> Any:
        return await self.context.send(*args, **kwargs)

    def is_user_integration(self) -> bool:
        return False

    async def original_response(self) -> Any:
        if self._response_message is not None:
            return self._response_message
        return self.message
