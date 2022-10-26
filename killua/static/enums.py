from enum import Enum, auto

class PrintColors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

class Category(Enum):

    ACTIONS = {
        "name": "actions",
        "description": "Commands that can be used to interact with other users, such as hugging them",
        "emoji": {
            "unicode": "\U0001f465",
            "normal": ":busts_in_silhouette:"
        }
    }
    CARDS = {
        "name": "cards",
        "description": "The greed island card system with monster, spell and item cards",
        "emoji": {
            "unicode": "<:card_number_46:811776158966218802>",
            "normal": "<:card_number_46:811776158966218802>"
        }
    }
    ECONOMY = {
        "name": "economy",
        "description": "' economy with the currency Jenny",
        "emoji": {
            "unicode": "\U0001f3c6",
            "normal": ":trophy:"
        } 
    }
    MODERATION = {
        "name": "moderation",
        "description": "Moderation commands",
        "emoji": {
            "unicode": "\U0001f6e0",
            "normal": ":tools:"
        }
    }
    TODO = {
        "name": "todo",
        "description": "Todo lists on discord to help you be organised",
        "emoji": {
            "unicode": "\U0001f4dc",
            "normal": ":scroll:"
        }
    }
    FUN = {
        "name": "fun",
        "description": "Commands to play around with with friends to pass the time",
        "emoji": {
            "unicode": "\U0001f921",
            "normal": ":clown:"
        }
    }
    OTHER = {
        "name": "other",
        "description": "Commands that fit none of the other categories",
        "emoji": {
            "unicode": "<:killua_wink:769919176110112778>",
            "normal": "<:killua_wink:769919176110112778>"
        }
    }

    GAMES = {
        "name": "games",
        "description": "Games you can play with friends or alone",
        "emoji": {
            "unicode": "\U0001f3ae",
            "normal": ":video_game:"
        }
    }

    TAGS = {
        "name": "tags",
        "description": "Tags if you want to save some text. `[PREMIUM ONLY]`",
        "emoji": {
            "unicode": "\U0001f5c4",
            "normal": ":file_cabinet:"
        }
    }

# the values are not important as only Enum.name is used
class Activities(Enum):
    playing = auto()
    watching = auto()
    listening = auto()
    competing = auto()

class Presences(Enum):
    dnd = auto()
    idle = auto()
    online = auto()

class HuntOptions(Enum):
    end = auto()
    time = auto()
    start = auto()

class Items(Enum):
    jenny = auto()
    card = auto()
    lootbox = auto()

class SellOptions(Enum):
    all = auto()
    spells = auto()
    monsters = auto()

class TriviaDifficulties(Enum):
    easy = auto()
    medium = auto()
    hard = auto()

class CountDifficulties(Enum):
    easy = auto()
    hard = auto()

class TodoStatus(Enum):
    public = auto()
    private = auto()

class TodoDeleteWhenDone(Enum):
    yes = auto()
    no = auto()

class TodoPermissions(Enum):
    viewer = auto()
    editor = auto()

class TodoAddons(Enum):
    thumbnail = auto()
    space = auto()
    color = auto()
    description = auto()
    timing = auto()

# class FlagOptions(Enum):
#     asexual = auto()
#     aromantic = auto()
#     bisexual = auto()
#     pansexual = auto()
#     gay = auto()
#     lesbian = auto()
#     trans = auto()
#     nonbinary = auto()
#     genderfluid = auto()
#     genderqeeur = auto()
#     polysexual = auto()
#     austria = auto()
#     belguim = auto()
#     botswana = auto()
#     bulgaria = auto()
#     ivory = auto()
#     estonia = auto()
#     france = auto()
#     gabon = auto()
#     gambia = auto()
#     germany = auto()
#     guinea = auto()
#     hungary = auto()
#     indonesia = auto()
#     ireland = auto()
#     italy = auto()
#     luxembourg = auto()
#     monaco = auto()
#     nigeria = auto()
#     poland = auto()
#     russia = auto()
#     romania = auto()
#     sierraleone = auto()
#     thailand = auto()
#     ukraine = auto()
#     yemen = auto()

class SnapOptions(Enum):
    dog = auto()
    dog2 = auto()
    dog3 = auto()
    pig = auto()
    flowers = auto()
    random = auto()

class EyesOptions(Enum):
    big = auto()
    black = auto()
    bloodshot = auto()
    blue = auto()
    default = auto()
    googly = auto()
    green = auto()
    horror = auto()
    illuminati = auto()
    money = auto()
    pink = auto()
    red = auto()
    small = auto()
    spinner = auto()
    spongebob = auto()
    white = auto()
    yellow = auto()
    random = auto()

class PremiumGuildOptions(Enum):
    add = auto()
    remove = auto()

class StatsOptions(Enum):
    usage = auto()
    growth = auto()

class GameOptions(Enum):
    rps = auto()
    counting = auto()
    trivia = auto()