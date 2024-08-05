from .bot import BOT as Bot
from .channel import TestingTextChannel as TextChannel
from .context import TestingContext as Context
from .member import TestingMember as DiscordMember
from .message import TestingMessage as Message
from .permissions import Permission, PermissionOverwrite, Permissions
from .role import TestingRole as Role
from .user import TestingUser as DiscordUser
from .guild import TestingGuild as DiscordGuild
from .interaction import TestingInteraction as Interaction
from .interaction import ArgumentInteraction, ArgumentResponseInteraction

# from .db import TestingDatabase as Database
# from .db_objects import TestingUser as User
# from .db_objects import TestingGuild as Guild
# from .db_objects import TestingTodo as Todo
# from .db_objects import TestingTodoList as TodoList
# from .db_objects import TestingCard as Card
from .testing_results import TestResult, Result, ResultData
from .utils import random_date, get_random_discord_id, random_name
from typing import TYPE_CHECKING

__all__ = [
    "Bot",
    "TextChannel",
    "Context",
    "DiscordMember",
    "Message",
    "Permission",
    "PermissionOverwrite",
    "Permissions",
    "Role",
    "DiscordUser",
    "DiscordGuild",
    # "Database",
    # "User",
    # "Guild",
    "Interaction",
    "ArgumentInteraction",
    "ArgumentResponseInteraction",
    # "Todo",
    # "TodoList",
    # "Card",
    "TestResult",
    "Result",
    "ResultData",
    "random_date",
    "get_random_discord_id",
    "random_name",
]

if TYPE_CHECKING:
    from .db_objects import TestingCard as Card

    __all__.append("Card")
