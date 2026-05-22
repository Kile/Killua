"""Top.gg v1 project API helpers (metrics + announcements)."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiohttp import ClientSession

logger = logging.getLogger(__name__)

TOPGG_METRICS_URL = "https://top.gg/api/v1/projects/@me/metrics"
TOPGG_ANNOUNCEMENTS_URL = "https://top.gg/api/v1/projects/@me/announcements"
TOPGG_TITLE_MIN = 3
TOPGG_TITLE_MAX = 100
TOPGG_CONTENT_MIN = 10
TOPGG_CONTENT_MAX = 2000


def _normalize_token(raw: str) -> str:
    token = raw.strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        token = token[1:-1].strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


def _token() -> str | None:
    value = os.getenv("TOPGG_TOKEN")
    if not value:
        return None
    token = _normalize_token(value)
    return token or None


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _log_auth_failure(method: str, url: str, status: int, body: str) -> None:
    token = _token()
    token_hint = f"length={len(token)}" if token else "unset"
    logger.error(
        "Top.gg %s %s failed (%s): %s (%s)",
        method,
        url,
        status,
        body or "(empty body)",
        token_hint,
    )


async def _request(
    session: ClientSession, method: str, url: str, *, json: dict | None = None
) -> bool:
    token = _token()
    if not token:
        logger.warning("TOPGG_TOKEN is not set; skipping Top.gg %s %s", method, url)
        return False

    try:
        async with session.request(
            method, url, headers=_auth_headers(token), json=json
        ) as resp:
            if resp.status >= 400:
                body = await resp.text()
                _log_auth_failure(method, url, resp.status, body)
                return False
            return True
    except Exception as exc:
        logger.error("Top.gg %s %s error: %s", method, url, exc)
        return False


async def post_metrics(
    session: ClientSession,
    *,
    server_count: int,
    shard_count: int | None = None,
) -> bool:
    """Push guild/shard counts to Top.gg (v1 projects metrics)."""
    payload: dict[str, int] = {"server_count": server_count}
    if shard_count is not None:
        payload["shard_count"] = shard_count
    logger.info(
        "Posting Top.gg metrics: server_count=%s shard_count=%s",
        server_count,
        shard_count,
    )
    return await _request(session, "PATCH", TOPGG_METRICS_URL, json=payload)


async def post_announcement(
    session: ClientSession, *, title: str, content: str
) -> bool:
    """Create a Top.gg project announcement."""
    if len(title) < TOPGG_TITLE_MIN or len(title) > TOPGG_TITLE_MAX:
        logger.warning(
            "Top.gg announcement title length %d is outside %d–%d; skipping",
            len(title),
            TOPGG_TITLE_MIN,
            TOPGG_TITLE_MAX,
        )
        return False
    if len(content) < TOPGG_CONTENT_MIN or len(content) > TOPGG_CONTENT_MAX:
        logger.warning(
            "Top.gg announcement content length %d is outside %d–%d; skipping",
            len(content),
            TOPGG_CONTENT_MIN,
            TOPGG_CONTENT_MAX,
        )
        return False
    return await _request(
        session,
        "POST",
        TOPGG_ANNOUNCEMENTS_URL,
        json={"title": title, "content": content},
    )
