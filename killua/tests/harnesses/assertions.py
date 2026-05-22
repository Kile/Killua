"""Shared assertion helpers for integration tests."""

from __future__ import annotations

from typing import Any, Sequence

from killua.utils.classes import User


def last_content(ctx: Any) -> str:
    if not ctx.result or not ctx.result.message:
        return ""
    return ctx.result.message.content or ""


def embed_at(ctx: Any, index: int = -1) -> Any | None:
    raw = ctx.result.message.embeds if ctx.result else None
    if raw is None:
        return None
    if isinstance(raw, list) and raw:
        return raw[index]
    if isinstance(raw, tuple) and raw:
        inner = raw[0]
        if isinstance(inner, list) and inner:
            return inner[index]
    return None


def assert_content_contains(ctx: Any, needle: str, *, msg: str | None = None) -> None:
    content = last_content(ctx)
    assert needle in content, msg or f"expected {needle!r} in {content!r}"


def assert_content_equals(ctx: Any, expected: str) -> None:
    assert last_content(ctx) == expected, (
        f"expected {expected!r}, got {last_content(ctx)!r}"
    )


def assert_embed_title(emb: Any, substring: str) -> None:
    title = (emb.title or "") if emb else ""
    assert substring in title, f"expected {substring!r} in embed title {title!r}"


async def reload_user(user_id: int) -> User:
    User.cache.pop(user_id, None)
    return await User.new(user_id)


async def assert_inventory(
    user_id: int,
    *,
    has: Sequence[int] = (),
    lacks: Sequence[int] = (),
    count: dict[int, int] | None = None,
) -> User:
    user = await reload_user(user_id)
    for cid in has:
        assert user.has_any_card(cid), f"user {user_id} should have card {cid}"
    for cid in lacks:
        assert not user.has_any_card(cid), f"user {user_id} should lack card {cid}"
    if count:
        for cid, n in count.items():
            assert user.count_card(cid, including_fakes=False) == n, (
                f"user {user_id} card {cid}: expected count {n}, "
                f"got {user.count_card(cid, including_fakes=False)}"
            )
    return user
