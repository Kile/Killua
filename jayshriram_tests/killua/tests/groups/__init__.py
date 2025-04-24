from .actions import TestingActions
from .cards import TestingCards
from .dev import TestingDev

tests = [TestingActions, TestingCards, TestingDev]

__all__ = ["tests"]