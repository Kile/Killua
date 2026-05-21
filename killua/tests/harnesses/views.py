"""Traverse discord.ui views and locate buttons/selects for tests."""

from __future__ import annotations

from typing import Any, Iterator, Optional

import discord


def iter_view_items(view: Any) -> Iterator[Any]:
    """Yield UI components under a View (unwraps ActionRow, recurses LayoutView containers)."""
    if view is None:
        return
    for item in getattr(view, "children", None) or []:
        if isinstance(item, discord.ui.ActionRow):
            for child in item.children:
                yield child
        elif getattr(item, "children", None):
            yield from iter_view_items(item)
        else:
            yield item


def find_button(
    view: Any,
    *,
    custom_id: Optional[str] = None,
    label: Optional[str] = None,
) -> Optional[Any]:
    for item in iter_view_items(view):
        if not isinstance(item, discord.ui.Button):
            continue
        if custom_id is not None and getattr(item, "custom_id", None) != custom_id:
            continue
        if label is not None and getattr(item, "label", None) != label:
            continue
        return item
    return None


def find_select(view: Any, *, custom_id: Optional[str] = None) -> Optional[Any]:
    for item in iter_view_items(view):
        if isinstance(item, discord.ui.Select) and (
            custom_id is None or getattr(item, "custom_id", None) == custom_id
        ):
            return item
    return None
