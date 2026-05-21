"""Build poll/wyr message fixtures and drive Events vote interactions for tests."""

from __future__ import annotations

from typing import Any, List, Optional, Sequence

import discord

from .interaction import MockComponentInteraction
from ..types import Bot


class ListenerFakeButton:
    """Minimal row child for Events vote path (``to_dict``, ``custom_id``)."""

    def __init__(self, *, custom_id: str, label: str, style: int = 1) -> None:
        self.custom_id = custom_id
        self.label = label
        self.style = style

    def to_dict(self) -> dict:
        return {
            "type": 2,
            "style": int(self.style),
            "label": self.label,
            "custom_id": self.custom_id,
        }


class ListenerFakeRow:
    __slots__ = ("children",)

    def __init__(self, children: Sequence[ListenerFakeButton]) -> None:
        self.children = list(children)


def _mention_lines(user_ids: Sequence[int]) -> str:
    return "\n".join(f"<@{uid}>" for uid in user_ids)


def build_poll_message(
    author_id: int,
    *,
    message_id: int = 99001,
    option_index: int = 1,
    option_count: int = 2,
    visible_voter_ids: Optional[Sequence[int]] = None,
    option_button_suffix: str = "",
    close_suffix: str = "",
) -> Any:
    visible_voter_ids = list(visible_voter_ids or [])
    enc_author = Bot._encrypt(author_id, smallest=False)
    sty = int(discord.ButtonStyle.blurple)
    emb = discord.Embed(title="Poll", description="Question?", color=0x3E4A78)
    for pos in range(1, option_count + 1):
        voters = visible_voter_ids if pos == option_index else []
        emb.add_field(
            name=f"{pos}) Option {pos} `[{len(voters)} votes]`",
            value=_mention_lines(voters) if voters else "—",
            inline=False,
        )

    buttons: List[ListenerFakeButton] = []
    for pos in range(1, option_count + 1):
        suffix = option_button_suffix if pos == option_index else ""
        buttons.append(
            ListenerFakeButton(
                custom_id=f"poll:opt-{pos}:{suffix}",
                label=str(pos),
                style=sty,
            )
        )
    buttons.append(
        ListenerFakeButton(
            custom_id=f"poll:close:{enc_author}:{close_suffix}",
            label="Close",
            style=sty,
        )
    )

    class PollMessage:
        id = message_id
        embeds = [emb]
        components = [ListenerFakeRow(buttons)]

    return PollMessage()


def build_wyr_message(
    *,
    message_id: int = 99002,
    side: str = "b",
    visible_voter_ids: Optional[Sequence[int]] = None,
    option_button_suffix: str = "",
) -> Any:
    visible_voter_ids = list(visible_voter_ids or [])
    sty = int(discord.ButtonStyle.blurple)
    emb = discord.Embed(title="Would you rather...", color=0x3E4A78)
    for label, key in (("A", "a"), ("B", "b")):
        voters = visible_voter_ids if key == side else []
        emb.add_field(
            name=f"{label}) choice `[{len(voters)} people]`",
            value=_mention_lines(voters) if voters else "—",
            inline=False,
        )

    suffix_a = option_button_suffix if side == "a" else ""
    suffix_b = option_button_suffix if side == "b" else ""
    row = ListenerFakeRow(
        [
            ListenerFakeButton(
                custom_id=f"wyr:opt-a:{suffix_a}", label="A", style=sty
            ),
            ListenerFakeButton(
                custom_id=f"wyr:opt-b:{suffix_b}", label="B", style=sty
            ),
        ]
    )

    class WyrMessage:
        id = message_id
        embeds = [emb]
        components = [row]

    return WyrMessage()


async def cast_vote(
    events: Any,
    *,
    context: Any,
    message: Any,
    voter: Any,
    custom_id: str,
) -> MockComponentInteraction:
    ix = MockComponentInteraction(
        context=context,
        custom_id=custom_id,
        user=voter,
        message=message,
        client=Bot,
    )
    await events.on_interaction(ix)
    return ix


def option_button_custom_id(message: Any, option_index: int = 1) -> str:
    return message.components[0].children[option_index - 1].custom_id


def encrypted_tail_on_button(custom_id: str, prefix: str) -> str:
    if not custom_id.startswith(prefix):
        return ""
    return custom_id[len(prefix) :]
