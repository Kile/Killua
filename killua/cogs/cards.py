import discord
from discord.ext import commands, tasks
import random
from random import randint
from datetime import datetime, timedelta
import pymongo
from pymongo import MongoClient
import json
import asyncio
from itertools import zip_longest
import math
import typing
from PIL import Image, ImageFont, ImageDraw
import io
import aiohttp
from killua.functions import custom_cooldown, blcheck

with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())

cluster = MongoClient(config['mongodb'])
db = cluster['Killua']
teams = db['teams']
items = db['items']
guilds = db['servers']
general = cluster['general']
shop = general['shop']

###################TODO TODO TODO####################
'''
             TO-DOs

1) k!book showing the cards you have in book format like in the anime |Done|

2) k!hunt Hunting for monsters |Done|

3) k!shop you can buy cards, daily offers, some stuff |Done|

4) k!sell sell a card |Done|

5) k!give modify to work with items |Done|

6) Add support for all spell cards usable with k!use |Done (24/24)|
'''
###################TODO TODO TODO####################


#Data structure for card system:

example = {
    "effects":{
      "effect": "time/amount"
    },
    "rs": [ #Stands for restricted slots
      [1,{"fake": True, "clone": False}],
      [4, {"fake": False, "clone": False}],
      [6, {"fake": False, "clone": True}],
      [7, {"fake": False, "clone": False}]
    ],
    "fs": [ #Stands for free slots
      [1004, {"fake": True, "clone": False}],
      [1008, {"fake": False, "clone": False}]
    ],
    "met_users": [
        606162661184372736,
        258265415770177536
    ]
}

# I am NOT writing a detailed description of every function in here, just a brief description for functions in classes

cached_cards = {}

ALLOWED_AMOUNT_MULTIPLE = 3
FREE_SLOTS = 40
DEF_SPELLS= [1003, 1004, 1019]
VIEW_DEF_SPELLS = [1025]
INDESTRUCTABLE = [1026]

PRICES:dict = {
    'S': 10000,
    'A': 5000,
    'B': 3000,
    'C': 1500,
    'D': 800,
    'E': 500,
    'F': 200,
    'G': 100
}

BOOK_PAGES = [
"""
📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖


A beginners guide of the greed island card system


📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖📖
""",
f"""If you are not familiar with how this works in the anime:
The main goal of the game is to obtain all 100 cards in the book. How hard it is to
obtain a card is determined by it's **rank**. You can find it on the top right of the 
card. Next to it to the right is a number. This number times {ALLOWED_AMOUNT_MULTIPLE} is the 
maximum amount of those cards to exist globally. If that limit is exceeded you can't 
obtain any more cards unless someone looses one of their copies which means one 
other person can obtain the card again""",

f"""On the top left, you can see the card number. Typically, spell cards have a number
one thousand and ... and item cards have a number less than 100. Cards with a 
number below 100 count towards your goal of colleting all 100 **restricted slot** 
cards. When you obtain a card which has an id below 100 but you already have one 
in your restricted slots, or the card id is above 100, the card comes into your 
**free slots**. You can have a maximum of {FREE_SLOTS} cards in your free slots""",

"""I have mentioned before that there are **spell cards**. You can use them to steal 
cards from other users, gamble and a lot more. To use a spell card, use 
`k!use <card> <arguments>`. Some spell cards only work in a **short range**. 
In discord terms that means that the target must have send a message
recently in the channel the command is used in. You can also use permament 
spell cards to protect yourself from others or tranform cards into fakes.""",

"""A word about **fakes**. The main usecase I see them as is bait. You can't 
sell fakes, you can't use them and they don't count towards the 100 card goal. 
If you want to swap out a fake in your album with a real card in your free slots 
or the other way around, use `k!swap <card_id>`. If you want to get rid of a fake, 
make sure it's in your free slots and discard it with `k!discard <card_id>`""",

"""You have reached the end of the introduction!

Now it's time for you to explore the world of cards, steal, collect, form alliances and so on. 

Do you want to add a card to the game you have a good idea for? That is possible, if you can make the
card design with image we will be happy to have a look at your idea!

Have fun hunters
- The Gamemaster"""
]

class CardNotFound(Exception):
    def __init__(self, msg=None):
        super().__init__()
        self.text = msg

class NotInPossesion(Exception):
    def __init__(self, msg=None):
        super().__init__()
        self.text = msg

class OnlyFakesFound(Exception):
    def __init__(self, msg=None):
        super().__init__()
        self.text = msg

class CardLimitReached(Exception):
    def __init__(self, msg=None):
        super().__init__()
        self.text = msg
    

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
            print('Yes')
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

    @staticmethod
    def remove_all():
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
    def is_registered(cls, user_id:int):
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
            return teams.update_one({'id': user_id}, {'$set': {'cards': {'rs': [], 'fs': [], 'effects': {}}, 'met_user': []}})  
        else:
            return teams.insert_one({'id': user_id, 'points': 0, 'badges': [], 'cooldowndaily': '','cards': {'rs': [], 'fs': [], 'effects': {}}, 'met_user': []}) 
        
    def has_rs_card(self, card_id:int, fake_allowed:bool=True):
        """Checking if the user has a card specified in their restricted slots"""
        if card_id in [x[0] for x in self.rs_cards]:
            if fake_allowed is False and True in [x[1] for x in self.rs_cards if x[0] == card_id]: #Not pretty but should work
                return False
            return True
        else:
            return False

    def has_fs_card(self, card_id:int, fake_allowed:bool=True):
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

    def has_any_card(self, card_id:int, fake_allowed:bool=True):
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

    def remove_card(self, card_id:int, remove_fake:bool=None, payed:bool=False, restricted_slot:bool=None, clone:bool=False):
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

        if payed is not False:
            self.add_jenny(PRICES[card.rank])

        return 

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
            return ac()

        if len(self.fs_cards) >= FREE_SLOTS:
            raise CardLimitReached('User reached card limit for free slots')

        ac()

    def count_card(self, card_id:int, including_fakes:bool=True):
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

    def has_defense(self):
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

    
    def has_effect(self, effect):
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

    def has_met(self, user_id:int):
        """Checks if the user id provided has been met by the self.id user"""
        if user_id in self.met_user:
            return True
        else:
            return False

    def nuke_cards(self, t='all'):
        """A function only intended to be used by bot owners, not in any actual command, that's why it returns True, so the owner can see if it suceeded"""
        if t == 'all': 
            for card in [x[0] for x in self.all_cards]:
                try:
                    Card(card).remove_owner(self.id)
                except:
                    pass
            teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': [], 'fs': [], 'effects': {}}}})
            return True
        if t == 'fs':
            for card in [x[0] for x in self.fs_cards]:
                try:
                    Card(card).remove_owner(self.id)
                except:
                    pass
            teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': self.rs_cards, 'fs': [], 'effects': self.effects}}})
            return True
        if t == 'rs':
            for card in [x[0] for x in self.rs_cards]:
                try:
                    Card(card).remove_owner(self.id)
                except:
                    pass
            teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': [], 'fs': self.fs_cards, 'effects': self.effects}}})
            return True
        if t == 'effects':
            teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': self.rs_cards, 'fs': self.fs_cards, 'effects': {}}}})
            return True

