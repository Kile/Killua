"""Helpers for ConfirmButton / LayoutView flows sent via User.send (DM)."""

from __future__ import annotations

from typing import Any

from ..types import ArgumentInteraction, Message


def _find_button(item: Any, custom_id: str) -> Any | None:
    if getattr(item, "custom_id", None) == custom_id:
        return item
    for child in getattr(item, "children", []) or []:
        found = _find_button(child, custom_id)
        if found:
            return found
    return None


async def patch_user_confirm_dm(
    user: Any,
    ctx: Any,
    *,
    invitee: Any = None,
    confirm: bool = True,
) -> None:
    """
    Patch ``user.send`` so ``ConfirmButton.wait`` auto-presses confirm or cancel.

    The invitee must match ``ConfirmButton.user_id`` (the DM recipient).
    """
    actor = invitee if invitee is not None else user

    async def patched_send(*args, **kwargs):
        view = kwargs.get("view")
        content = kwargs.get("content")
        msg = Message(author=actor, channel=ctx.channel, content=content or "")
        msg.ctx = ctx
        if view is not None:

            async def patched_wait():
                ix = ArgumentInteraction(ctx, user=actor, message=msg)
                which = "confirm" if confirm else "cancel"
                button = _find_button(view, which)
                if button:
                    await button.callback(ix)

            view.wait = patched_wait
        return msg

    user.send = patched_send
