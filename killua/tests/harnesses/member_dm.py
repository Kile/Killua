"""Wire Member.send so DM views (e.g. RPS select) complete via real view.wait paths."""

from __future__ import annotations

from typing import Any

from killua.cogs.games import RpsSelect
from killua.utils.interactions import Select as KSelect

from ..types import ArgumentInteraction, Message


def _find_rps_select(view: Any) -> Any | None:
    for child in getattr(view, "children", []) or []:
        if isinstance(child, RpsSelect):
            return child
    return None


async def patch_member_rps_select(
    member: Any,
    ctx: Any,
    *,
    choice: int = 0,
) -> None:
    """
    Patch ``member.send`` so ``_wait_for_dm_response`` receives real views with
    ``value`` set by ``RpsSelect.callback`` (paper=0, rock=-1, scissors=1).
    """

    async def patched_send(*args, **kwargs):
        view = kwargs.get("view")
        content = kwargs.get("content")
        embed = kwargs.get("embed")
        msg = Message(
            author=member,
            channel=ctx.channel,
            content=content or "",
            embed=embed,
        )
        msg.ctx = ctx
        if view is not None:
            view.user = member

            async def patched_wait():
                select = _find_rps_select(view)
                if select is not None:
                    ix = ArgumentInteraction(
                        ctx,
                        user=member,
                        message=msg,
                        data={"values": [str(choice)]},
                    )
                    await select.callback(ix)

            view.wait = patched_wait

        return msg

    member.send = patched_send


async def patch_member_trivia_select(
    member: Any,
    ctx: Any,
    *,
    choice_index: int = 0,
) -> None:
    """
    Patch ``member.send`` so trivia multiplayer ``_wait_for_dm_response`` completes
    via real ``Select.callback`` (option index in the shuffled list).
    """

    async def patched_send(*args, **kwargs):
        view = kwargs.get("view")
        content = kwargs.get("content")
        embed = kwargs.get("embed")
        msg = Message(
            author=member,
            channel=ctx.channel,
            content=content or "",
            embed=embed,
        )
        msg.ctx = ctx
        if view is not None:
            view.user = member

            async def patched_wait():
                for child in getattr(view, "children", []) or []:
                    if isinstance(child, KSelect):
                        ix = ArgumentInteraction(
                            ctx,
                            user=member,
                            message=msg,
                            data={"values": [str(choice_index)]},
                        )
                        await child.callback(ix)
                        break

            view.wait = patched_wait

        return msg

    member.send = patched_send
