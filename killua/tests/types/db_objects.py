from ...utils.classes import User, Guild, TodoList, Todo, PartialCard, DB

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...static.cards import Card

    class TestingCard(Card):
        """A class to construct a testing card. This is needed to be added because it needs to use a testing database instead of a real one."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

    from ...__init__ import should_run_tests

    from .db import TestingDatabase as Database

    if should_run_tests():
        # This should only be overwritten if the tests are being run
        DB.teams = Database("teams")
        DB.items = Database("items")
        DB.guilds = Database("guilds")

class TestingUser(User):
    """A class to construct a testing user. This is needed to be added because it needs to use a testing database instead of a real one."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the cache of the users."""
        cls.cache = {}

class TestingGuild(Guild):
    """A class to construct a testing guild. This is needed to be added because it needs to use a testing database instead of a real one."""

    def __init__(self, guild_id: int, *args, **kwargs):
        super().__init__(guild_id, *args, **kwargs)

class TestingTodoList(TodoList):
    """A class to construct a testing todo list. This is needed to be added because it needs to use a testing database instead of a real one."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class TestingTodo(Todo):
    """A class to construct a testing todo. This is needed to be added because it needs to use a testing database instead of a real one."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class TestingPartialCard(PartialCard):
    """A class to construct a testing partial card. This is needed to be added because it needs to use a testing database instead of a real one."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)