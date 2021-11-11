from __future__ import annotations
"""
This file comtains classes that are not specific to one group and are used across several files
"""

import io
import aiohttp
import pathlib
import random
import discord

from enum import Enum
from discord.ext import commands
from datetime import datetime, timedelta
from PIL import Image, ImageFont, ImageDraw
from typing import Union, Tuple, List, Any, Optional

from .paginator import View
from killua.static.constants import FREE_SLOTS, teams, items, guilds, todo, PATREON_TIERS, LOOTBOXES, PREMIUM_ALIASES, DEF_SPELLS

class NotInPossesion(Exception):
    pass

class CardLimitReached(Exception):
    pass

class TodoListNotFound(Exception):
    pass

class CardNotFound(Exception):
    pass

class NoMatches(Exception):
    pass

class CheckFailure(Exception):
    def __init__(self, message:str, **kwargs):
        self.message = message
        super().__init__(**kwargs)

class SuccessfullDefense(CheckFailure):
    pass

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

class PartialCard:
    """A class preventing a circular import by providing the bare minimum of methods and properties. Only used in this file"""
    def __init__(self, card_id:int):
        card = items.find_one({'_id': card_id})
        if card is None:
            raise CardNotFound
        
        self.id:int = card['_id']
        self.image_url:str = card["Image"]
        self.owners:list = card['owners']
        self.emoji:str = card['emoji']
        self.limit:int = card['limit']
        try:
            self.type:str = card['type']
        except KeyError:
            items.update_one({'_id': self.id}, {'$set':{'type': 'normal'}})
            self.type = 'normal'

    def add_owner(self, user_id:int):
        """Adds an owner to a card entry in my db. Only used in User().add_card()"""
        self.owners.append(user_id)
        items.update_one({'_id': self.id}, {'$push': {'owners': user_id}})
        return

    def remove_owner(self, user_id:int):
        """Removes an owner from a card entry in my db. Only used in User().remove_card()"""
        self.owners.remove(user_id)
        items.update_one({'_id': self.id}, {'$set': {'owners': self.owners}})
        return

class _LootBoxButton(discord.ui.Button):
    """A class used for lootbox buttons"""
    def __init__(self, index:int, rewards:List[Union[PartialCard, int, None]],**kwargs):
        super().__init__(**kwargs)
        self.index = index
        if self.index != 24:
            self.reward = rewards[self.index]
            self.has_reward = not not self.reward

    def _create_view(self) -> View:
        """Creates a new view after the callback depending on if this button has a reward"""
        for c in self.view.children:
            if c.index == self.index and not c.index == 24:
                c.disabled=True
                c.label=("" if isinstance(self.reward, PartialCard) else str(self.reward)) if self.has_reward else ""
                c.style=discord.ButtonStyle.success if self.has_reward else discord.ButtonStyle.red
                c.emoji=(self.reward.emoji if isinstance(self.reward, PartialCard) else None) if self.has_reward else "\U0001f4a3"
            elif c.index == 24:
                c.disabled = not self.has_reward
            else:
                c.disabled=c.disabled if self.has_reward else True
                c.label=(("" if isinstance(c.reward, PartialCard) else str(c.reward)) if c.has_reward else "") if not self.has_reward else c.label
                c.emoji=((c.reward.emoji if isinstance(c.reward, PartialCard) else None) if c.has_reward else "\U0001f4a3") if not self.has_reward else c.emoji
            
        return self.view

    async def _respond(self, correct:bool, last:bool, view:View, interaction:discord.Interaction) -> discord.Message:
        """Responds with the new view"""
        if correct and last:
            return await interaction.response.edit_message(content="Congrats, you move on to the next level!", view=view)
        if not correct:
            return await interaction.response.edit_message(content="Oh no! This was not the right order! Better luck next time", view=view)
        if not last:
            return await interaction.response.edit_message(content="Can you remember?", view=view)

    def _format_rewards(self) -> str:
        """Creates a readable string from rewards"""
        jenny = 0
        for rew in self.view.claimed:
            if isinstance(rew, int):
                jenny += rew

        rewards = ("cards " + ", ".join(cards)+(" and " if jenny > 0 else "") if len(cards:= [c.emoji for c in self.view.claimed if isinstance(c, PartialCard)]) > 0 else "") + (str(jenny) + " jenny" if jenny > 0 else "")
        return rewards

    async def _end_button(self, interaction: discord.Interaction) -> Union[None, discord.Message]:
        """Handles the "save" button"""
        if len(self.view.claimed) == 0: # User cannot click save not having clicked any button yet
            return await interaction.response.send_message(content="You can't save with no rewards!", ephemeral=True)

        self.has_reward = False # important for _create_view
        view = self._create_view()
        self.view.saved = True

        await interaction.response.edit_message(content=f"Successfully claimed the following rewards from the box: {self._format_rewards()}", view=view)
        self.view.stop()

    async def _handle_incorrect(self, interaction: discord.Interaction) -> None:
        """Handles an incorrect button click"""
        view = self._create_view()
        await interaction.response.edit_message(content="Oh no! You lost all rewards! Better luck next time. You lost: " + (r if len((r:= self._format_rewards())) > 1 else "no rewards"), view=view)
        self.view.stop()

    async def _handle_correct(self, interaction: discord.Interaction) -> None:
        """Handles a correct button click"""
        view = self._create_view()
        self.view.claimed.append(self.reward)
        await interaction.response.edit_message(content="Correct! To save your current rewards and exit, press save. Current rewards: " + (r if len((r:= self._format_rewards())) > 1 else "no rewards"), view=view)

    async def callback(self, interaction: discord.Interaction):
        """The callback of the button which calls the right method depending on the reward and index"""        
        if self.index == 24:
            return await self._end_button(interaction)

        if not self.has_reward:
            await self._handle_incorrect(interaction)
        
        else:
            await self._handle_correct(interaction)
    