class Cards(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.shop_update.start()
        
    @tasks.loop(hours=6)
    async def shop_update(self):
        #There have to be 4-5 shop items, inserted into the db as a list with the card numbers
        #the challange is to create a balanced system with good items rare enough but not too rare
        shop_items:list = []
        number_of_items = randint(3,5) #How many items the shop has
        if randint(1,100) > 95:
            #Add a S/A card to the shop
            thing = [i['_id'] for i in items.find({'type': 'normal', 'rank': random.choice(['A', 'S'])})]
            shop_items.append(random.choice(thing))
        if randint(1,100) > 20: #80% chance for spell
            if randint(1, 100) > 95: #5% chance for a good spell (they are rare)
                spells = [s['_id'] for s in items.find({'type': 'spell', 'rank': 'A'})]
                shop_items.append(random.choice(spells))
            elif randint(1,50): #50% chance of getting a medium good card
                spells = [s['_id'] for s in items.find({'type': 'spell', 'rank': random.choice(['B', 'C'])})]
                shop_items.append(random.choice(spells))
            else: #otherwise getting a fairly normal card
                spells = [s['_id'] for s in items.find({'type': 'spell', 'rank': random.choice(['D', 'E', 'F', 'G'])})]
                shop_items.append(random.choice(spells))

            while len(shop_items) != number_of_items: #Filling remaining spots
                thing = [t['_id'] for t in items.find({'type': 'normal', 'rank': random.choice(['D', 'B'])})] 
                #There is just one D item so there is a really high probablility of it being in the shop EVERY TIME
                t = random.choice(thing)
                if not t in shop_items:
                    shop_items.append(t)

            log = shop.find_one({'_id': 'daily_offers'})['log']
            if randint(1, 10) > 6: #40% to have an item in the shop reduced
                reduced_item = randint(0, len(shop_items)-1)
                reduced_by = randint(15, 40)
                print('Updated shop with following cards: ' + ', '.join([str(x) for x in shop_items])+f', reduced item number {shop_items[reduced_item]} by {reduced_by}%')
                log.append({'time': datetime.now(), 'items': shop_items, 'reduced': {'reduced_item': reduced_item, 'reduced_by': reduced_by}})
                shop.update_many({'_id': 'daily_offers'}, {'$set': {'offers': shop_items, 'log': log, 'reduced': {'reduced_item': reduced_item, 'reduced_by': reduced_by}}})
            else:
                print('Updated shop with following cards: ' + ', '.join([str(x) for x in shop_items]))
                log.append({'time': datetime.now(), 'items': shop_items, 'redued': None})
                shop.update_many({'_id': 'daily_offers'}, {'$set': {'offers': shop_items, 'log': log, 'reduced': None}})

    @custom_cooldown(5)
    @commands.command()
    async def book(self, ctx, page:int=None):
        #h Allows you to take a look at your cards
        #u book <page(optional)>
        if blcheck(ctx.author.id) is True:
            return
        
        if len(User(ctx.author.id).all_cards) == 0:
            return await ctx.send('You don\'t have any cards yet!')

        if page:
            if page > 7+math.ceil(len(User(ctx.author.id).fs_cards)/18) or page < 1:
                return await ctx.send(f'Please choose a page number between 1 and {6+math.ceil(len(User(ctx.author.id).fs_cards)/18)}')

        return await paginator(self, ctx, 1 if not page else page, first_time=True)

    @commands.command(aliases=['store'])
    async def shop(self, ctx):
        #h Shows the current cards for sale
        #u shop
        if blcheck(ctx.author.id) is True:
            return
        
        sh = shop.find_one({'_id': 'daily_offers'})
        shop_items:list = sh['offers']
        formatted = list()
        if not sh['reduced'] is None:
            reduced_item = sh['reduced']['reduced_item']
            reduced_by = sh['reduced']['reduced_by']
            formatted = format_offers(shop_items, reduced_item, reduced_by)
            embed = discord.Embed(title='Current Card shop', description=f'**{items.find_one({"_id": shop_items[reduced_item]})["name"]} is reduced by {reduced_by}%**')
        else:
            formatted:list = format_offers(shop_items)
            embed = discord.Embed(title='Current Card shop')

        embed.color = 0x1400ff
        embed.set_thumbnail(url='https://static.wikia.nocookie.net/hunterxhunter/images/0/08/Spell_Card_Store.png/revision/latest?cb=20130328063032')
        for item in formatted:
            embed.add_field(name=item['name'], value=item['value'], inline=False)

        await ctx.send(embed=embed)

    @custom_cooldown(7400)
    @commands.command()
    async def buy(self, ctx, item:int):
        #h Buy a card from the shop with this command
        #u buy <card_id>
        if blcheck(ctx.author.id) is True:
            return
        
        shop_data = shop.find_one({'_id': 'daily_offers'})
        shop_items = shop_data['offers']
        user = User(ctx.author.id)
        price = int()

        try:
            card = Card(item)
        except CardNotFound:
            return await ctx.send(f'This card is not for sale at the moment! Find what cards are in the shop with `{self.client.command_prefix(self.client, ctx.message)[2]}shop`')

        if not item in shop_items:
            return await ctx.send(f'This card is not for sale at the moment! Find what cards are in the shop with `{self.client.command_prefix(self.client, ctx.message)[2]}shop`')

        if not shop_data['reduced'] is None:
            if shop_items.index(card.id) == shop_data['reduced']['reduced_item']:
                price = int(PRICES[card.rank] - int(PRICES[card.rank] * shop_data['reduced']['reduced_by']/100))
            else:
                price = PRICES[card.rank]
        else:
            price = PRICES[card.rank]

        if len(card.owners) >= (card.limit * ALLOWED_AMOUNT_MULTIPLE):
            return await ctx.send('Unfortunatly the global maximal limit of this card is reached! Someone needs to sell their card for you to buy one or trade/give it to you')

        if len(user.fs_cards) >= FREE_SLOTS:
            return await ctx.send(f'Looks like your free slots are filled! Get rid of some with `{self.client.command_prefix(self.client, ctx.message)[2]}sell`')

        if user.jenny < price:
            return await ctx.send(f'I\'m afraid you don\'t have enough Jenny to buy this card. Your balance is {user.jenny} while the card costs {price} Jenny')
        try:
            user.add_card(item)
        except Exception as e:
            if isinstance(e, CardLimitReached):
                return await ctx.send(f'Free slots card limit reached (`{FREE_SLOTS}`)! Get rid of one card in your free slots to add more cards with `{self.client.command_prefix(self.client, ctx.message)[2]}sell <card>`')
            else:
                print(e)

        user.remove_jenny(price) #Always putting substracting points before giving the item so if the payment errors no iten is given
        return await ctx.send(f'Sucessfully bought card number `{card.id}` {card.emoji} for {price} Jenny. Check it out in your inventory with `{self.client.command_prefix(self.client, ctx.message)[2]}book`!')

    @custom_cooldown(30)
    @commands.command()
    async def sell(self, ctx, item:int, amount=1):
        #h Sell any amount of cards you own
        #u sell <card_id> <amount(optional)>
        if blcheck(ctx.author.id) is True:
            return
        
        user = User(ctx.author.id)
        if amount < 1:
            amount = 1
        if len(user.all_cards) == 0:
            return await ctx.send('You don\'t have any cards yet!')
        try:
            card = Card(item)
        except CardNotFound:
            return await ctx.send(f'A card with the id `{item}` does not exist')
        in_possesion = user.count_card(card.id, including_fakes=False)

        if in_possesion < amount:
            return await ctx.send(f'Seems you don\'t own enough copis of this card. You own {in_possesion} cop{"y" if in_possesion == 1 else "ies"} of this card')
        
        await ctx.send(f'You will recieve {PRICES[card.rank]*amount} Jenny for selling {"this card" if amount == 1 else "those cards"}, do you want to proceed? **[y/n]**')

        def check(msg):
            return msg.author.id == ctx.author.id and (msg.content.lower() in ['y', 'n'])
        try:
            msg = await self.client.wait_for('message', timeout=20, check=check)
        except asyncio.TimeoutError:
            return await ctx.send('Timed out!')
        else:
            if msg.content.lower() == 'n':
                return await ctx.send('Sucessfully canceled!')
            
            card_amount = user.count_card(item, False)

            if not amount >= amount:
                return await ctx.send('Seems like you don\'t own enoug ch non-fake copies of this card you try to sell')
            else:
                for i in range(amount):
                    user.remove_card(item, False)
                user.add_jenny(PRICES[card.rank]*amount)
                await ctx.send(f'Sucessfully sold {amount} cop{"y" if amount == 1 else "ies"} of card number {item} for {PRICES[card.rank]*amount} Jenny!')

    @custom_cooldown(2)
    @commands.command()
    async def swap(self, ctx, card_id:int):
        #h Allows you to swap cards from your free slots with the restrcited slots and the other way around
        #u swap <card_id>
        if blcheck(ctx.author.id) is True:
            return
        
        user = User(ctx.author.id)
        if len(user.all_cards) == 0:
            return await ctx.send('You don\'t have any cards yet!')
        try:
            card = Card(card_id)
        except CardNotFound:
            return await ctx.send('Please use a valid card number!')

        sw = user.swap(card_id)

        if sw is False:
            return await ctx.send(f'You don\'t own a fake and real copy of card `{card.name}` you can swap out!')
        
        await ctx.send(f'Successfully swapped out card No. {card_id}')

    @commands.command()
    async def hunt(self, ctx, end:str=None):
        #h Go on a hunt! The longer you are on the hunt, the better the rewards!
        #u hunt <end(optional)>
        if blcheck(ctx.author.id) is True:
            return
        
        user = User(ctx.author.id)
        has_effect, value = user.has_effect('hunting')

        if end:
            if not end.lower() == 'end':
                pass
            elif has_effect is True:
                difference = datetime.now() - value
                if int(difference.seconds/60/60+difference.days*24*60*60) < 12: # I don't think timedelta has an hours or minutes property :c
                    return await ctx.send('You must be at least hunting for twelve hours!')

                minutes = int(difference.seconds/60+difference.days*24*60)
                reward_score = minutes/10000 # There are 10080 minutes in a week if I'm not completely wrong
                
                rewards = construct_rewards(reward_score)
                r = f'You\'ve been hunting for {difference.days} days, {int((difference.seconds/60)/60)} hours, {int(difference.seconds/60)-(int((difference.seconds/60)/60)*60)} minutes and {int(difference.seconds)-(int(difference.seconds/60)*60)} seconds. You brought back the following items from your hunt: \n\n'
                def form(rewards, r):
                    r_l = list()
                    l = list()
                    
                    for rew in rewards:
                        for i in range(rew[1]):
                            if len([*user.fs_cards,*[x for x in l if x[0] > 99 and not user.has_rs_card(x[0])]]) >= 40 and (rew[0] > 99 or (not user.has_rs_card(rew[0]) and rew[0] < 100)):
                                r = f':warning:*Your free slot limit has been reached! Sell some cards with `{self.client.command_prefix(self.client, ctx.message)[2]}sell`*:warning:\n\n' + r
                                return r_l, r, l
                            l.append([rew[0], {"fake": False, "clone": False}])
                        r_l.append(f'{rew[1]}x **{Card(rew[0]).name}**{Card(rew[0]).emoji}')
                    return r_l, r, l

                r_l, r, l = form(rewards, r)

                embed = discord.Embed.from_dict({
                    'title': 'Hunt returned!',
                    'description': r + ('\n'.join(r_l) if len(r_l) else "Seems like you didn't bring anything back from your hunt"),
                    'color': 0x1400ff
                })
                user.remove_effect('hunting')
                user.add_multi(l)
                return await ctx.send(embed=embed)
                
            elif end.lower() == 'end': 
                return await ctx.send(f'You aren\'t on a hunt yet! Start one with `{self.client.command_prefix(self.client, ctx.message)[2]}hunt`')

        if user.has_effect('hunting')[0] is True:
            return await ctx.send(f'You are already on a hunt! Get the results with `{self.client.command_prefix(self.client, ctx.message)[2]}hunt end`')
        user.add_effect('hunting', datetime.now())
        await ctx.send('You went hunting! Make sure to claim your rewards at least twelve hours from now, but remember, the longer you hunt, the more you get')

    @custom_cooldown(120)
    @commands.command(aliases=['approach'])
    async def meet(self, ctx, user:discord.Member):
        #h Meet a user who has recently send a message in this channel to enable certain spell card effects
        #u meet <user>
        if blcheck(ctx.author.id) is True:
            return
        
        author = User(ctx.author.id)
        past_users = list()
        if user.bot:
            return await ctx.send('You can\'t interact with bots with this command')
        async for message in ctx.channel.history(limit=20):
            if message.author.id not in past_users:
                past_users.append(message.author.id)

        if not user.id in past_users:
            return await ctx.send('The user you tried to approach has not send a message in this channel recently')

        if user.id in author.met_user:
            await ctx.message.delete()
            return await ctx.send(f'You already have `{user}` in the list of users you met, {ctx.author.name}', delete_after=2)

        author.add_met_user(user.id)
        await ctx.message.delete()
        return await ctx.send(f'Done {ctx.author.mention}! Successfully added `{user}` to the list of people you\'ve met', delete_after=5)

    @commands.command()
    async def give(self, ctx, other:discord.Member, t:str, item:int):
        #h If you're feeling generous give another user cards or jenny. Available types are jenny and card
        #u give <user> <type> <card_id/amount>
        if blcheck(ctx.author.id) is True:
            return
        
        if other == ctx.author:
            return await ctx.send('You can\'t give yourself anything!')
        if other.bot:
            return await ctx.send('🤖')
        user = User(ctx.author.id)
        o = User(other.id)
        if t.lower() == 'jenny':
            if item < 1:
                return await ctx.send(f'You can\'t transfer less than 1 Jenny!')
            if user.jenny < item:
                return await ctx.send('You can\'t transfer more Jenny than you have')
            o.add_jenny(item)
            user.remove_jenny(item)
            return await ctx.send(f'✉️ transferred {item} Jenny to `{other}`!')
        elif t.lower() == 'card':
            try:
                card = Card(item)
            except CardNotFound:
                return await ctx.send('Invalid card number')
            if user.has_any_card(item, False) is False:
                return await ctx.send('You don\'t have any not fake copies of this card!')
            if (len(o.fs_cards) >= 40 and item < 100 and o.has_rs_card(item)) or (len(o.fs_cards) >= 40 and item > 99):
                return await ctx.send('The user you are trying to give the cards\'s free slots are full!')

            removed_card = user.remove_card(item)
            o.add_card(item, clone=removed_card[1]["clone"])
            return await ctx.send(f'✉️ gave `{other}` card No. {item}!')

        else:
            await ctx.send('You need to choose a valid type (`card`|`jenny`)')
            
    @commands.command()
    async def discard(self, ctx, card:int):
        #h Discard a card you want to get rid of with this command
        #u discard <card_id>
        if blcheck(ctx.author.id) is True:
            return
        
        user = User(ctx.author.id)
        try:
            card = Card(card)
        except CardNotFound:
            return await ctx.send('This card does not exist!')

        if not user.has_any_card(card.id):
            return await ctx.send('You are not in possesion of this card!')

        await ctx.send(f'Do you really want to throw this card away? (be aware that this will throw the first card you own with this id away, if you want to get rid of a fake swap it out of your album with `{self.client.command_prefix(self.client, ctx.message)[2]}swap <card_id>`) **[y/n]**')

        def check(msg):
            return msg.author.id == ctx.author.id and (msg.content.lower() in ['y', 'n'])
        try:
            msg = await self.client.wait_for('message', timeout=20, check=check)
        except asyncio.TimeoutError:
            return await ctx.send('Timed out!')
        else:
            if msg.content.lower() == 'n':
                await msg.delete()
                await ctx.message.delete()
                return await ctx.send('Sucessfully canceled!')

            elif msg.content.lower() == 'y':
                user.remove_card(card.id)
                await msg.delete()
                await ctx.message.delete()
                await ctx.send(f'Successfully thrown away card No. `{card.id}`')

    @custom_cooldown(4)
    @commands.command()
    async def use(self, ctx, item: typing.Union[int,str], args: typing.Union[discord.Member, str, int]=None, add_args:int=None):
        #h Use spell cards you own with this command! Focus on offense or defense, team up with your friends or steal their cards in their sleep!
        #u use <card_id> <required_arguments>
        if blcheck(ctx.author.id) is True:
            return
        
        if isinstance(item, str):
            if not item.lower() == 'booklet':
                return await ctx.send('Either use a spell card with this command or the booklet')
            return await book_paginator(self, ctx, 1, first_time=True)

        if not item in [x[0] for x in User(ctx.author.id).fs_cards] and not item in [1036]:
            return await ctx.send('You are not in possesion of this card!')

        if isinstance(args, discord.Member):
            if args.id == ctx.author.id:
                return await ctx.send('You can\'t use spell cards on yourself')

        elif args:
            if args.isdigit():
                args = int(args)
                if args < 1:
                    return await ctx.send('You can\'t use an integer less than 1')
        # This can be made a bit prettier with the new python `case` but it's still not optimal at all.
        # Not wanting to use eval I don't have an other solution at the moment
        if item == 1001:
            return await card_1001(self, ctx, args)
        elif item == 1002:
            return await card_1002(self, ctx, args)
        elif item == 1007:
            return await card_1007(self, ctx, args)
        elif item == 1008:
            return await card_1008(self, ctx, args)
        elif item == 1010:
            return await card_1010(self, ctx, args)
        elif item == 1011:
            return await card_1011(self, ctx, args)
        elif item == 1015:
            return await card_1015(self, ctx, args)
        elif item == 1018:
            return await card_1018(self, ctx)
        elif item == 1020:
            return await card_1020(self, ctx, args)
        elif item == 1021:
            return await card_1021(self, ctx, args, add_args)
        elif item == 1024:
            return await card_1024(self, ctx, args)
        elif item == 1026:
            return await card_1026(self, ctx, args)
        elif item == 1028:
            return await card_1028(self, ctx, args)
        elif item == 1029:
            return await card_1029(self, ctx, args)
        elif item == 1031:
            return await card_1031(self, ctx, args)
        elif item == 1032:
            return await card_1032(self, ctx)
        elif item == 1033:
            return await card_1033(self, ctx, args)
        elif item == 1035:
            return await card_1035(self, ctx, args)
        elif item == 1036:
            return await card_1036(self, ctx, args, add_args)
        elif item == 1038:
            return await card_1038(self, ctx, args)

        if item in [*DEF_SPELLS, *VIEW_DEF_SPELLS]:
            return await ctx.send('You can only use this card in response to an attack!')
        await ctx.send('Invalid card!')

    @commands.command()
    async def gain(self, ctx, t:str, item:str):
        #h An owner restricted command allowing the user to obtain any card or amount of jenny
        #u gain <type> <card_id/amount>
        if not ctx.author.id == 606162661184372736:
            return
        user = User(ctx.author.id)
        if not t.lower() in ["jenny", "card"]:
            return await ctx.send(f'You need to provide a valid type! `{self.client.command_prefix(self.client, ctx.message)[2]}gain <jenny/card> <amount/id>`')
        if t.lower() == 'card':
            try:
                item = int(item)
                card = Card(item)
            except CardNotFound:
                return await ctx.send('Invalid card id')
            if len(card.owners) >= card.limit * ALLOWED_AMOUNT_MULTIPLE:
                return await ctx.send('Sorry! Global card limit reached!')
            if len(user.fs_cards) >= FREE_SLOTS and (item > 99 or item in [x[0] for x in user.rs_cards]):
                return await ctx.send('Seems like you have no space left in your free slots!')
            user.add_card(item)
            return await ctx.send(f'Added card "{card.name}" to your inventory')

        if t.lower() == 'jenny':
            if not item.isdigit():
                return await ctx.send('Please provide a valid amount of jenny!')
            item = int(item)
            if item < 1:
                return await ctx.send('Please provide a valid amount of jenny!')
            if item > 20000:
                return await ctx.send('Be reasonable.')
            user.add_jenny(item)
            return await ctx.send(f'Added {item} Jenny to your account')

async def card_1038(self, ctx, card_id:int, without_removing=False):
    if not isinstance(card_id, int):
        return await ctx.send('Invalid arguments')
    
    try:
        card = Card(card_id)
    except CardNotFound:
        return await ctx.send('Invalid card!')
    if card.id == 0:
        return await ctx.send('Invalid card!')
    if without_removing is False:
        User(ctx.author.id).remove_card(1038)
    real_owners = list()
    for o in card.owners: 
        # Get the total number of owners
        if not o in real_owners:
            real_owners.append(o)
    embed = discord.Embed.from_dict({
        'title': f'Infos about card {card.name}',
        'description': f'**Total copies in circulation**: {len(card.owners)}\n\n**Total owners**: {len(real_owners)}',
        'image': {'url': card.image_url},
        'color': 0x1400ff
    })
    return await ctx.send(embed=embed)

async def card_1036(self, ctx, effect:str, card_id:int):
    user = User(ctx.author.id)
    effect = str(effect)
    if not '1036' in user.effects and not user.has_fs_card(1036):
        return await ctx.send('You need to have used the card 1036 once to use this command')
    if user.has_fs_card(1036) and not '1036' in user.effects:
        user.remove_card(1036)
        user.add_effect('1036', datetime.now())
    if not effect.lower() in ["list", "analysis", "1031", "1038"]:
        return await ctx.send(f'Invalid effect to use! You can use either `analysis` or `list` with this card. Usage: `{self.client.command_prefix(self.client, ctx.message)[2]}use 1036 <list/analysis> <card_id>`')

    if effect.lower() in ["list", "1038"]:
        return await card_1038(self, ctx, card_id, True)
    if effect.lower() in ["analysis", "1031"]:
        return await card_1031(self, ctx, card_id, True)

async def card_1035(self, ctx, page:int):
    if not isinstance(page, int):
        return await ctx.send('You need to provide a valid integer as an argument')
    user = User(ctx.author.id)
    if page > 6 or page < 1:
        return await ctx.send('You need to choose a page between 1 and 6')
    if user.has_effect(f'page_protection_{page}')[0]:
        return await ctx.send('This page is already protected!')
    user.add_effect(f'page_protection_{page}', datetime.now()) # The value doesn't matter here
    return await ctx.send(f'Success! Page {page} is now permanently protected')
 
async def card_1033(self, ctx, card_id:int):
    if not isinstance(card_id, int):
        return await ctx.send('You need to provide a valid integer as an argument')
    user = User(ctx.author.id)
    l = [x for x in user.all_cards if (x[1]["fake"] is True or x[1]["clone"] is True) and x[0] == card_id]
    if len(l) == 0:
        return await ctx.send('You don\'t own a copy of this card that is not an original')

    user.remove_card(card_id, remove_fake=l[0][1]["fake"], clone=l[0][1]["clone"])
    await ctx.send("Done, tranformed the fake and thus destroyed it")

async def card_1032(self, ctx):
    user = User(ctx.author.id)
    if len(user.fs_cards) >= FREE_SLOTS:
        return await ctx.send('You can only use this card with space in your free slots!')
    c = random.choice([x['_id'] for x in items.find({'type': 'normal'}) if x['rank'] != 'SS'])
    user.remove_card(1032)
    if len(Card(c).owners) >= Card(c).limit*ALLOWED_AMOUNT_MULTIPLE:
        return await ctx.send('Sadly the card limit of the card "Lottery" was about to transorm into is reached. Lottery will be used up anyways')
    user.add_card(c)
    await ctx.send(f'Successfully added card No. {c} to your inventory')

async def card_1031(self, ctx, card_id:int, without_removing=False):
    try:
        card = Card(card_id)
    except CardNotFound:
        return await ctx.send('Invalid card!')
    if card.id == 0:
        return await ctx.send('Invalid card!')
    if without_removing is False:
        User(ctx.author.id).remove_card(1031)
    placeholder_name = f"**Class:** {', '.join(card.cls)}\n**Range:** {card.range}\n\n" if card.type == "spell" else "\n"
    embed = discord.Embed.from_dict({
        'title': f'Info about card {card_id}',
        'thumbnail': {'url': card.image_url},
        'color': 0x1400ff,
        'description': f'**Name:** {card.name} {card.emoji}\n**Type:** {card.type.replace("normal", "item")}\n**Rank:** {card.rank}\n**Limit:** {card.limit*ALLOWED_AMOUNT_MULTIPLE}\n{placeholder_name}{card.description}'
    })
    await ctx.send(embed=embed)

async def card_1029(self, ctx, member:discord.Member):
    if not isinstance(member, discord.Member):
        return await ctx.send('Invalid argument used with card number 10029')
    if member.bot:
        return await ctx.send('🤖')
    if (await check_circumstances(ctx, member)) is not True:
        return
    other = User(member.id)
    user = User(ctx.author.id)
    if len(other.rs_cards) == 0:
        return await ctx.send('This user has no card in their free slots')
    c = random.choice([x for x in other.rs_cards if not x[0] in INDESTRUCTABLE])
    user.remove_card(1029)
    if await check_defense(self, ctx, member, 1029, c[0]) is True:
        return
    rc = other.remove_card(c[0], remove_fake=c[1]["fake"], restricted_slot=True, clone=c[1]["clone"])
    return await ctx.send(f'Done, you destroyed card No. {rc[0]}!')

async def card_1028(self, ctx, member:discord.Member):
    if not isinstance(member, discord.Member):
        return await ctx.send('Invalid argument used with card number 1008')
    if member.bot:
        return await ctx.send('🤖')
    if (await check_circumstances(ctx, member)) is not True:
        return
    other = User(member.id)
    user = User(ctx.author.id)
    if len(other.fs_cards) == 0:
        return await ctx.send('This user has no card in their free slots')
    c = random.choice([x for x in other.fs_cards if not x[0] in INDESTRUCTABLE])
    user.remove_card(1028)
    if await check_defense(self, ctx, member, 1028, c[0]) is True:
        return
    rc = other.remove_card(c[0], remove_fake=c[1]["fake"], restricted_slot=False, clone=c[1]["clone"])
    return await ctx.send(f'Done, you destroyed card No. {rc[0]}!')

async def card_1026(self, ctx, args:str=None):
    user = User(ctx.author.id)
    if user.has_effect('1026') and not args == '-force':
        return await ctx.send('You already have card 1026 in place! If you wish to throw away the remaining protections and renew the effect, use `use 1026 -force`')
    if user.has_effect('1026'):
        user.remove_effect('1026')
    user.add_effect('1026', 10)
    await ctx.send('Done, you will be automatically protected from the next 10 attacks! You need to keep the card in your inventory until all 10 defenses are used up')

async def card_1024(self, ctx, member:discord.Member):
    if not isinstance(member, discord.Member):
        return await ctx.send('Invalid argument used with card number 1024')
    if member.bot:
        return await ctx.send('🤖')

    other = User(member.id)
    user = User(ctx.author.id)
    tbr = [x for x in other.all_cards if x[1]["fake"] or x[1]["clone"]]
    if len(tbr) == 0:
        return await ctx.send('This user does not have any cards you could target with this spell!')
    user.remove_card(1024)

    rs_tbr = [x for x in other.rs_cards if x[1]["fake"] is True or x[1]["clone"] is True]
    fs_tbr = [x for x in other.fs_cards if x[1]["fake"] is True or x[1]["clone"] is True]

    for c in rs_tbr:
        other.rs_cards.remove(c)
    for c in fs_tbr:
        other.fs_cards.remove(c)
    # Why in the world do I use native pymongo instead of my class? 'Cause it's kinda useless to make a function I will just use here
    teams.update_one({'id': other.id}, {'$set': {'cards': {'rs': other.rs_cards, 'fs': other.fs_cards, 'effects': other.effects}}})
    return await ctx.send(f'Successfully removed all cloned and fake cards from `{member}`. Cards removed in total: {len(tbr)}')

async def card_1021(self, ctx, member:discord.Member, card_id:int):
    if not isinstance(member, discord.Member):
        return await ctx.send('Invalid argument used with card number 1021')
    if member.bot:
        return await ctx.send('🤖')
    if (await check_circumstances(ctx, member)) is not True:
        return

    user = User(ctx.author.id)
    other = User(member.id)
    if not other.has_any_card(card_id):
        return await ctx.send('The user is not in possesion of that card!')
    user.remove_card(1021)
    if await check_defense(self, ctx, member, 1021, card_id) is True:
        return
    c = other.remove_card(card_id)
    user.add_card(c[0], c[1]["fake"])
    return await ctx.send(f'Stole card number {card_id} successfully!')

async def card_1020(self, ctx, card_id:int):
    user = User(ctx.author.id)
    if not isinstance(card_id, int):
        return await ctx.send('You need to provide a valid number!')
    try:
        Card(card_id)
    except CardNotFound:
        return await ctx.send('Invalid card')
    if card_id > 99:
        return await ctx.send('You can only use "Fake" on a card with id between 1 and 99!')

    user.remove_card(1020)
    user.add_card(card_id, True)
    await ctx.send(f'Created a fake of card No. {card_id}! Make sure to remember that it\'s a fake, fakes don\'t count towards completion of the album')

async def card_1018(self, ctx):
    user = User(ctx.author.id)
    user.remove_card(1018)

    users = list()
    stolen_cards = list()
    async for message in ctx.channel.history(limit=20):
        if message.author not in users and message.author.bot is False and message.author != ctx.author:
            users.append(message.author)

    for usr in users:
        if (await check_circumstances(ctx, usr)) is not True:
            continue
        u = User(usr.id)
        if len(u.all_cards) == 0:
            continue
        c = random.choice(u.all_cards)
        if await check_defense(self, ctx, usr, 1018, c[0]) is True:
            continue
        r = u.remove_card(c[0], c[1]["fake"])
        stolen_cards.append(r)

    if len(stolen_cards) > 0:
        user.add_multi(stolen_cards)
        return await ctx.send(f'Success! Stole the card{"s" if len(stolen_cards) > 1 else ""} {", ".join([str(x[0]) for x in stolen_cards])} from {len(stolen_cards)} user{"s" if len(users) > 1 else ""}!')
    else:
        return await ctx.send('All targetted users were able to defend themselves!')

async def card_1015(self, ctx, member:discord.Member):
    if not isinstance(member, discord.Member):
        return await ctx.send('Invalid argument used with card number 1015')
    if member.bot:
        return await ctx.send('🤖')

    user = User(ctx.author.id)
    if not user.has_met(member.id):
        return await ctx.send(f'You haven\'t met this user yet! Use `{self.client.command_prefix(self.client, ctx.message)[2]}meet <@someone>` if they send a message in a channel to be able to use this card on them')

    user.remove_card(1015)

    if len(User(member.id).all_cards) == 0:
        return await ctx.send('This user does not have any cards! ("Clairvoyance" will get used up anyways)')

    return await paginator(self, ctx, 1, first_time=True, user=member) 

async def card_1011(self, ctx, member:discord.Member):
    if not isinstance(member, discord.Member):
        return await ctx.send('Invalid argument used with card number 1011')
    if member.bot:
        return await ctx.send('🤖')

    user = User(ctx.author.id)
    other = User(member.id)
    user.remove_card(1011)

    if len(other.rs_cards) == 0:
        return await ctx.send('The target does not have any restricted slot cards! Clone will get used up anyways')
    card = random.choice(other.rs_cards)
    if len(Card(card[0]).owners) >= len(Card(card[0]).owners) * ALLOWED_AMOUNT_MULTIPLE:
        return await ctx.send(f'The maximum amount of existing cards with id {card[0]} is reached! Clone gets used up anyways')

    if len(user.fs_cards) >= FREE_SLOTS: # This will NEVER be true but there is a very small chance with perfect timing
        return await ctx.send('You don\'t have space in your free slots so you can\'t use this command')
    user.add_card(card[0], card[1]["fake"], True)
    return await ctx.send(f'Successfully added another copy of card No. {card[0]} to your book! This card is {"not" if card[1]["fake"] is False else ""} a fake!')

async def card_1010(self, ctx, card_id:int):
    user = User(ctx.author.id)
    if not isinstance(card_id, int):
        return await ctx.send('You need to provide a valid card id you want another copy of!')
    if not user.has_any_card(card_id, False):
        return await ctx.send('Seems like you don\'t own this card You already need to own a (non-fake) copy of the card you want to duplicate')
    if len(Card(card_id).owners) >= Card(card_id).limit * ALLOWED_AMOUNT_MULTIPLE:
        return await ctx.send(f'The maximum amount of existing cards with id {card_id} is reached!')

    user.remove_card(1010)
    if len(user.fs_cards) >= FREE_SLOTS: # This will NEVER be true but there is a very small chance with perfect timing
        return await ctx.send('You don\'t have space in your free slots so you can\'t use this command')
    user.add_card(card_id, clone=True)
    return await ctx.send(f'Successfully added another copy of {card_id} to your book!')  

async def card_1008(self, ctx, member:discord.Member):
    user = User(ctx.author.id)

    if not isinstance(member, discord.Member):
        return await ctx.send('Invalid argument used with card number 1008')
    if member.bot:
        return await ctx.send('🤖')
    if (await check_circumstances(ctx, member)) is not True:
        return
    other = User(member.id)

    if len(other.all_cards) == 0:
        return await ctx.send('The user specified does not have any cards I\'m afraid! (maybe give them one)')

    attackist_cards = [x[0] for x in user.all_cards] # 4 Lines for an unlikely case :c
    
    attackist_cards.remove(1008)
    if len(attackist_cards) == 0:
        return await ctx.send('You don\'t have any cards left that could be swapped!')

    rm_c = random.choice([x[0] for x in other.all_cards if x[0] != 1008])
    if (await check_defense(self, ctx, member, 1008, rm_c)) is True:
        return
    
    user.remove_card(1008)
    removed_card_other = other.remove_card(rm_c)
    removed_attackist_card = user.remove_card(random.choice(attackist_cards))
    other.add_card(removed_attackist_card[0], removed_attackist_card[1]["fake"])
    user.add_card(removed_card_other[0], removed_card_other[1]["fake"])

    await ctx.send(f'Sucesfully swapped cards! Gave {member} the card `{removed_attackist_card[0]}` and took card number `{removed_card_other[0]}` from them!')

async def card_1007(self, ctx, member:discord.Member):
    if not isinstance(member, discord.Member):
        return await ctx.send('Invalid argument used with card number 1007')
    if member.bot:
        return await ctx.send('🤖')
    if (await check_circumstances(ctx, member)) is not True:
        return

    other = User(member.id)
    attackist = User(ctx.author.id)

    if len(other.rs_cards) == 0:
        return await ctx.send('This person does not have any cards in their restricted slots!')

    card:int = random.choice([x[0] for x in other.rs_cards])
    attackist.remove_card(1007)
    if (await check_defense(self, ctx, member, 1007, card)) is True:
        return

    removed_card = other.remove_card(card, restricted_slot=True)
    attackist.add_card(card, removed_card[1]["fake"])
    await ctx.send(f'Sucessfully stole card number `{card}` from `{member}`!')

async def card_1002(self, ctx, member:discord.Member):
    if not isinstance(member, discord.Member):
        return await ctx.send('Invalid argument used with card number 1002')
    if member.bot:
        return await ctx.send('🤖')
    if (await check_circumstances(ctx, member)) is not True:
        return

    user = User(ctx.author.id)
    if not user.has_met(member.id):
        return await ctx.send(f'You haven\'t met this user yet! Use `{self.client.command_prefix(self.client, ctx.message)[2]}meet <@someone>` if they send a message in a channel to be able to use this card on them')

    user.remove_card(1002)

    if (await check_view_defense(self, ctx, member, 1002)) is True:
        return

    return await paginator(self, ctx, 1, first_time=True, only_display='rs', user=member)    

async def card_1001(self, ctx, member:discord.Member):
    if not isinstance(member, discord.Member):
        return await ctx.send('Invalid argument used with card number 1001')
    if member.bot:
        return await ctx.send('🤖')

    if not User(ctx.author.id).has_met(member.id):
        return await ctx.send(f'You haven\'t met this user yet! Use `{self.client.command_prefix(self.client, ctx.message)[2]}meet <@someone>` if they send a message in a channel to be able to use this card on them')

    if (await check_circumstances(ctx, member)) is not True:
        return

    User(ctx.author.id).remove_card(1001)

    if (await check_view_defense(self, ctx, member, 1001)) is True:
        return

    if len(User(member.id).fs_cards) == 0:
        return await ctx.send('This user does not have any cards in their free slots! (this info used up card 1001)')

    return await paginator(self, ctx, 7, first_time=True, only_display='fs', user=member)  

async def book_paginator(self, ctx, page, msg:discord.Message=None, first_time=False):
    
    embed = discord.Embed.from_dict({
        'title': 'Introduction booklet',
        'description': BOOK_PAGES[page-1],
        'color': 0x1400ff,
        'footer': {'text': f'Page {page}/{len(BOOK_PAGES)}'}
    })

    if first_time is False:
        await msg.edit(embed=embed)
    else:
        msg = await ctx.send(embed=embed)
        #arrow backwards
        await msg.add_reaction('\U000025c0')
        #arrow forwards
        await msg.add_reaction('\U000025b6')

    def check(reaction, user):
        #Checking if everything is right, the bot's reaction does not count
        return user == ctx.author and reaction.message.id == msg.id and user != ctx.me and(reaction.emoji == '\U000025b6' or reaction.emoji == '\U000025c0')
    try:
        reaction, user = await self.client.wait_for('reaction_add', timeout=120, check=check)
    except asyncio.TimeoutError:
        try:
            await msg.remove_reaction('\U000025c0', ctx.me)
            await msg.remove_reaction('\U000025b6', ctx.me)
            return
        except:
            pass
    else:
        if reaction.emoji == '\U000025b6':
            await msg.remove_reaction('\U000025b6', ctx.author)
            #forward emoji
            if page == len(BOOK_PAGES):
                return await book_paginator(self, ctx, 1, msg)
            else:
                return await book_paginator(self, ctx, page+1, msg)

        if reaction.emoji == '\U000025c0':
            await msg.remove_reaction('\U000025c0', ctx.author)
            #backwards emoji
            if page == 1:
                return await book_paginator(self, ctx, len(BOOK_PAGES), msg)
            else:
                return await book_paginator(self, ctx, page-1, msg)

async def check_defense(self, ctx, attacked_user:discord.Member, attack_spell:int, target_card:int): #This function will alow the user to defend themselfes if they have protection spells
    user = User(attacked_user.id)
    if target_card in [x[0] for x in user.rs_cards]: # A list of cards that steal from restricted slots
        if f'page_protection_{int((target_card-10)/18+2)}' in user.effects and not target_card in [x[0] for x in user.fs_cards]:
            await ctx.send('The user has protected the page this card is in against spells!')
            return True

    if user.has_effect('1026')[0]:
        if 1026 in [x[0] for x in user.all_cards]: # Card has to remain in posession
            if user.effects['1026']-1 == 0:
                user.remove_effect('1026')
                user.remove_card(1026) 
            else:
                user.add_effect('1026', user.effects['1026']-1)
            await ctx.send('The user had remaining protection from card 1026 thus your attack failed')
            return True

    effects = list()
    for c in user.fs_cards:
        if c[0] in DEF_SPELLS and not c[0] in effects:
            if c[0] == 1019 and not Card(attack_spell).range == 'SR':
                continue
            if c[0] == 1004 and ctx.author.id not in user.met_user:
                continue
            effects.append(c[0])

    if len(effects) == 0:
        return
    
    await ctx.send(f'{attacked_user.mention} {ctx.author} has used the spell `{attack_spell}` on you! You have {len(effects)} spells to defend yourself: `{", ".join([str(x) for x in effects])}`! To use a spell, type its id, else type `n`')
    def check(msg):
        return msg.author.id == attacked_user.id and (msg.content.lower() in [*['n'], *[str(x) for x in effects]])
    try:
        msg = await self.client.wait_for('message', timeout=60, check=check)
    except asyncio.TimeoutError:
        await ctx.send('No response from the one attacked, the attack goes through!', delete_after=3)
        return
    else:
        if msg.content.lower() == 'n':
            await ctx.send('You decided not to use a defense spell, the attack goes through!', delete_after=3)
            return
        else:
            user.remove_card(int(msg.content), False)
            await ctx.send(f'Successfully defended against card `{attack_spell}`!')
            return True

async def check_circumstances(ctx, attacked_user:discord.Member):
    # This makes sure members always have the chance to defend themselves against attacks
    perms = ctx.channel.permissions_for(attacked_user)
    if not perms.send_messages or not perms.read_messages:
        return await ctx.send(f'You can only attack a user in a channel they have read and write permissions to which isn\'t the case with {attacked_user.name}') 
    return True

async def check_view_defense(self, ctx, attacked_user:discord.Member, attack_spell:int):
    user = User(attacked_user.id)

    effects = list() # This is currently unnecessary because there is only one card like this, but who knows whats to come
    for c in user.fs_cards:
        if c[0] in VIEW_DEF_SPELLS and not c[0] in effects:
            effects.append(c[0])
    
    if len(effects) == 0:
        return 

    await ctx.send(f'{attacked_user.mention} {ctx.author} has used the spell `{attack_spell}` on you! You have {len(effects)} spells to defend yourself: `{", ".join(effects)}`! To use a spell, type its id, else type `n`')
    def check(msg):
        return msg.author.id == attacked_user.id and (msg.content.lower() in [*['n'], *[str(x) for x in effects]])
    try:
        msg = await self.client.wait_for('message', timeout=120, check=check)
    except asyncio.TimeoutError:
        return await ctx.send('No response from the one attacked, the attack goes through!')
    else:
        if msg.content.lower() == 'n':
            return await ctx.send('You decided not to use a defense spell, the attack goes through!')
        else:
            user.remove_card(int(msg.content), False)
            await ctx.send(f'Successfully defended against card `{attack_spell}`!')
            return True    
    
def construct_rewards(reward_score:int):
    # reward_score will be minutes/10000 which equals a week. Max rewards will get returned once a user has hunted for a week
    if reward_score > 1:
        reward_score = 1

    MONSTERS = [572, 585, 598, 673, 697, 711, 1217]
    rewards = list()
    def rw(reward_score:int):
        if reward_score == 1:
            if randint(1,10) < 5:
                return (random.choice([x['_id'] for x in items.find({'type': 'normal', 'rank': random.choice(['A', 'B', 'C'])})]), 1), 0.3
            else:
                return (random.choice([x['_id'] for x in items.find({'type': 'spell', 'rank': random.choice(['B', 'C'])})]), 1), 0.3
        if reward_score < 3000/10000:
            rarities = ['E', 'G', 'H']
        elif reward_score < 7000/10000:
            rarities = ['D', 'E', 'F']
        else:
            rarities = ['C', 'D', 'E']
        amount = int(random.randint(int(100*reward_score), int(130*reward_score))/25)
        return (random.choice([x['_id'] for x in items.find({'type': 'monster', 'rank': random.choice(rarities)})]), amount if amount != 0 else 1), reward_score

    card_amount = int(random.randint(4, 10)*reward_score)
    for i in range(card_amount if card_amount >= 1 else 1):
        r, s = rw(reward_score) # I get a type error if I don't pass the score idk why
        rewards.append(r)
        reward_score = s
  
    other_rewards = rewards
    for reward in other_rewards: 
        # This avoid duplicates e.g. 4xPaladins Neclace, 2xPaladins Necklace => 6xPaladins Necklace
        if [x[0] for x in other_rewards].count(reward[0]) > 1:
            total = 0
            for x in other_rewards:
                if x[0] == reward[0]:
                    total = total+x[1]
                    rewards.remove(x)
            rewards.append([reward[0], total])

    return rewards

def format_offers(offers:list, reduced_item:int=None, reduced_by:int=None):
    formatted:list = []
    if reduced_item and reduced_by:
        x:int = 0
        for offer in offers:
            formatted.append(format_item(offer, reduced_item, reduced_by, x))
            x = x+1
    else:
        for offer in offers:
            formatted.append(format_item(offer))

    return formatted

def format_item(offer:int, reduced_item:int=None, reduced_by:int=None, number:int=None):
    item = items.find_one({'_id': int(offer)})
    if reduced_item and reduced_by and number: #Uneccesssary to check for all but why not
        if number == reduced_item:
            return {'name':f'**Number {item["_id"]}: {item["name"]}** |{item["emoji"]}|', 'value': f'**Description:** {item["description"]}\n**Price:** {PRICES[item["rank"]]-int(PRICES[item["rank"]]*(reduced_by/100))} (Reduced by **{reduced_by}%**) Jenny\n**Type:** {item["type"].replace("normal", "item")}\n**Rarity:** {item["rank"]}'}  
    
    return {'name':f'**Number {item["_id"]}: {item["name"]}** |{item["emoji"]}|', 'value': f'**Description:** {item["description"]}\n**Price:** {PRICES[item["rank"]]} Jenny\n**Type:** {item["type"].replace("normal", "item")}\n**Rarity:** {item["rank"]}'}

async def paginator(self, ctx, page:int, msg:discord.Message=None, first_time=False, only_display=None, user=None):
    if user is None:
        name = ctx.author
        person = User(ctx.author.id)
    else:
        name = user
        person = User(user.id)
    
    restricted_slots = bool()
    rs_cards = list()
    fs_cards = list()
    max_pages = 6+math.ceil(len(person.fs_cards)/18)
    
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
                rs_cards.append([i, Card(i).image_url])
            if page == 1 and len(rs_cards) == 10:
                break
            i = i+1
    else:
        i = (page-7)*18 
        while (len(fs_cards) % 18 == 0) == False or (len(fs_cards) == 0) == True: 
            try:
                fs_cards.append([person.fs_cards[i][0], Card(person.fs_cards[i][0]).image_url])
            except: # don't know what the out of range error is called so I can't check for it
                fs_cards.append(None)
            i = i+1

    if page <= 6:
        cards = rs_cards
        restricted_slots = True
    elif page > 6:
        cards = fs_cards
        restricted_slots = False

    image = await imagefunction(cards, restricted_slots, page)

    buffer = io.BytesIO()
    image.save(buffer, "png") 
    buffer.seek(0)

    f = discord.File(buffer, filename="image.png")
    embed = discord.Embed.from_dict({
        'title': f'{name}\'s book',
        'color': 0x2f3136, # making the boarder "invisible" (assuming there are no light mode users)
        'image': {'url': 'attachment://image.png' }
    })

    if first_time is False:
        await msg.delete()
    
    msg = await ctx.send(file=f, embed=embed)
    #arrow backwards
    await msg.add_reaction('\U000025c0')
    #arrow forwards
    await msg.add_reaction('\U000025b6')

    def check(reaction, u):
        #Checking if everything is right, the bot's reaction does not count
        return u == ctx.author and reaction.message.id == msg.id and u != ctx.me and(reaction.emoji == '\U000025b6' or reaction.emoji == '\U000025c0')
    try:
        reaction, u = await self.client.wait_for('reaction_add', timeout=120, check=check)
    except asyncio.TimeoutError:
        try:
            await msg.remove_reaction('\U000025c0', ctx.me)
            await msg.remove_reaction('\U000025b6', ctx.me)
            return
        except:
            pass
    else:
        if reaction.emoji == '\U000025b6':
            #forward emoji
            if page == max_pages:
                if only_display == 'fs':
                    return await paginator(self, ctx, 7, msg, only_display='fs', user=user)
                return await paginator(self, ctx, 1, msg, only_display=only_display, user=user)
            else:
                if page == 6 and only_display == 'rs':
                    return await paginator(self, ctx, 1, msg, only_display='rs', user=user)
                
                return await paginator(self, ctx, page+1, msg, only_display=only_display, user=user)

        if reaction.emoji == '\U000025c0':
            #backwards emoji
            if page == 1:
                if only_display == 'rs':
                    return await paginator(self, ctx, 6, msg, only_display='rs', user=user)
                return await paginator(self, ctx, max_pages, msg, only_display=only_display, user=user)
            else:
                if only_display == 'fs' and page == 7:
                    return await paginator(self, ctx, max_pages, msg, only_display='fs', user=user)
                return await paginator(self, ctx, page-1, msg, only_display=only_display, user=user)

# Contribution by DerUSBStick (Thank you!)
async def imagefunction(data, restricted_slots, page:int):
    background = await getbackground(0 if len(data) == 10 else 1)
    if len(data) == 18 and restricted_slots:
        background = await numbers(background, data, page)
    background = await cards(background, data, 0 if len(data) == 10 else 1)
    background = await setpage(background, page)
    return background

async def getbackground(types):
    url = ['https://alekeagle.me/XdYUt-P8Xv.png', 'https://alekeagle.me/wp2mKvzvCD.png']
    async with aiohttp.ClientSession() as cs:
        async with cs.get(url[types]) as res:
            image_bytes = await res.read()
            background = Image.open(io.BytesIO(image_bytes)).convert('RGB') 
    return background

async def getcard(url):
    async with aiohttp.ClientSession() as cs:
        async with cs.get(url) as res:
            image_bytes = await res.read()
            image_card = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            image_card = image_card.resize((80, 110), Image.ANTIALIAS)
    await asyncio.sleep(0.3) # This is to hopefully prevent aiohttp's "Response payload is not completed" bug
    return image_card

async def setpage(image, page):
    font = await getfont(20)
    draw = ImageDraw.Draw(image)
    draw.text((5, 385), f'{page*2-1}', (0,0,0), font=font)
    draw.text((595, 385), f'{page*2}', (0,0,0), font=font)
    return image

async def getfont(size):
    font = ImageFont.truetype('/home/ec2-user/killua/killua/font.ttf', size, encoding="unic") 
    return font

async def cards(image, data, option):

    card_pos:list = [
        [(113, 145),(320, 15),(418, 15),(516, 15),(320, 142),(418, 142),(516, 142),(320, 269),(418, 269),(516, 269)],
        [(15,17),(112,17),(210,17),(15,144),(112,144),(210,144),(15,274),(112,274),(210,274),(320,13),(418,13),(516,13),(320,143),(418,143),(516,143),(320,273),(418,273),(516,273)]
    ]
    for n, i in enumerate(data): 
        if i:
            if i[1]:
                if not str(i[0]) in cached_cards: # Kile part (I wrote a small optimasation algorithm which avoids fetching the same card and just uses the same data)
                    cached_cards[str(i[0])] = await getcard(i[1])

                image.paste(cached_cards[str(i[0])], (card_pos[option][n]))
    return image

async def numbers(image, data, page):
    page -= 2
    numbers_pos:list = [
      [(35, 60),(138, 60),(230, 60),(35, 188),(138, 188),(230, 188),(36, 317),(134, 317),(232, 317),(338, 60),(436, 60),(536, 60),(338, 188),(436, 188),(536, 188),(338, 317),(436, 317),(536, 317)], 
      [(30, 60),(132, 60),(224, 60),(34, 188),(131, 188),(227, 188),(32, 317),(130, 317),(228, 317),(338, 60),(436, 60),(533, 60),(338, 188),(436, 188),(533, 188),(338, 317),(436, 317),(533, 317)], 
      [(30, 60),(130, 60),(224, 60),(31, 188),(131, 188),(230, 188),(32, 317),(130, 317),(228, 317),(338, 60),(436, 60),(533, 60),(338, 188),(436, 188),(533, 188),(340, 317),(436, 317),(533, 317)], 
      [(30, 60),(130, 60),(224, 60),(31, 188),(131, 188),(230, 188),(32, 317),(133, 317),(228, 317),(338, 60),(436, 60),(533, 60),(338, 188),(436, 188),(533, 188),(338, 317),(436, 317),(535, 317)], 
      [(30, 60),(130, 60),(224, 60),(31, 188),(131, 188),(230, 188),(32, 317),(133, 317),(228, 317),(342, 60),(436, 60),(533, 60),(338, 188),(436, 188),(533, 188),(338, 317),(436, 317),(535, 317)], 
      [(30, 60),(130, 60),(224, 60),(31, 188),(131, 188),(230, 188),(32, 317),(133, 317),(228, 317),(342, 60),(436, 60),(533, 60),(338, 188),(436, 188),(533, 188),(338, 317),(436, 317),(535, 317)] 
      ]

    font = await getfont(35)
    draw = ImageDraw.Draw(image)
    for n, i in enumerate(data):
        if i[1] == None:
            draw.text(numbers_pos[page][n], f'0{i[0]}', (165,165,165), font=font)
    return image

Cog = Cards

def setup(client):
    client.add_cog(Cards(client))
