"""Shared fixture reset for the integration test suite."""

from __future__ import annotations

import json
from pathlib import Path

from killua.static.constants import DB
from killua.utils.test_db import TestingDatabase

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CARDS_FILE = _REPO_ROOT / "cards.json"


def ensure_test_cards() -> None:
    """Load Card.raw from cards.json (run ``python -m killua --download public`` first)."""
    from killua.utils.classes.card import Card

    if Card.raw:
        return

    if not _CARDS_FILE.exists():
        raise FileNotFoundError(
            f"{_CARDS_FILE} not found. Download cards with: "
            "python -m killua --download public"
        )

    with _CARDS_FILE.open() as handle:
        Card.raw = json.load(handle)

    Card.cached_raw = []
    Card.cache.clear()


def reset_test_fixtures() -> None:
    """Reset in-memory DB, user cache, and bot flags between test command classes."""
    TestingDatabase.reset_all()
    DB._test_const_seeded = False

    from killua.utils.classes import User

    User.cache.clear()

    from .types import Bot

    Bot.fail_timeout = False
    Bot.run_in_docker = False