class LootBox:
    """A class which contains infos about a lootbox and can open one"""
    def __init__(self, ctx:commands.Context, rewards:List[Union[None, PartialCard, int]]):
        self.ctx = ctx
        self.rewards = rewards

    def _assign_until_unique(self, taken:List[int]) -> int:
        if taken[(res:= random.randint(0, 23))]:
            return self._assign_until_unique(taken)
        return res

    def _create_view(self) -> discord.ui.View:
        l = [None for x in range(24)] # creating a list of no rewards as the base
        for rew in self.rewards:
            l[self._assign_until_unique(l)] = rew
        
        view = View(self.ctx.author.id)
        view.rewards = l 
        view.saved = False
        view.claimed = []
        for i in range(24):
            view.add_item(_LootBoxButton(index=i, style=discord.ButtonStyle.grey, rewards=l, label=" "))
        view.add_item(_LootBoxButton(index=24, style=discord.ButtonStyle.blurple, rewards=l, label="Save rewards"))

        return view

    @staticmethod
    def get_random_lootbox() -> int:
        """Gets a random lootbox from the LOOTBOXES constant"""
        return random.choices(list(LOOTBOXES.keys()), [x["probability"] for x in LOOTBOXES.values()])[0]

    @classmethod
    def generate_rewards(self, box:int) -> List[Union[PartialCard, int]]:
        """Generates a list of rewards that can be used to pass to this class"""
        data = LOOTBOXES[box]
        rew = []
        for i in range((cards:=random.choice(data["cards_total"]))):
            r = [x["_id"] for x in items.find({"rank": {"$in": data["rewards"]["cards"]["rarities"]}, "type": {"$in": data["rewards"]["cards"]["types"]}, "available": True}) if x["_id"] != 0]
            rew.append(PartialCard(random.choice(r)))

        for i in range(data["rewards_total"]-cards):
            rew.append(random.randint(*data["rewards"]["jenny"]))

        return rew

    async def open(self):
        """Opens a lootbox"""
        view = self._create_view()
        msg = await self.ctx.send(f"There are {len(self.rewards)} rewards hidden in this box. Click a button to reveal a reward. You can reveal buttons as much as you like, but careful, if you hit a bomb you loose all rewards! If you are happy with your rewards and don't want to risk anything, hit save to claim them", view=view)
        await view.wait()
        await view.disable(msg)

        if not view.saved:
            return
        
        user = User(self.ctx.author.id)
        for r in view.claimed:
            if isinstance(r, PartialCard):
                user.add_card(r.id)
            else:
                if user.is_entitled_to_double_jenny:
                    r *= 2
                user.add_jenny(r)

class Button(discord.ui.Button):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def callback(self, interaction: discord.Interaction):
        self.view.value = self.custom_id
        self.view.stop()

