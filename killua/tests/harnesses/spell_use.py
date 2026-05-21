"""Helpers for per-spell ``cards use`` integration tests."""

from __future__ import annotations

import math
from contextlib import contextmanager
from typing import Any, Optional, Sequence, Tuple, Union
from unittest.mock import patch

from killua.utils.interactions import Select as KSelect
from killua.utils.classes import User
from killua.utils.classes.card import Card
from killua.static.constants import DEF_SPELLS, VIEW_DEF_SPELLS
from killua.utils.paginator import Buttons

from ..types import ArgumentInteraction, DiscordMember
from .assertions import (
    assert_content_contains,
    assert_inventory,
    embed_at,
    last_content,
    reload_user,
)

SPELL_IDS_WITH_EXEC = [
    1001, 1002, 1007, 1008, 1010, 1011, 1015, 1018, 1020, 1021, 1024, 1026,
    1028, 1029, 1031, 1032, 1035, 1036, 1038,
]
DEFENSE_SPELL_IDS = list(DEF_SPELLS) + list(VIEW_DEF_SPELLS)
DEFAULT_ATTACK_SPELL = 1021
STEAL_TARGET_CARD = 50
MET_ERROR_FRAGMENT = "haven't met this user yet"
DEFENSE_SUCCESS_FRAGMENT = "successfully defended"
ATTACK_TIMEOUT_FRAGMENT = "attack goes through"


async def setup_author_spell(
    author_id: int,
    spell_id: int,
    *,
    extra_fs: Optional[Sequence[int]] = None,
    met_ids: Optional[Sequence[int]] = None,
) -> User:
    user = await User.new(author_id)
    await user.nuke_cards("all")
    await user.add_card(spell_id)
    for cid in extra_fs or []:
        await user.add_card(cid)
    for mid in met_ids or []:
        await user.add_met_user(mid)
    return user


async def setup_target_user(
    target_id: int,
    *,
    fs_cards: Optional[Sequence] = None,
    rs_cards: Optional[Sequence] = None,
    defense_ids: Optional[Sequence[int]] = None,
    effects: Optional[dict] = None,
    met_attacker: bool = True,
    attacker_id: Optional[int] = None,
) -> User:
    user = await User.new(target_id)
    await user.nuke_cards("all")

    async def _add_slot(cid, *, fake=False, clone=False):
        await user.add_card(int(cid), fake=bool(fake), clone=bool(clone))

    for cid in fs_cards or []:
        fake, clone = False, False
        if isinstance(cid, tuple):
            cid, fake, clone = cid[0], cid[1], cid[2] if len(cid) > 2 else False
        await _add_slot(cid, fake=fake, clone=clone)
    for cid in rs_cards or []:
        fake, clone = False, False
        if isinstance(cid, tuple):
            cid, fake, clone = cid[0], cid[1], cid[2] if len(cid) > 2 else False
        else:
            cid = int(cid)
        await _add_slot(cid, fake=fake, clone=clone)
    for did in defense_ids or []:
        if not user.has_any_card(did):
            await user.add_card(did)
    if effects:
        for key, val in effects.items():
            await user.add_effect(key, val)
    if met_attacker and attacker_id is not None:
        await user.add_met_user(attacker_id)
    return user


def ensure_no_defense(user: User) -> None:
    for did in DEF_SPELLS + VIEW_DEF_SPELLS:
        assert not user.has_any_card(did), f"target still has defense card {did}"
    assert not user.has_effect("1026")[0], "target has 1026 protection active"


def _is_member_target(target: Any) -> bool:
    return target is not None and hasattr(target, "id") and hasattr(target, "display_name")


async def invoke_use(
    testing: Any,
    card_id: Union[int, str],
    *,
    target: Any = None,
    args: Any = None,
) -> None:
    item = str(card_id)
    cog, ctx = testing.cog, testing.base_context
    if target is None and args is None:
        await testing.command(cog, ctx, item)
    elif args is None:
        if _is_member_target(target):
            await testing.command(cog, ctx, item, target)
        else:
            await testing.command(cog, ctx, item, target=target)
    elif _is_member_target(target):
        await testing.command(cog, ctx, item, target, args=args)
    else:
        await testing.command(cog, ctx, item, target=target, args=args)


def make_target_member(testing: Any, target_id: int) -> DiscordMember:
    member = DiscordMember(
        id=target_id,
        username=f"Target{target_id}",
        mutual_guilds=[object()],
    )
    testing.base_guild.members = [testing.base_author, member]
    return member


