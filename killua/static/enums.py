from enum import Enum

class PrintColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

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
        "description": "Killua's economy with the currency Jenny",
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