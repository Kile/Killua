from .actions import TestingActions
from .cards import TestingCards
from .dev import TestingDev
from .message import TestingMessage

tests = [TestingActions, TestingCards, TestingDev, TestingMessage]

__all__ = ["tests"]
