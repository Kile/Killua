from __future__ import annotations
"""
This file comtains classes that are not specific to one group and are used across several files
"""
from datetime import datetime, timedelta
import random
import discord
from enum import Enum
from typing import Union, Tuple, List

from .paginator import View
from .constants import FREE_SLOTS, teams, items, guilds, todo, PATREON_TIERS, LOOTBOXES

class CardNotFound(Exception):
    pass

class NotInPossesion(Exception):
    pass

class OnlyFakesFound(Exception):
    pass

class CardLimitReached(Exception):
    pass

class TodoListNotFound(Exception):
    pass

class _LootBoxButton(discord.ui.Button):
    """A class used for lootbox buttons"""
    def __init__(self, index:int, rewards:List[Union[Card, int, None]],**kwargs):
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
                c.label=("" if isinstance(self.reward, Card) else str(self.reward)) if self.has_reward else ""
                c.style=discord.ButtonStyle.success if self.has_reward else discord.ButtonStyle.red
                c.emoji=(self.reward.emoji if isinstance(self.reward, Card) else None) if self.has_reward else "\U0001f4a3"
            elif c.index == 24:
                c.disabled = not self.has_reward
            else:
                c.disabled=c.disabled if self.has_reward else True
                c.label=(("" if isinstance(c.reward, Card) else str(c.reward)) if c.has_reward else "") if not self.has_reward else c.label
                c.emoji=((c.reward.emoji if isinstance(c.reward, Card) else None) if c.has_reward else "\U0001f4a3") if not self.has_reward else c.emoji
            
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

        rewards = ("cards " + ", ".join(cards)+(" and " if jenny > 0 else "") if len(cards:= [c.emoji for c in self.view.claimed if isinstance(c, Card)]) > 0 else "") + (str(jenny) + " jenny" if jenny > 0 else "")
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
    def __init__(self, ctx:commands.Context, rewards:List[Union[None, Card, int]]):
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
    def generate_rewards(self, box:int) -> List[Union[Card, int]]:
        """Generates a list of rewards that can be used to pass to this class"""
        data = LOOTBOXES[box]
        rew = []
        for i in range((cards:=random.choice(data["cards_total"]))):
            r = [x["_id"] for x in items.find({"rank": {"$in": data["rewards"]["cards"]["rarities"]}, "type": {"$in": data["rewards"]["cards"]["types"]}})]
            rew.append(Card(random.choice(r)))

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
            if isinstance(r, Card):
                user.add_card(r.id)
            else:
                user.add_jenny(r)

