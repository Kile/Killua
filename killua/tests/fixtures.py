"""Shared fixture reset for the integration test suite."""

from __future__ import annotations

from killua.static.constants import DB
from killua.utils.test_db import TestingDatabase


def reset_test_fixtures() -> None:
    """Reset in-memory DB, user cache, and bot flags between test command classes."""
    TestingDatabase.reset_all()
    DB._test_const_seeded = False

    from killua.utils.classes import User

    User.cache.clear()

    from .types import Bot

    Bot.fail_timeout = False
    Bot.run_in_docker = False
