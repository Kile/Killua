from .actions import TestingActions
from .api import TestingApi
from .bot_cov import TestingBotCov
from .cards import TestingCards
from .deep_coverage import TestingDeep
from .dev import TestingDev
from .economy import TestingEconomy
from .events import TestingEvents
from .games import TestingGames
from .help import TestingHelp
from .image_manipulation import TestingImageManipulation
from .moderation import TestingModeration
from .premium import TestingPremium
from .prometheus_cov import TestingPrometheus
from .shop import TestingShop
from .small_commands import TestingSmallCommands
from .tags import TestingTags
from .todo import TestingTodo
from .unit_boost import TestingUnitBoost
from .web_scraping import TestingWebScraping

tests = [
    TestingActions,
    TestingApi,
    TestingBotCov,
    TestingCards,
    TestingDeep,
    TestingDev,
    TestingEconomy,
    TestingEvents,
    TestingGames,
    TestingHelp,
    TestingImageManipulation,
    TestingModeration,
    TestingPremium,
    TestingPrometheus,
    TestingShop,
    TestingSmallCommands,
    TestingTags,
    TestingTodo,
    TestingUnitBoost,
    TestingWebScraping,
]

__all__ = ["tests"]
