"""Helpers to drive killua.utils.paginator.Buttons in tests."""

from __future__ import annotations

import re
from typing import Any, Optional, Tuple

import discord

from ..types import ArgumentInteraction
from .views import find_button


def embed_footer_page(embed: discord.Embed) -> Optional[Tuple[int, int]]:
    """Parse 'Page n/m' from DefaultEmbed footer. Returns (page, max) or None."""
    foot = (embed.footer and embed.footer.text) or ""
    m = re.search(r"Page\s+(\d+)/(\d+)", foot)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


async def press_paginator_button(
    view: Any,
    custom_id: str,
    *,
    context: Any,
    message: Optional[Any] = None,
    user: Optional[Any] = None,
) -> None:
    """Invoke a Paginator Buttons callback (custom_id: first, previous, next, last, delete)."""
    btn = find_button(view, custom_id=custom_id)
    assert btn is not None, f"no button custom_id={custom_id!r} on view"
    msg = message or (context.result.message if context.result else None)
    assert msg is not None, "paginator needs a message on context.result"
    inter = ArgumentInteraction(context, user=user or context.author, message=msg)
    await btn.callback(inter)