class ConfirmButton(discord.ui.View):
    """A button that is used to confirm a certain action or deny it"""
    def __init__(self, user_id:int, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not (val := interaction.user.id == self.user_id):
            await interaction.response.defer()
        return val

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
    TAGS = {
        "name": "tags",
        "description": "Tags if you want to save some text. Premium only",
        "emoji": {
            "unicode": "\U0001f5c4",
            "normal": ":file_cabinet:"
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

class Card():
    """This class makes it easier to access card information"""
    def __init__(self, card_id:int):
        card = items.find_one({'_id': card_id})
        if card is None:
            raise CardNotFound
        
        self.id:int = card['_id']
        self.name:str = card['name']
        self.image_url:str = card['Image']
        self.owners:list = card['owners']
        self.description:str = card['description']
        self.emoji:str = card['emoji']
        self.rank:str = card['rank']
        self.limit:int = card['limit']
        try:
            self.type:str = card['type']
        except KeyError:
            items.update_one({'_id': self.id}, {'$set':{'type': 'normal'}})
            self.type = 'normal'

        if card_id > 1000 and not card_id == 1217: # If the card is a spell card it has two additional properties
            self.range:str = card['range']
            self.cls:list = card['class']

    def add_owner(self, user_id:int):
        """Adds an owner to a card entry in my db. Only used in Card().add_card()"""
        self.owners.append(user_id)
        items.update_one({'_id': self.id}, {'$set': {'owners': self.owners}})
        return

    def remove_owner(self, user_id:int):
        """Removes an owner from a card entry in my db. Only used in Card().remove_card()"""
        self.owners.remove(user_id)
        items.update_one({'_id': self.id}, {'$set': {'owners': self.owners}})
        return

    def __eq__(self, other):
        """"This function isn't used but I thought it would be nice to implement"""
        if isinstance(other, Card): # Checking if the other card is a Card object
            if self.id == other.id:
                return True
            else:
                return False
        if isinstance(other, int): # Checking if just the card id was passed
            if self.id == other:
                return True
            else: 
                return False
        if isinstance(other, list): # Checking if it's passed like it would be in an inventory [int, {"fake": bool}]
            if self.id == other[0]:
                return True
            else:
                return False
        if isinstance(other, dict): # Checking if it's passed from a pymongo items.find_one({"_id": int})
            if self.id == other['_id']:
                return True
            else:
                return False

class User():
    """This class allows me to handle a lot of user related actions more easily"""
    
    def __init__(self, user_id:int):
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
        self.all_cards:list = [*self.fs_cards, *self.rs_cards]
        self.badges:list = user['badges']
        self.is_premium:bool = len([x for x in self.badges if x in PATREON_TIERS.keys()]) > 0
        self.premium_tier:str = [x for x in self.badges if x in PATREON_TIERS.keys()][0] if self.is_premium else None
        self.votes = user["votes"] if "votes" in user else 0
        self.premium_guilds:dict = user["premium_guilds"] if "premium_guilds" in user else {}
        self.lootboxes:list = user["lootboxes"] if "lootboxes" in user else []
        self.weekly_cooldown = user["weekly_cooldown"] if "weekly_cooldown" in user else None

    @staticmethod
    def remove_all() -> str:
        """Removes all cards etc from every user. Only used for testing"""
        start = datetime.now()
        user = list()
        cards = list()
        for u in [x for x in teams.find()]:
            if 'cards' in u:
                user.append(u['id'])
        teams.update_many({'$or': [{'id': x} for x in user]}, {'$set': {'cards': {'rs': [], 'fs': [], 'effects': {}}, 'met_user': []}})

        for c in [x for x in items.find()]:
            if len(c['owners']) > 0:
                cards.append(c['_id'])
        items.update_many({'$or': [{'id': x} for x in cards]}, {'$set': {'owners': []}})

        return f"Removed all cards from {len(user)} user{'s' if len(user) > 1 else ''} and all owners from {len(cards)} card{'s' if len(cards) > 1 else ''} in {(datetime.now() - start).seconds} second{'s' if (datetime.now() - start).seconds > 1 else ''}"

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
    def add_empty(self, user_id, cards:bool=True):
        """Can be called when the user does not have an entry to make the class return empty objects instead of None"""
        if cards:
            return teams.update_one({'id': user_id}, {'$set': {'cards': {'rs': [], 'fs': [], 'effects': {}}, 'met_user': [], "votes": 0}})  
        else:
            return teams.insert_one({'id': user_id, 'points': 0, 'badges': [], 'cooldowndaily': '','cards': {'rs': [], 'fs': [], 'effects': {}}, 'met_user': [], "votes": 0}) 

    def add_badge(self, badge:str, premium=False):
        """Adds a badge to a user"""
        if badge.lower() in self.badges:
            raise TypeError("Badge already in possesion of user")
        self.badges.append(badge.lower())
        if premium:
            if 'premium' in self.badges:
                raise TypeError("Premium badge already in possesion of user")
            self.badges.append('premium')
        teams.update_one({'id': self.id}, {'$set': {'badges': self.badges}})

    def remove_badge(self, badge:str, premium=False):
        """Removes a badge from a user"""
        if not badge in self.badges:
            return # Don't really care if that happens
        self.badges.remove(badge)
        if premium:
            if 'premium' in self.badges:    
                self.badges.remove('premium')
        teams.update_one({'id': self.id}, {'$set': {'badges': self.badges}})

    def add_vote(self):
        """Keeps track of how many times a user has voted for Killua to increase the rewards over time"""
        teams.update_one({'id': self.id}, {'$set': {'votes': self.votes+1}})

    def add_premium_guild(self, guild_id:int) -> None:
        """Adds a guild to a users premium guilds"""
        self.premium_guilds[str(guild_id)] = datetime.now()
        teams.update_one({"id": self.id}, {"$set": {"premium_guilds": self.premium_guilds}})

    def remove_premium_guild(self, guild_id:int) -> None:
        """Removes a guild from a users premium guilds"""
        del self.premium_guilds[str(guild_id)]
        teams.update_one({"id": self.id}, {"$set": {"premium_guilds": self.premium_guilds}})

    def claim_weekly(self) -> None:
        """Sets the weekly cooldown new"""
        self.weekly_cooldown = datetime.now() +  timedelta(days=7)
        teams.update_one({"id": self.id}, {"$set": {"weekly_cooldown": self.weekly_cooldown}})

    def has_lootbox(self, box:int) -> bool:
        """Returns wether the user has the lootbox specified"""
        return box in self.lootboxes

    def add_lootbox(self, box:int) -> None:
        """Adds a lootbox to a users inventory"""
        self.lootboxes.append(box)
        teams.update_one({"id": self.id}, {"$set": {"lootboxes": self.lootboxes}})

    def remove_lootbox(self, box:int) -> None:
        """Removes a lootbox from a user"""
        self.lootboxes.remove(box)
        teams.update_one({"id": self.id}, {"$set": {"lootboxes": self.lootboxes}})
        
    def has_rs_card(self, card_id:int, fake_allowed:bool=True) -> bool:
        """Checking if the user has a card specified in their restricted slots"""
        if card_id in [x[0] for x in self.rs_cards]:
            if fake_allowed is False and True in [x[1] for x in self.rs_cards if x[0] == card_id]: #Not pretty but should work
                return False
            return True
        else:
            return False

    def has_fs_card(self, card_id:int, fake_allowed:bool=True) -> bool:
        """Checking if the user has a card specified in their free slots"""
        fs = self.fs_cards
        if card_id in [x[0] for x in fs]:
            if fake_allowed is False:
                if True in [x[1]["fake"] for x in fs if x[0] == card_id]:
                    for x in [x for x in fs if x[0] == card_id and x[1]['fake'] == True]:
                        fs.remove([x[0], {"fake": True, "clone": x[1]["clone"]}])
                    if len([x for x in fs if x[0] == card_id]) == 0:
                        return False
            return True
        else:
            return False

    def has_any_card(self, card_id:int, fake_allowed:bool=True) -> bool:
        """Checks if the user has the card"""
        total = self.all_cards
        if card_id in [x[0] for x in total]:
            if fake_allowed is False:
                if True in [x[1]["fake"] for x in total if x[0] == card_id]:
                    for x in [x for x in total if x[0] == card_id and x[1]['fake'] == True]:
                        total.remove([x[0], {"fake": True, "clone": x[1]["clone"]}])
                    if len([x for x in total if x[0] == card_id]) == 0:
                        return False
            return True
        else:
            return False

    def remove_jenny(self, amount:int):
        """Removes x Jenny from a user"""
        if self.jenny < amount:
            raise Exception('Trying to remove more Jenny than the user has')
        teams.update_one({'id': self.id}, {'$set': {'points': self.jenny - amount}})
        return

    def add_jenny(self, amount:int):
        """Adds x Jenny to a users balance"""
        teams.update_one({'id': self.id}, {'$set': {'points': self.jenny + amount}})
        return

    def set_jenny(self, amount:int):
        """Sets the users jenny to the specified value. Only used for testing"""
        teams.update_one({'id': self.id}, {'$set': {'points': amount}})
        return

    def remove_card(self, card_id:int, remove_fake:bool=None, restricted_slot:bool=None, clone:bool=False):
        """Removes a card from a user"""
        card = Card(card_id)
        if self.has_any_card(card_id) is False:
            raise NotInPossesion('This card is not in possesion of the specified user!')

        def fake_check(card_list:list):
            indx = [x for x in card_list if x[0] == card_id]
            (indx.remove([card_id, {"fake": True, "clone": clone}]) for i in indx if card_list[i]['fake'] == True)
            if len(indx) == 0:
                return False
            else:
                return True

        def rc(fake:bool, restricted_slot:bool):

            if restricted_slot is False or (self.has_fs_card(card_id) and remove_fake is None):
                #Honestly I am not sure if what I am doing in this whole function works for all usecases it's intended to
                self.fs_cards.remove([card_id, {'fake': fake, "clone": clone}])
            elif restricted_slot is True:
                self.rs_cards.remove([card_id, {'fake': fake, "clone": clone}])
            if fake is False:
                card.remove_owner(self.id)
            teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': self.rs_cards, 'fs': self.fs_cards, 'effects': self.effects}}})
            return [card_id, {"fake": fake, "clone": clone}]

        def fake():
            if remove_fake is None:
                c = []
                if restricted_slot is True:
                    for x in self.rs_cards:
                        if x[0] == card_id:
                            c.append(x)
                elif restricted_slot is False:
                    for x in self.rs_cards:
                        if x[0] == card_id:
                            c.append(x)
                else:
                    if self.has_fs_card(card_id):
                        random_fake = random.choice([x[1]['fake'] for x in self.fs_cards if x[0] == card_id])
                    else:
                        random_fake = random.choice([x[1]['fake'] for x in self.rs_cards if x[0] == card_id])
                    return random_fake
                return random.choice(c)[1]["fake"]
            elif remove_fake is False:
                return False
            elif remove_fake is True:
                return True

        if self.has_fs_card(card_id) is False:
            if fake_check(self.rs_cards) is False and remove_fake is False:
                raise OnlyFakesFound('The user has no card with this id that is not a fake')
            else:
                if not restricted_slot: # This is needed if we want to force to take a card from the restricted slots
                    return rc(fake(), True)
                else:
                    return rc(fake(), restricted_slot)
        else:
            if fake_check(self.fs_cards) is False and remove_fake is False:
                if fake_check(self.rs_cards) is False and remove_fake is False:
                    raise OnlyFakesFound('The user has no card with this id that is not a fake')
                if not restricted_slot:
                    return rc(fake(), True)
                else:
                    return rc(fake(), restricted_slot)
            else:
                if not restricted_slot:
                    return rc(fake(), False)
                else:
                    return rc(fake(), restricted_slot)

    def add_card(self, card_id:int, fake:bool=False, clone:bool=False):
        """Adds a card to the the user"""
        card = Card(card_id)

        def ac(restricted_slot:bool=False):
            if restricted_slot is False:
                self.fs_cards.append([card_id, {'fake': fake, 'clone': clone}])
            elif restricted_slot is True:
                self.rs_cards.append([card_id, {'fake': fake, 'clone': clone}])
            if fake is False:
                card.add_owner(self.id)
            teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': self.rs_cards, 'fs': self.fs_cards, 'effects': self.effects}}})

        if self.has_rs_card(card.id) is False:
            if card_id < 100:
                ac(True)
                return
            ac()
            return

        if len(self.fs_cards) >= FREE_SLOTS:
            raise CardLimitReached('User reached card limit for free slots')

        ac()

    def count_card(self, card_id:int, including_fakes:bool=True) -> int:
        "Counts how many copies of a card someone has"
        card = Card(card_id)
        card_amount = 0
        if including_fakes is True:
            rs_cards = [x[0] for x in self.rs_cards]
            fs_cards = [x[0] for x in self.fs_cards]
        else:
            rs_cards = [x[0] for x in self.rs_cards if x[1]['fake'] == False]
            fs_cards = [x[0] for x in self.fs_cards if x[1]['fake'] == False]

        for x in [*rs_cards, *fs_cards]:
            if x == card.id:
                card_amount = card_amount+1

        return card_amount

    def add_multi(self, *args):
        """The purpose of this function is to be a faster alternative when adding multiple cards than for loop with add_card"""
        fs_cards = list()
        rs_cards = list()

        def fs_append(item:list):
            if len([*self.fs_cards, *fs_cards]) >= 40:
                    return fs_cards
            fs_cards.append(item)
            return fs_cards

        if len(args) == 1: # I might just pass all items in a list
            args = args[0]

        for item in args:
            if item[1]["fake"] is False:
                Card(item[0]).add_owner(self.id)
            if item[0] < 99:
                if not self.has_rs_card(item[0]):
                    if not item[0] in [x[0] for x in rs_cards]:
                        rs_cards.append(item)
                    else:
                        fs_cards = fs_append(item)
                else:
                    fs_cards = fs_append(item)
            else:
                fs_cards = fs_append(item)

        teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': [*self.rs_cards, *rs_cards], 'fs': [*self.fs_cards, *fs_cards], 'effects': self.effects}}})

    def has_defense(self) -> bool:
        """Checks if a user holds on to a defense spell card"""
        for x in DEFENSE_SPELLS:
            if x in [x[0] for x in self.fs_cards]:
                if self.has_any_card(x, False):
                    return True
        return False

    def swap(self, card_id:int): 
        """Swaps a card from the free slots with one from the restricted slots. Usecase: swapping fake and real card"""

        if (True in [x[1]['fake'] for x in self.rs_cards if x[0] == card_id] and False in [x[1]['fake'] for x in self.fs_cards if x[0] == card_id]):
            r = self.remove_card(card_id, remove_fake=True, restricted_slot=True)
            r2 = self.remove_card(card_id, remove_fake=False, restricted_slot=False)
            self.add_card(card_id, False, r[1]["clone"])
            self.add_card(card_id, True, r2[1]["clone"])
            return

        if (True in [x[1]['fake'] for x in self.fs_cards if x[0] == card_id] and False in [x[1]['fake'] for x in self.rs_cards if x[0] == card_id]):
            r = self.remove_card(card_id, remove_fake=True, restricted_slot=False)
            r2 = self.remove_card(card_id, remove_fake=False, restricted_slot=True)
            self.add_card(card_id, True, r[1]["clone"])
            self.add_card(card_id, False, r2[1]["clone"])
            return

        return False # Returned if the requirements haven't been met
            

    def add_effect(self, effect, value): 
        """Adds a card with specified value, easier than checking for appropriate value with effect name"""
        l = self.effects
        l[effect] = value
        teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': self.rs_cards, 'fs': self.fs_cards, 'effects': l}}})

    def remove_effect(self, effect):
        """Remove effect provided"""
        l = self.effects
        l.pop(effect, None)
        teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': self.rs_cards, 'fs': self.fs_cards, 'effects': l}}})

    
    def has_effect(self, effect) -> bool:
        """Checks if a user has an effect and returns what effect if the user has it"""
        if effect in self.effects:
            return True, self.effects[effect]
        else:
            return False, None

    def add_met_user(self, user_id:int):
        """Adds a user to a "previously met" list which is a parameter in some spell cards"""
        if not user_id in self.met_user:
            self.met_user.append(user_id)
            teams.update_one({'id': self.id}, {'$set': {'met_user': self.met_user}})

    def has_met(self, user_id:int) -> bool:
        """Checks if the user id provided has been met by the self.id user"""
        if user_id in self.met_user:
            return True
        else:
            return False

    def nuke_cards(self, t='all') -> bool:
        """A function only intended to be used by bot owners, not in any actual command, that's why it returns True, so the owner can see if it suceeded"""
        if t == 'all': 
            for card in [x[0] for x in self.all_cards]:
                try:
                    Card(card).remove_owner(self.id)
                except Exception:
                    pass
            teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': [], 'fs': [], 'effects': {}}}})
            return True
        if t == 'fs':
            for card in [x[0] for x in self.fs_cards]:
                try:
                    Card(card).remove_owner(self.id)
                except Exception:
                    pass
            teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': self.rs_cards, 'fs': [], 'effects': self.effects}}})
            return True
        if t == 'rs':
            for card in [x[0] for x in self.rs_cards]:
                try:
                    Card(card).remove_owner(self.id)
                except Exception:
                    pass
            teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': [], 'fs': self.fs_cards, 'effects': self.effects}}})
            return True
        if t == 'effects':
            teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': self.rs_cards, 'fs': self.fs_cards, 'effects': {}}}})
            return True

class TodoList():
    def __init__(self, list_id):
        td_list = todo.find_one({'_id' if str(list_id).isdigit() else 'custom_id': int(list_id) if str(list_id).isdigit() else list_id.lower()})
        if not td_list:
            raise TodoListNotFound

        self.id:int = td_list['_id']
        self.name:str = td_list['name']
        self.owner:int = td_list['owner']
        self.custom_id:str = td_list['custom_id']
        self.status:str = td_list['status']
        self.delete_done:bool = td_list['delete_done']
        self.viewer:list = td_list['viewer']
        self.editor:list = td_list['editor']
        self.todos:list = td_list['todos']
        self.created_at:str = td_list['created_at']
        self.spots:int = td_list['spots']
        self.views:int = td_list['views']
        self.thumbnail:str = td_list['thumbnail'] if 'thumbnail' in td_list else None
        self.color:int = td_list['color'] if 'color' in td_list else None
        self.description:str = td_list['description'] if 'description' in td_list else None

    def __len__(self) -> int:
        """Makes it nicer to get the "lenght" of a todo list, or rather the length of its todos"""
        return len(self.todos)

    @staticmethod
    def _generate_id() -> int:
        l = []
        while len(l) != 6:
            l.append(str(randint(0,9)))

        todo_id = todo.find_one({'_id': ''.join(l)})

        if todo_id is None:
            return int(''.join(l))
        else:
            return self._generate_id()

    @staticmethod
    def create(owner:int, title:str, status:str, done_delete:bool, custom_id:str=None) -> TodoList:
        """Creates a todo list and returns a TodoList class"""
        list_id = TodoList._generate_id()
        todo.insert_one({'_id': list_id, 'name': title, 'owner': owner, 'custom_id': custom_id, 'status': status, 'delete_done': done_delete, 'viewer': [], 'editor': [], 'todos': [{'todo': 'add todos', 'marked': None, 'added_by': 756206646396452975, 'added_on': (datetime.now()).strftime("%b %d %Y %H:%M:%S"), 'views':0, 'assigned_to': [], 'mark_log': []}], 'marks': [], 'created_at': (datetime.now()).strftime("%b %d %Y %H:%M:%S"), 'spots': 10, 'views': 0 })
        return TodoList(list_id)

    def delete(self) -> None:
        """Deletes a todo list"""
        todo.delete_one({'_id': self.id})

    def has_view_permission(self, user_id:int) -> bool:
        """Checks if someone has permission to view a todo list"""
        if self.status== 'private':
            if not (user_id in self.viewer or user_id in self.editor or user_id == self.owner):
                return False
        return True

    def has_edit_permission(self, user_id:int) -> bool:
        """Checks if someone has permission to edit a todo list"""
        if not (user_id in self.editor or user_id == self.owner):
            return False
        return True

    def add_view(self, viewer:int) -> None:
        """Adds a view to a todo lists viewcount"""
        if not viewer == self.owner and not viewer in self.viewer and viewer in self.editor:
            todo.update_one({'_id': self.id}, {'$set':{'views': self.views+1 }})

    def set_property(self, prop, value) -> None:
        """Sets/updates a certain property of a todo list"""
        todo.update_one({'_id': self.id}, {'$set':{prop: value}})

    def add_spots(self, spots) -> None:
        """Easy way to add max spots"""
        self.set_property('spots', self.spots+spots)

    def add_editor(self, user:int) -> None:
        """Easy way to add an editor"""
        self.editor.append(user)
        self.set_property('editor', self.editor)

    def add_viewer(self, user:int) -> None:
        """Easy way to add a viewer"""
        self.viewer.append(user)
        self.set_property('viewer', self.viewer)

    def kick_editor(self, editor:int) -> None:
        """Easy way to kick an editor"""
        self.editor.remove(editor)
        self.set_property('editor', self.editor)

    def kick_viewer(self, viewer:int) -> None:
        """Easy way to kick a viewer"""
        self.viewer.remove(viewer)
        self.set_property('viewer', self.viewer)

    def has_todo(self, task:int) -> bool:
        """Checks if a list contains a certain todo task"""
        try:
            if task == 0:
                raise Exception('Error!')
            self.todos[task-1]
        except Exception:
            return False
        return True

    def clear(self) -> None:
        """Removes all todos from a todo list"""
        self.todos = []
        self.set_property("todos", [])

class Todo(TodoList):

    def __init__(self, position:int, list_id):
        super().__init__(list_id)
        task = self.todos[position-1]

        self.todo:str = task['todo']
        self.marked:str = task['marked']
        self.added_by:int = task['added_by']
        self.added_on:str = task['added_on']
        self.views:int = task['views']
        self.assigned_to:list = task['assigned_to']
        self.mark_log:list = task['mark_log']

class Guild():

    def __init__(self, guild_id:int):
        g = guilds.find_one({'id': guild_id})
        if not g:
            self.add_default(guild_id)
            g = guilds.find_one({'id': guild_id})

        self.id:int = guild_id
        self.badges:list = g['badges']
        #self.points = g['points'] Idk why I have that, unused for now
        self.prefix:str = g['prefix']
        self.is_premium:bool = ('partner' in self.badges or 'premium' in self.badges)
        
        if 'tags' in g:
            self.tags = g['tags']

    @classmethod
    def add_default(self, guild_id:int):
        """Adds a guild to the database"""
        guilds.insert_one({'id': guild_id, 'points': 0,'items': '','badges': [], 'prefix': 'k!'})

    def delete(self):
        """Deletes a guild from the database"""
        guilds.delete_one({'id': self.id})

    def change_prefix(self, prefix:str):
        "Changes the prefix of a guild"
        guilds.update_one({'id': self.id}, {'$set': {'prefix': prefix}})

    def add_premium(self):
        """Adds premium to a guild"""
        guilds.update_one({"id": self.id}, {"$push": {"badges": "premium"}})

    def remove_premium(self):
        """"Removes premium from a guild"""
        guilds.update_one({"id": self.id}, {"$pull": {"badges": "premium"}})