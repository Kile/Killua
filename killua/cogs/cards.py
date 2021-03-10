import discord
from discord.ext import commands, tasks
import random
from random import randint
import datetime
import pymongo
from pymongo import MongoClient
import json
import asyncio
from itertools import zip_longest
import math
import typing

with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())

cluster = MongoClient(config['mongodb'])
db = cluster['Killua']
teams = db['teams']
items = db['items']
guilds = db['servers']
general = cluster['general']
shop = general['shop']

ALOWED_AMOUNT_MULTIPLE = 3
FREE_SLOTS = 40

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

def return_none(*args, **kwargs):
    return None

class NotInPossesion(Exception):
    def __init__(self):
        super().__init__()

class OnlyFakesFound(Exception):
    def __init__(self):
        super().__init__()

class Card():
    """This class makes it easier to access card information"""
    def __init__(self, card_id:int):
        card = items.find_one({'_id': card_id})
        if card is None:
            return return_none #Returns none if no card with this id is valid

        self.id:int = card['_id']
        self.name:str = card['name']
        self.image_url:str = card['Image']
        self.owners:list = card['owners']
        self.description:str = card['description']
        self.emoji:str = card['emoji']
        self.rank:str = card['rank']
        self.limit:int = card['limit']

        if card_id < 1000: # If the card is a spell card it has two additional properties
            self.range:str = card['range']
            self.cls:list = card['class']

        def add_owner(self, user_id:int):
            self.owners.append(user_id)
            items.update_one({'_id': self.id}, {'$set': {'owners': self.owners}})
            return

        def remove_owner(self, user_id:int):
            self.owners.remove(user_id)
            items.update_one({'_id': self.id}, {'$set': {'owners': self.owners}})
            return

        def __eq__(self, other):
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

        if user is None:
            return return_none

        if not 'cards' in user:
            self.rs_cards = None
            self.fs_cards = None
            self.effects = None
        else:
            self.effects:dict = user['cards']['effects']
            self.rs_cards:list = user['cards']['rs']
            self.fs_cards:list = user['cards']['fs']

        self.id:int = user_id
        self.jenny:int = user['points']
        
    def has_rs_card(self, card_id:int):
        if card_id in [x[0] for x in self.rs_cards]:
            return True
        else:
            return False

    def has_fs_card(self, card_id:int):
        if card_id in [x[0] for x in self.fs_cards]:
            return True
        else:
            return False

    def has_any_card(self, card_id:int):
        if card_id in [x[0] for x in self.fs_cards] or card_id in [x[0] for x in self.rs_cards]:
            return True
        else:
            return False

    def remove_jenny(self, amount:int):
        if self.jenny < amount:
            raise Exception('Trying to remove more Jenny than the user has')
        teams.update_one({'id': self.id}, {'$set': {'points': self.jenny - amount}})
        return

    def add_jenny(self, amount:int):
        teams.update_one({'id': self.id}, {'$set': {'points': self.jenny + amount}})
        return

    def remove_card(self, card_id:int, remove_fake:bool=None, payed:bool=False):
        card = Card(card_id)
        if User(self.id).has_any_card(card_id) is False:
            raise NotInPossesion('This card is not in possesion of the specified user!')

        def fake_check(card_list:list):
            indx = [x for x in card_list if x[0] == card_id]
            (indx.remove([card_id, {"fake": True}]) for i in indx if card_list[i]['fake'] == True)
            if len(indx) == 0:
                return False
            else:
                return True

        def rc(fake:bool, restricted_slot:bool):

            if restricted_slot is False:
                self.fs_cards.remove([card_id, {'fake': fake}])
            elif restricted_slot is True:
                self.rs_cards.remove([card_id, {'fake': fake}])
            card.remove_owner(self.id)
            teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': self.rs_cards, 'fs': self.fs_cards, 'effects': self.effects}}})

        def fake():
            if remove_fake is None:
                c = []
                for x in self.rs_cards if x[0] == card_id:
                    c.append(x)
                random_fake = random.choice([x[1]['fake'] for x in c])
                return random_fake
            elif remove_fake is False:
                return False
            elif remove_fake is True:
                return True

        if User(self.id).has_fs_card(card_id) is False:
            if fake_check(self.rs_cards) is False and remove_fake is False:
                raise OnlyFakesFound('The user has no card with this id that is not a fake')
            else:
                rc(fake(), True)
        else:
            if fake_check(self.fs_cards) is False and remove_fake is False:
                if fake_check(self.rs_cards) is False and remove_fake is False:
                    raise OnlyFakesFound('The user has no card with this id that is not a fake')
                
                rc(fake(), True)
            else:
                rc(fake(), False)

        if payed is not False:
            User(self.id).remove_jenny(PRICES[card.rank])

        return 

    def add_card(self, card_id:int, fake:bool):
        card = Card(card_id)

        def ac(restricted_slot:bool=False):
            if restricted_slot is False:
                self.fs_cards.append([card_id, {'fake': fake}])
            elif restricted_slot is True:
                self.rs_cards.append([card_id, {'fake': fake}])
            card.add_owner(self.id)
            teams.update_one({'id': self.id}, {'$set': {'cards': {'rs': self.rs_cards, 'fs': self.fs_cards, 'effects': self.effects}}})

        if User(self.id).has_rs_card(card.id) is False:
            if card_id > 99:
                ac(True)
                return
        ac()

    def count_card(self, card_id:int, including_fakes:bool=True):
        card = Card(card_id)
        card_amount = 0
        if including_fakes is True:
            rs_cards = [x[0] for x in self.rs_cards]
            fs_cards = [x[0] for x in self.fs_cards]
        else:
            rs_cards = [x[0] for x in self.rs_cards if x[1]['fake'] == False]
            fs_cards = [x[0] for x in self.fs_cards if x[1]['fake'] == False]

        for x in [*rs_cards, *fs_cards] if x == card.id:
            card_amount = card_amount+1

        return card_amount

    def add_effect(self, effect:int): # Effect are resembled by the card id which caused them
        pass #TODO add effects here depending on what card
    
    def has_effect(self, effect:int):
        if effect in self.effects:
            return True
        else:
            return False

###############TODO TODO TODO################
'''
             TO-DOs

1) k!book showing the cards you have in book format like in the anime |Restricted slots mostly done (not tested)|

2) k!hunt Hunting for monsters = cards

3) k!shop you can buy cards, daily offers, some stuff |Mostly Done|

4) k!sell sell a card

5) k!give modify to work with items

6) Add support for all spell cards usable with k!use
'''
###############TODO TODO TODO################

example = {
    "effects":{
      "effect": "time/amount"
    },
    "rs": [ #Stands for restricted slots
      [1,{"fake": True}],
      [4, {"fake": False}],
      [6, {"fake": False}],
      [7, {"fake": False}]
    ],
    "fs": [ #Stands for free slots
      [1004, {"fake": True}],
      [1008, {"fake": False}]
    ]
}

# WARNING this is not ready for use, I am purely giving you a look on an (untested) part of my code