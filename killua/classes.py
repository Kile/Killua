from datetime import datetime
from pymongo import MongoClient
import json
from .constants import FREE_SLOTS

with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())

cluster = MongoClient(config['mongodb'])
db = cluster['Killua']
teams = db['teams']
items = db['items']
guilds = db['guilds']

class CardNotFound(Exception):
    pass

class NotInPossesion(Exception):
    pass

class OnlyFakesFound(Exception):
    pass

class CardLimitReached(Exception):
    pass

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
        self.is_premium:bool = 'premium' in self.badges

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
            return teams.update_one({'id': user_id}, {'$set': {'cards': {'rs': [], 'fs': [], 'effects': {}}, 'met_user': []}})  
        else:
            return teams.insert_one({'id': user_id, 'points': 0, 'badges': [], 'cooldowndaily': '','cards': {'rs': [], 'fs': [], 'effects': {}}, 'met_user': []}) 

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