def target_member(testing: Any, offset: int) -> Tuple[DiscordMember, int]:
    target_id = testing.base_author.id + offset
    return make_target_member(testing, target_id), target_id


async def setup_met_view_spell(
    testing: Any,
    spell_id: int,
    offset: int,
    *,
    fs_cards: Optional[Sequence] = None,
) -> Tuple[DiscordMember, int]:
    member, target_id = target_member(testing, offset)
    await setup_author_spell(
        testing.base_author.id, spell_id, met_ids=[target_id]
    )
    await setup_target_user(target_id, fs_cards=fs_cards or [1011])
    return member, target_id


async def use_view_spell_paginator(
    testing: Any,
    spell_id: int,
    target: DiscordMember,
) -> None:
    testing.base_context.timeout_view = True
    await invoke_use(testing, spell_id, target=target)
    assert isinstance(testing.base_context.current_view, Buttons)


def assert_met_error(ctx: Any) -> None:
    assert MET_ERROR_FRAGMENT in last_content(ctx).lower()


async def assert_steal_succeeded(
    ctx: Any,
    author_id: int,
    target_id: int,
    card_id: int,
    *,
    message_fragment: str = "stole",
) -> None:
    assert_content_contains(ctx, message_fragment)
    await assert_inventory(author_id, has=[card_id])
    await assert_inventory(target_id, lacks=[card_id])


async def assert_steal_blocked_by_defense(
    ctx: Any,
    author_id: int,
    target_id: int,
    card_id: int,
) -> None:
    assert_content_contains(ctx, DEFENSE_SUCCESS_FRAGMENT)
    await assert_inventory(target_id, has=[card_id])
    await assert_inventory(author_id, lacks=[card_id])


async def respond_defense_with_spell(ctx: Any, spell_id: int) -> None:
    view = ctx.current_view
    if view is None:
        return
    for child in view.children:
        if isinstance(child, KSelect):
            await child.callback(
                ArgumentInteraction(
                    ctx,
                    user=getattr(ctx.current_view, "user_id", ctx.author),
                    data={"values": [str(spell_id)]},
                )
            )
            break
    if view is not None:
        view.stop()


@contextmanager
def patch_random_choice(return_value: Any):
    with patch("killua.static.cards.random.choice", return_value=return_value):
        yield


def seed_channel_history(ctx: Any, authors: Sequence[Any]):
    class _HistMsg:
        def __init__(self, author: Any):
            self.author = author

    messages = [_HistMsg(a) for a in authors]

    async def _history(limit=20):
        for m in messages[:limit]:
            yield m

    return patch.object(ctx.channel, "history", _history)


async def run_attack_against_defender(
    testing: Any,
    *,
    defense_id: int,
    attacker_spell: int = DEFAULT_ATTACK_SPELL,
    stolen_card: int = STEAL_TARGET_CARD,
    use_defense: bool = True,
    attacker_in_met: bool = True,
    patch_attacker_range: Optional[str] = None,
) -> Tuple[DiscordMember, int]:
    target_id = testing.base_author.id + 50_000
    target_member_obj = make_target_member(testing, target_id)
    await setup_author_spell(
        testing.base_author.id,
        attacker_spell,
        met_ids=[target_id] if attacker_in_met else [],
    )
    await setup_target_user(
        target_id,
        rs_cards=[(stolen_card, False, False)],
        defense_ids=[defense_id] if defense_id in DEF_SPELLS else None,
        fs_cards=[(defense_id, False, False)] if defense_id in VIEW_DEF_SPELLS else None,
        met_attacker=attacker_in_met,
        attacker_id=testing.base_author.id,
    )

    prev_rtv = testing.base_context.respond_to_view
    if use_defense:

        async def _def(ctx):
            await respond_defense_with_spell(ctx, defense_id)

        testing.base_context.respond_to_view = _def
    else:
        testing.base_context.respond_to_view = prev_rtv

    patches = []
    if patch_attacker_range is not None:
        original_init = Card.__init__

        def _patched_init(self, name_or_id, *a, **kw):
            original_init(self, name_or_id, *a, **kw)
            if getattr(self, "id", None) == attacker_spell:
                self.range = patch_attacker_range

        patches.append(patch.object(Card, "__init__", _patched_init))

    try:
        for p in patches:
            p.start()
        await invoke_use(
            testing,
            attacker_spell,
            target=target_member_obj,
            args=stolen_card,
        )
    finally:
        for p in patches:
            p.stop()
        testing.base_context.respond_to_view = prev_rtv
    return target_member_obj, target_id


# Back-compat aliases
embed0 = embed_at