class ConfirmButton(discord.ui.View):
    """A button that is used to confirm a certain action or deny it"""
    def __init__(self, user_id:int, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.timed_out = False # helps subclasses using Button to have set this to False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not (val := interaction.user.id == self.user_id):
            await interaction.response.defer()
        return val

    async def disable(self, msg:discord.Message) -> discord.Message:
        if len([c for c in self.children if not c.disabled]) == 0: # if every child is already disabled, we don't need to edit the message again
            return

        for child in self.children:
            child.disabled = True

        await msg.edit(view=self)

    async def on_timeout(self):
        self.value = False
        self.timed_out = True
    
    @discord.ui.button(label="confirm", style=discord.ButtonStyle.green)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = True
        self.timed_out = False
        self.stop()

    @discord.ui.button(label="cancel", style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = False
        self.timed_out = False
        self.stop()

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

# pillow logic contributed by DerUSBstick (Thank you!)
class Book:

    background_cache = {}
    card_cache = {}

    def __init__(self, session:aiohttp.ClientSession):
        self.session = session

    async def _imagefunction(self, data, restricted_slots, page:int):
        background = await self._getbackground(0 if len(data) == 10 else 1)
        if len(data) == 18 and restricted_slots:
            background = await self._numbers(background, data, page)
        background = await self._cards(background, data, 0 if len(data) == 10 else 1)
        background = self._setpage(background, page)
        return background

    def _get_from_cache(self, types:int) -> Union[Image.Image, None]:
        if types == 0:
            if "first_page" in self.background_cache:
                return self.background_cache["first_page"]
            return
        else:
            if "default_background" in self.background_cache:
                return self.background_cache["default_background"]
            return
        
    def _set_cache(self, data:Image, first_page:bool) -> None:
        self.background_cache["first_page" if first_page else "default_background"] = data

    async def _getbackground(self, types) -> Image.Image:
        url = ['https://alekeagle.me/XdYUt-P8Xv.png', 'https://alekeagle.me/wp2mKvzvCD.png']
        if (res:= self._get_from_cache(types)):
            return res.convert("RGBA")

        async with self.session.get(url[types]) as res: 
            image_bytes = await res.read()
            background = (img:= Image.open(io.BytesIO(image_bytes))).convert('RGBA') 

        self._set_cache(img, types == 0)
        return background

    async def _getcard(self, url) -> Image.Image:

        async with self.session.get(url) as res:
            image_bytes = await res.read()
            image_card = Image.open(io.BytesIO(image_bytes)).convert('RGBA')
            image_card = image_card.resize((84, 115), Image.ANTIALIAS)
        # await asyncio.sleep(0.4) # This is to hopefully prevent aiohttp's "Response payload is not completed" bug
        return image_card

    def _setpage(self, image, page):
        font = self._getfont(20)
        draw = ImageDraw.Draw(image)
        draw.text((5, 385), f'{page*2-1}', (0,0,0), font=font)
        draw.text((595, 385), f'{page*2}', (0,0,0), font=font)
        return image

    def _getfont(self, size) -> ImageFont.ImageFont:
        font = ImageFont.truetype(str(pathlib.Path(__file__).parent.parent) + "/static/font.ttf", size, encoding="unic") 
        return font

    async def _cards(self, image, data, option):
        card_pos:list = [
            [(112, 143),(318, 15),(418, 15),(513, 15),(318, 142),(418, 142),(514, 142),(318, 269),(418, 269),(514, 269)],
            [(12,14),(112,14),(207,14),(12,141),(112,143),(208,143),(13,271),(112,272),(209,272), (318, 15),(417, 15),(513, 15),(318, 142),(418, 142),(514, 142),(318, 269),(418, 269),(514, 269)]
        ]
        for n, i in enumerate(data): 
            if i:
                if i[1]:
                    if not str(i[0]) in self.card_cache:
                        self.card_cache[str(i[0])] = await self._getcard(i[1])

                    card = self.card_cache[str(i[0])]
                    image.paste(card, (card_pos[option][n]), card)
        return image

    async def _numbers(self, image, data, page):
        page -= 2
        numbers_pos:list = [
        [(35, 60),(138, 60),(230, 60),(35, 188),(138, 188),(230, 188),(36, 317),(134, 317),(232, 317),(338, 60),(436, 60),(536, 60),(338, 188),(436, 188),(536, 188),(338, 317),(436, 317),(536, 317)], 
        [(30, 60),(132, 60),(224, 60),(34, 188),(131, 188),(227, 188),(32, 317),(130, 317),(228, 317),(338, 60),(436, 60),(533, 60),(338, 188),(436, 188),(533, 188),(338, 317),(436, 317),(533, 317)], 
        [(30, 60),(130, 60),(224, 60),(31, 188),(131, 188),(230, 188),(32, 317),(130, 317),(228, 317),(338, 60),(436, 60),(533, 60),(338, 188),(436, 188),(533, 188),(340, 317),(436, 317),(533, 317)], 
        [(30, 60),(130, 60),(224, 60),(31, 188),(131, 188),(230, 188),(32, 317),(133, 317),(228, 317),(338, 60),(436, 60),(533, 60),(338, 188),(436, 188),(533, 188),(338, 317),(436, 317),(535, 317)], 
        [(30, 60),(130, 60),(224, 60),(31, 188),(131, 188),(230, 188),(32, 317),(133, 317),(228, 317),(342, 60),(436, 60),(533, 60),(338, 188),(436, 188),(533, 188),(338, 317),(436, 317),(535, 317)], 
        [(30, 60),(130, 60),(224, 60),(31, 188),(131, 188),(230, 188),(32, 317),(133, 317),(228, 317),(342, 60),(436, 60),(533, 60),(338, 188),(436, 188),(533, 188),(338, 317),(436, 317),(535, 317)] 
        ]

        font = self._getfont(35)
        draw = ImageDraw.Draw(image)
        for n, i in enumerate(data):
            if i[1] is None:
                draw.text(numbers_pos[page][n], f'0{i[0]}', (165,165,165), font=font)
        return image

    async def _get_book(self, user:discord.Member, page:int, just_fs_cards:bool=False):
        rs_cards = []
        fs_cards = []
        person = User(user.id)
        if just_fs_cards:
            page += 6
        
        # Bringing the list in the right format for the image generator
        if page < 7:
            if page == 1:
                i = 0
            else:
                i = 10+((page-2)*18) 
                # By calculating where the list should start, I make the code faster because I don't need to
                # make a list of all cards and I also don't need to deal with a problem I had when trying to get
                # the right part out of the list. It also saves me lines! 
            while not len(rs_cards) % 18 == 0 or len(rs_cards) == 0: 
                # I killed my pc multiple times while testing, don't use while loops!
                if not i in [x[0] for x in person.rs_cards]:
                    rs_cards.append([i, None])
                else:
                    rs_cards.append([i, PartialCard(i).image_url])
                if page == 1 and len(rs_cards) == 10:
                    break
                i = i+1
        else:
            i = (page-7)*18 
            while (len(fs_cards) % 18 == 0) == False or (len(fs_cards) == 0) == True: 
                try:
                    fs_cards.append([person.fs_cards[i][0], PartialCard(person.fs_cards[i][0]).image_url])
                except IndexError: 
                    fs_cards.append(None)
                i = i+1

        image = await self._imagefunction(rs_cards if (page <= 6 and not just_fs_cards) else fs_cards, (page <= 6 and not just_fs_cards), page)

        buffer = io.BytesIO()
        image.save(buffer, "png") 
        buffer.seek(0)

        f = discord.File(buffer, filename="image.png")
        embed = discord.Embed.from_dict({
            'title': f'{user.display_name}\'s book',
            'color': 0x2f3136, # making the boarder "invisible" (assuming there are no light mode users)
            'image': {'url': 'attachment://image.png' },
            'footer': {'text': ''}
        })
        return embed, f

    async def create(self, user:discord.Member, page:int, just_fs_cards:bool=False) -> Tuple[discord.Embed, discord.File]:
        return await self._get_book(user, page, just_fs_cards)

class User:
    """This class allows me to handle a lot of user related actions more easily"""
    cache = {}

    @classmethod 
    def __get_cache(cls, user_id:int):
        """Returns a cached object"""
        return cls.cache[user_id] if user_id in cls.cache else None

    def __new__(cls, user_id:int, *args, **kwargs):
        existing = cls.__get_cache(user_id)
        if existing:
            return existing
        return super().__new__(cls)

    def __init__(self, user_id:int):
        if user_id in self.cache:
            return 

        user = teams.find_one({'id': user_id})

        self.id:int = user_id

        if user is None:
            self.add_empty(self.id, False)
            user = teams.find_one({'id': user_id})

        if not 'cards' in user or not 'met_user' in user:
            self.add_empty(self.id)
            user = teams.find_one({'id': user_id})

        self.jenny:int = user['points']
        self.daily_cooldown = user['cooldowndaily']
        self.met_user:list = user['met_user']
        self.effects:dict = user['cards']['effects']
        self.rs_cards:list = user['cards']['rs']
        self.fs_cards:list = user['cards']['fs']
        self.badges:list = user['badges']
        self.votes = user["votes"] if "votes" in user else 0
        self.premium_guilds:dict = user["premium_guilds"] if "premium_guilds" in user else {}
        self.lootboxes:list = user["lootboxes"] if "lootboxes" in user else []
        self.weekly_cooldown = user["weekly_cooldown"] if "weekly_cooldown" in user else None

        self.cache[self.id] = self

    @property
    def all_cards(self) -> List[int, dict]:
        return [*self.rs_cards, *self.fs_cards]

    @property
    def is_premium(self) -> bool:
        if len([x for x in self.badges if x in PREMIUM_ALIASES.keys()]) > 0:
            return True
        return len([x for x in self.badges if x in PATREON_TIERS.keys()]) > 0

    @property
    def premium_tier(self) -> Union[str, None]:
        if len((res := [x for x in self.badges if x in PREMIUM_ALIASES.keys()])) > 0:
            return PREMIUM_ALIASES[res]
        return [x for x in self.badges if x in PATREON_TIERS.keys()][0] if self.is_premium else None

    @property
    def is_entitled_to_double_jenny(self) -> bool:
        return self.is_premium and self.premium_tier in list(PATREON_TIERS.keys())[2:]

    @all_cards.setter
    def all_cards(self, other):
        """The only time I'd realistically call this is to remove all cards"""
        if not isinstance(other, list) or len(other) != 0:
            raise TypeError("Can only set this property to an empty list") # setting this to something else by accident could be fatal
        self.fs_cards = []
        self.rs_cards = []

    @classmethod
    def remove_all(cls) -> str:
        """Removes all cards etc from every user. Only used for testing"""
        start = datetime.now()
        user = []
        for u in teams.find():
            if 'cards' in u:
                user.append(u['id'])
            if "id" in u and u["id"] in cls.cache:
                cls.cache[u["id"]].all_cards = []
                cls.cache[u["id"]].effects = {}

        teams.update_many({'$or': [{'id': x} for x in user]}, {'$set': {'cards': {'rs': [], 'fs': [], 'effects': {}}, 'met_user': []}})
        cards = [x for x in items.find() if "owners" in x and len(x["owners"]) > 0]
        items.update_many({'_id': {"$in": [x["_id"] for x in items.find()]}}, {'$set': {'owners': []}})

        return f"Removed all cards from {len(user)} user{'s' if len(user) > 1 else ''} and all owners from {len(cards)} card{'s' if len(cards) != 1 else ''} in {(datetime.now() - start).seconds} second{'s' if (datetime.now() - start).seconds > 1 else ''}"

    @classmethod
    def is_registered(cls, user_id:int) -> bool:
        """Checks if the "cards" dictionary is in the database entry of the user"""
        u = teams.find_one({'id': user_id})
        if u is None:
            return False
        if not 'cards' in u:
            return False

        return True   

    @classmethod # The reason for this being a classmethod is that User(user_id) automatically calls this function, 
    # so while I will also never use this, it at least makes more sense
    def add_empty(cls, user_id:int, cards:bool=True) -> None:
        """Can be called when the user does not have an entry to make the class return empty objects instead of None"""
        if cards:
            teams.update_one({'id': user_id}, {'$set': {'cards': {'rs': [], 'fs': [], 'effects': {}}, 'met_user': [], "votes": 0}})  
        else:
            teams.insert_one({'id': user_id, 'points': 0, 'badges': [], 'cooldowndaily': '','cards': {'rs': [], 'fs': [], 'effects': {}}, 'met_user': [], "votes": 0}) 

    def _update_val(self, key:str, value:Any, operator:str="$set") -> None:
        """An easier way to update a value"""
        teams.update_one({"id": self.id}, {operator: {key: value}})

    def add_badge(self, badge:str) -> None:
        """Adds a badge to a user"""
        if badge.lower() in self.badges:
            raise TypeError("Badge already in possesion of user")

        self.badges.append(badge.lower())
        self._update_val("badges", badge.lower(), "$push")

    def remove_badge(self, badge:str) -> None:
        """Removes a badge from a user"""
        if not badge.lower() in self.badges:
            return # Don't really care if that happens
        self.badges.remove(badge.lower())
        self._update_val("badges", badge.lower(), "$pull")

    def set_badges(self, badges:List[str]) -> None:
        """Sets badges to anything"""
        self.badges = badges
        self._update_val("badges", self.badges)

    def clear_premium_guilds(self) -> None:
        """Removes all premium guilds from a user"""
        self.premium_guilds = {}
        self._update_val("premium_guilds", {})

    def add_vote(self) -> None:
        """Keeps track of how many times a user has voted for Killua to increase the rewards over time"""
        self.votes += 1
        self._update_val("votes", 1, "$inc")

    def add_premium_guild(self, guild_id:int) -> None:
        """Adds a guild to a users premium guilds"""
        self.premium_guilds[str(guild_id)] = datetime.now()
        self._update_val("premium_guilds", self.premium_guilds)

    def remove_premium_guild(self, guild_id:int) -> None:
        """Removes a guild from a users premium guilds"""
        del self.premium_guilds[str(guild_id)]
        self._update_val("premium_guilds", self.premium_guilds)

    def claim_weekly(self) -> None:
        """Sets the weekly cooldown new"""
        self.weekly_cooldown = datetime.now() +  timedelta(days=7)
        self._update_val("weekly_cooldown", self.weekly_cooldown)

    def claim_daily(self) -> None:
        """Sets the daily cooldown new"""
        self.daily_cooldown = datetime.now() +  timedelta(days=1)
        self._update_val("cooldowndaily", self.daily_cooldown) 

    def has_lootbox(self, box:int) -> bool:
        """Returns wether the user has the lootbox specified"""
        return box in self.lootboxes

    def add_lootbox(self, box:int) -> None:
        """Adds a lootbox to a users inventory"""
        self.lootboxes.append(box)
        self._update_val("lootboxes", box, "$push")

    def remove_lootbox(self, box:int) -> None:
        """Removes a lootbox from a user"""
        self.lootboxes.remove(box)
        self._update_val("lootboxes", self.lootboxes, "$set")
        
    def _has_card(self, cards:List[list], card_id:int, fake_allowed:bool, only_allow_fakes:bool) -> bool:
        counter = 0
        while counter != len(cards): # I use a while loop because it has c bindings and is thus faster than a for loop which is good for this 
            id, data = cards[counter]
            if (id == card_id) and ((only_allow_fakes and data["fake"]) or (not data["fake"] or fake_allowed)):
                return True

            counter += 1
        return False

    def has_rs_card(self, card_id:int, fake_allowed:bool=True, only_allow_fakes:bool=False) -> bool:
        """Checking if the user has a card specified in their restricted slots"""
        return self._has_card(self.rs_cards, card_id, fake_allowed, only_allow_fakes)

    def has_fs_card(self, card_id:int, fake_allowed:bool=True, only_allow_fakes:bool=False) -> bool:
        """Checking if the user has a card specified in their free slots"""
        return self._has_card(self.fs_cards, card_id, fake_allowed, only_allow_fakes)

    def has_any_card(self, card_id:int, fake_allowed:bool=True, only_allow_fakes:bool=False) -> bool:
        """Checks if the user has the card"""
        return self._has_card(self.all_cards, card_id, fake_allowed, only_allow_fakes)

    def remove_jenny(self, amount:int):
        """Removes x Jenny from a user"""
        if self.jenny < amount:
            raise Exception('Trying to remove more Jenny than the user has')
        self.jenny -= amount
        self._update_val("points", -amount, "$inc")

    def add_jenny(self, amount:int):
        """Adds x Jenny to a users balance"""
        self.jenny += amount
        self._update_val("points", amount, "$inc")

    def set_jenny(self, amount:int):
        """Sets the users jenny to the specified value. Only used for testing"""
        self.jenny = amount
        self._update_val("points", amount)

    def _find_match(self, cards:List[list], card_id:int, fake:Optional[bool], clone:Optional[bool]) -> Tuple[Union[List[List[int, dict]], None], Union[List[int, dict], None]]:
        counter = 0
        while counter != len(cards): # I use a while loop because it has c bindings and is thus faster than a for loop which is good for this 
            id, data = cards[counter]
            if (id == card_id) and \
                ((data["clone"] == clone) if not clone is None else True) and \
                ((data["fake"] == fake) if not fake is None else True):

                    if not data["fake"]:
                        PartialCard(id).remove_owner(self.id)

                    del cards[counter] # instead of returning the match I delete it because in theory there can be multiple matches and that would break stuff
                    return cards, [id, data]
            counter += 1
        return None, None

    def _incomplete(self) -> None:
        """Called every time a card is removed it checks if it should remove card 0 and the badge and if it should, it does"""
        if len(self.rs_cards) == 99:
            self.remove_card(0)
            self.remove_badge("greed_island_badge")

    def _remove_logic(self, card_type:str, card_id:int, remove_fake:bool, clone:bool, no_exception:bool=False) -> List[int, dict]:
        """Handles the logic of the remove_card method"""
        attr = getattr(self, f"{card_type}_cards")
        cards, match = self._find_match(attr, card_id, remove_fake, clone)
        if not match:
            if no_exception:
                return self._remove_logic("rs", card_id, remove_fake, clone)
            else:
                raise NoMatches
        attr = cards
        self._update_val(f"cards.{card_type}", attr)
        self._incomplete()
        return match

    def remove_card(self, card_id:int, remove_fake:bool=None, restricted_slot:bool=None, clone:bool=None) -> List[int, dict]:
        """Removes a card from a user"""
        if self.has_any_card(card_id) is False:
            raise NotInPossesion('This card is not in possesion of the specified user!')

        if restricted_slot:
            return self._remove_logic("rs", card_id, remove_fake, clone)

        elif restricted_slot is False:
            return self._remove_logic("fs", card_id, remove_fake, clone)

        else: # if it wasn't specified it first tries to find it in the free slots, then restricted slots
            return self._remove_logic("fs", card_id, remove_fake, clone, no_exception=True)

    def _add_card_owner(self, card:int, fake:bool) -> None:
        if not fake:
            PartialCard(card).add_owner(self.id)

    def add_card(self, card_id:int, fake:bool=False, clone:bool=False):
        """Adds a card to the the user"""
        data = [card_id, {"fake": fake, "clone": clone}]

        if self.has_rs_card(card_id) is False:
            if card_id < 100:

                self.rs_cards.append(data)
                self._add_card_owner(card_id, fake)
                self._update_val("cards.rs", data, "$push")
                if len([x for x in self.rs_cards if not x[1]["fake"]]) == 99:
                    self.add_card(0)
                    self.add_badge("greed_island_badge")
                return

        if len(self.fs_cards) >= FREE_SLOTS:
            raise CardLimitReached('User reached card limit for free slots')

        self.fs_cards.append(data)
        self._add_card_owner(card_id, fake)
        self._update_val("cards.fs", data, "$push")

    def count_card(self, card_id:int, including_fakes:bool=True) -> int:
        "Counts how many copies of a card someone has"
        return len([x for x in self.all_cards if (including_fakes or not x[1]["fake"]) and x[0] == card_id])

    def add_multi(self, *args):
        """The purpose of this function is to be a faster alternative when adding multiple cards than for loop with add_card"""
        fs_cards = []
        rs_cards = []

        def fs_append(item:list):
            if len([*self.fs_cards, *fs_cards]) >= 40:
                return fs_cards
            fs_cards.append(item)
            return fs_cards

        for item in args:
            if not item[1]["fake"]:
                PartialCard(item[0]).add_owner(self.id)
            if item[0] < 99:
                if not self.has_rs_card(item[0]):
                    if not item[0] in [x[0] for x in rs_cards]:
                        rs_cards.append(item)
                        continue
            fs_append(item)

        self.rs_cards = [*self.rs_cards, *rs_cards]
        self.fs_cards = [*self.fs_cards, *fs_cards]
        teams.update_one({"id": self.id}, {"$set": {'cards.rs': self.rs_cards, 'cards.fs': self.fs_cards}})

    def has_defense(self) -> bool:
        """Checks if a user holds on to a defense spell card"""
        for x in DEF_SPELLS:
            if x in [x[0] for x in self.fs_cards]:
                if self.has_any_card(x, False):
                    return True
        return False

    def swap(self, card_id:int) -> Union[bool, None]: 
        """Swaps a card from the free slots with one from the restricted slots. Usecase: swapping fake and real card"""

        if (True in [x[1]['fake'] for x in self.rs_cards if x[0] == card_id] and False in [x[1]['fake'] for x in self.fs_cards if x[0] == card_id]):
            r = self.remove_card(card_id, remove_fake=True, restricted_slot=True)
            r2 = self.remove_card(card_id, remove_fake=False, restricted_slot=False)
            self.add_card(card_id, False, r[1]["clone"])
            self.add_card(card_id, True, r2[1]["clone"])

        elif (True in [x[1]['fake'] for x in self.fs_cards if x[0] == card_id] and False in [x[1]['fake'] for x in self.rs_cards if x[0] == card_id]):
            r = self.remove_card(card_id, remove_fake=True, restricted_slot=False)
            r2 = self.remove_card(card_id, remove_fake=False, restricted_slot=True)
            self.add_card(card_id, True, r[1]["clone"])
            self.add_card(card_id, False, r2[1]["clone"])

        else:
            return False # Returned if the requirements haven't been met
            

    def add_effect(self, effect, value): 
        """Adds a card with specified value, easier than checking for appropriate value with effect name"""
        self.effects[effect] = value
        self._update_val("cards.effects", self.effects)

    def remove_effect(self, effect):
        """Remove effect provided"""
        self.effects.pop(effect, None)
        self._update_val("cards.effects", self.effects)

    
    def has_effect(self, effect) -> Tuple[bool, Any]:
        """Checks if a user has an effect and returns what effect if the user has it"""
        if effect in self.effects:
            return True, self.effects[effect]
        else:
            return False, None

    def add_met_user(self, user_id:int):
        """Adds a user to a "previously met" list which is a parameter in some spell cards"""
        if not user_id in self.met_user:
            self.met_user.append(user_id)
            self._update_val("met_user", user_id, "$push")

    def has_met(self, user_id:int) -> bool:
        """Checks if the user id provided has been met by the self.id user"""
        return user_id in self.met_user

    def _remove(self, cards:str):
        for card in [x[0] for x in getattr(self, cards)]:
            try:
                PartialCard(card).remove_owner(self.id)
            except Exception:
                pass

        setattr(self, cards, [])

    def nuke_cards(self, t='all') -> bool:
        """A function only intended to be used by bot owners, not in any actual command, that's why it returns True, so the owner can see if it succeeded"""
        if t == 'all': 
            self._remove("all_cards")
            self.effects = {}
            teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': [], 'fs': [], 'effects': {}}}})
            return True
        if t == 'fs':
            self._remove("fs_cards")
            teams.update_one({'id': self.id}, {'$set': {'cards.fs': []}})
            return True
        if t == 'rs':
            self._remove("rs_cards")
            teams.update_one({'id': self.id}, {'$set': {'cards.rs': []}})
            return True
        if t == 'effects':
            self.effects = {}
            teams.update_one({'id': self.id}, {'$set': {'cards.effects': {}}})
            return True

class TodoList():
    cache = {}
    custom_id_cache = {}

    @classmethod 
    def __get_cache(cls, list_id:int):
        """Returns a cached object"""
        if isinstance(list_id, str):
            if not list_id in cls.custom_id_cache:
                return None
            list_id = cls.custom_id_cache[list_id]
        return cls.cache[list_id] if list_id in cls.cache else None

    def __new__(cls, list_id:Union[int, str], *args, **kwargs):
        existing = cls.__get_cache(list_id)
        if existing is not None: # why not just `if existing:` python does not call this when I do this which is dumb so I have to do it this way
            return existing
        return super().__new__(cls)

    def __init__(self, list_id:Union[int, str]):
        
        if (list_id in self.cache) or (list_id in self.custom_id_cache):
            return

        td_list = todo.find_one({'_id' if isinstance(list_id, int) else 'custom_id': list_id if isinstance(list_id, int) else list_id.lower()})

        if not td_list:
            raise TodoListNotFound

        self.id:int = td_list['_id']
        self.owner:int = td_list['owner']
        self.name:str = td_list['name']
        self._custom_id:str = td_list['custom_id']
        self.status:str = td_list['status']
        self.delete_done:bool = td_list['delete_done']
        self.viewer:list = td_list['viewer']
        self.editor:list = td_list['editor']
        self.created_at:str = td_list['created_at']
        self.spots:int = td_list['spots']
        self.views:int = td_list['views']
        self.todos:list = td_list['todos']
        self.thumbnail:str = td_list['thumbnail'] if 'thumbnail' in td_list else None
        self.color:int = td_list['color'] if 'color' in td_list else None
        self.description:str = td_list['description'] if 'description' in td_list else None

        if self._custom_id:
            self.custom_id_cache[self._custom_id] = self.id
        self.cache[self.id] = self

    @property
    def custom_id(self) -> Union[str, None]:
        return self._custom_id

    @custom_id.setter
    def custom_id(self, value):
        del self.custom_id_cache[self._custom_id]
        self._custom_id = value
        self.custom_id_cache[value] = self.id

    def __len__(self) -> int:
        """Makes it nicer to get the "length" of a todo list, or rather the length of its todo's"""
        return len(self.todos)

    @staticmethod
    def _generate_id() -> int:
        l = []
        while len(l) != 6:
            l.append(str(random.randint(0,9)))

        todo_id = todo.find_one({'_id': ''.join(l)})

        if todo_id is None:
            return int(''.join(l))
        else:
            return TodoList._generate_id()

    @staticmethod
    def create(owner:int, title:str, status:str, done_delete:bool, custom_id:str=None) -> TodoList:
        """Creates a todo list and returns a TodoList class"""
        list_id = TodoList._generate_id()
        todo.insert_one({'_id': list_id, 'name': title, 'owner': owner, 'custom_id': custom_id, 'status': status, 'delete_done': done_delete, 'viewer': [], 'editor': [], 'todos': [{'todo': 'add todos', 'marked': None, 'added_by': 756206646396452975, 'added_on': (datetime.now()).strftime("%b %d %Y %H:%M:%S"), 'views':0, 'assigned_to': [], 'mark_log': []}], 'marks': [], 'created_at': (datetime.now()).strftime("%b %d %Y %H:%M:%S"), 'spots': 10, 'views': 0 })
        return TodoList(list_id)

    def delete(self) -> None:
        """Deletes a todo list"""
        del self.cache[self.id]
        if self.custom_id:
            del self.custom_id_cache[self.custom_id]
        todo.delete_one({'_id': self.id})

    def has_view_permission(self, user_id:int) -> bool:
        """Checks if someone has permission to view a todo list"""
        if self.status == 'private':
            if not (user_id in self.viewer or user_id in self.editor or user_id == self.owner):
                return False
        return True

    def has_edit_permission(self, user_id:int) -> bool:
        """Checks if someone has permission to edit a todo list"""
        if not (user_id in self.editor or user_id == self.owner):
            return False
        return True

    def _update_val(self, key:str, value:Any, operator:str="$set") -> None:
        """An easier way to update a value"""
        todo.update_one({"_id": self.id}, {operator: {key: value}})

    def set_property(self, prop, value):
        """Sets any property and updates the db as well"""
        setattr(self, prop, value)
        self._update_val(prop, value)

    def add_view(self, viewer:int) -> None:
        """Adds a view to a todo lists viewcount"""
        if not viewer == self.owner and not viewer in self.viewer and viewer in self.editor:
            self.views += 1
            self._update_val("views", 1, "$inc")

    def add_spots(self, spots) -> None:
        """Easy way to add max spots"""
        self.spots += spots
        self._update_val("spots", spots, "$inc")

    def add_editor(self, user:int) -> None:
        """Easy way to add an editor"""
        self.editor.append(user)
        self._update_val("editor", user, "$push")

    def add_viewer(self, user:int) -> None:
        """Easy way to add a viewer"""
        self.viewer.append(user)
        self._update_val("viewer", user, "$push")

    def kick_editor(self, editor:int) -> None:
        """Easy way to kick an editor"""
        self.editor.remove(editor)
        self._update_val("editor", editor, "$pull")

    def kick_viewer(self, viewer:int) -> None:
        """Easy way to kick a viewer"""
        self.viewer.remove(viewer)
        self._update_val("viewer", viewer, "$pull")

    def has_todo(self, task:int) -> bool:
        """Checks if a list contains a certain todo task"""
        try:
            if task < 1:
                return False
            self.todos[task-1]
        except Exception:
            return False
        return True

    def clear(self) -> None:
        """Removes all todos from a todo list"""
        self.todos = []
        self._update_val("todos", [])

class Todo(TodoList):

    def __new__(cls, position:int, list_id:int):
        cls = super().__new__(cls, list_id)
        task = cls.todos[position-1]

        cls.todo:str = task['todo']
        cls.marked:str = task['marked']
        cls.added_by:int = task['added_by']
        cls.added_on:str = task['added_on']
        cls.views:int = task['views']
        cls.assigned_to:list = task['assigned_to']
        cls.mark_log:list = task['mark_log']
        return cls

class Guild():
    """A class to handle basic guild data"""
    cache = {}

    @classmethod
    def __get_cache(cls, guild_id:int) -> Union[Guild, None]:
        return cls.cache[guild_id] if guild_id in cls.cache else None

    def __new__(cls, guild_id:int, *args, **kwargs):
        existing = cls.__get_cache(guild_id)
        if existing:
            return existing
        guild = super().__new__(cls)
        return guild

    def __init__(self, guild_id:int):
        if guild_id in self.cache:
            return

        g = guilds.find_one({'id': guild_id})

        if not g:
            self.add_default(guild_id)
            g = guilds.find_one({'id': guild_id})

        self.id:int = guild_id
        self.badges:list = g['badges']
        self.prefix:str = g['prefix']
        self.commands:dict = {v for k, v in g["commands"].items()} if "commands" in g else {}
        
        if 'tags' in g:
            self.tags = g['tags']

        self.cache[self.id] = self

    @property
    def is_premium(self) -> bool:
        return ("partner" in self.badges) or ("premium" in self.badges)

    @classmethod
    def add_default(self, guild_id:int):
        """Adds a guild to the database"""
        guilds.insert_one({'id': guild_id, 'points': 0,'items': '','badges': [], 'prefix': 'k!'})

    @classmethod
    def bullk_remove_premium(cls, guild_ids:List[int]) -> None:
        """Removes premium from all guilds specified, if possible"""
        for guild in guild_ids:
            try:
                User.cache[guild].badges.remove("premium")
            except Exception:
                guild_ids.remove(guild) # in case something got messed up it removes the guild id before making the db interaction

        guilds.update_many({"id": {"$in": guild_ids}}, {"$pull": {"badges": "premium"}})

    def _update_val(self, key:str, value:Any, operator:str="$set") -> None:
        """An easier way to update a value"""
        guilds.update_one({"id": self.id}, {operator: {key: value}})

    def delete(self):
        """Deletes a guild from the database"""
        del self.cache[self.id]
        guilds.delete_one({'id': self.id})

    def change_prefix(self, prefix:str):
        "Changes the prefix of a guild"
        self.prefix = prefix
        self._update_val("prefix", self.prefix)

    def add_premium(self):
        """Adds premium to a guild"""
        self.badges.append("premium")
        self._update_val("badges", "premium", "$push")

    def remove_premium(self):
        """"Removes premium from a guild"""
        self.badges.remove("premium")
        self._update_val("badges", "premium", "$pull")
