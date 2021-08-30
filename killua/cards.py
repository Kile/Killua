import math
import random
import discord
from discord.ext import commands
from datetime import datetime
from typing import List

from .constants import items, INDESTRUCTABLE, ALLOWED_AMOUNT_MULTIPLE, DEF_SPELLS, VIEW_DEF_SPELLS, FREE_SLOTS
from .classes import User, SuccessfullDefense, CheckFailure, CardNotFound, Book, Button, ConfirmButton
from .paginator import View, Paginator
from .help import Select

card_cache = {}
background_cache = {}

class Card:
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

    async def _wait_for_defense(self, ctx:commands.Context, other:User, effects:list) -> None:

        if len(effects) == 0:
            return

        effects = [Card(c) for c in effects]
        view = View(other.id, timeout=20)
        view.add_item(Select(options=[discord.SelectOption(label=c.name, emoji=c.emoji, value=str(c.id)) for c in effects]))
        view.add_item(Button(label="Ignore", style=discord.ButtonStyle.red))

        msg = await ctx.send(f"<@{other.id}> {ctx.author} has used the spell `{self.id}` on you! You have {len(effects)} spells to defend yourself. You can either choose one of them to defend yourself with or let the attack go through", view=view)
        await view.wait()
        await view.disable(msg)

        if not view.value:
            if view.timed_out:
                await ctx.send(f"No response from the attacked user, the attack goes through!", reference=msg)
            else:
                await ctx.send("You decided not to use a defense spell, the attack goes through!", reference=msg)
            return

        if isinstance(view.value, int): 
            other.remove_card(view.value)
            raise SuccessfullDefense(f"<@{other.id}> successfully defended against your attack")
        else:
            await ctx.send("You decided not to use a defense spell, the attack goes through!", reference=msg)

    async def _view_defense_check(self, ctx: commands.Context, other:User) -> None:
        effects = []
        for c in other.fs_cards:
            if c[0] in VIEW_DEF_SPELLS and not c[0] in effects:
                effects.append(c[0])

        await self._wait_for_defense(ctx, other, effects)

    async def _attack_defense_check(self, ctx: commands.Context, other: User, target_card:int) -> None:
        if target_card in [x[0] for x in other.rs_cards]: # A list of cards that steal from restricted slots
            if f'page_protection_{int((target_card-10)/18+2)}' in other.effects and not target_card in [x[0] for x in other.fs_cards]:
                raise SuccessfullDefense('The user has protected the page this card is in against spells!')

        if other.has_effect('1026')[0]:
            if 1026 in [x[0] for x in other.all_cards]: # Card has to remain in posession
                if other.effects['1026']-1 == 0:
                    other.remove_effect('1026')
                    other.remove_card(1026) 
                else:
                    other.add_effect('1026', other.effects['1026']-1)
                raise SuccessfullDefense('The user had remaining protection from card 1026 thus your attack failed')

        effects = []
        for c in other.fs_cards:
            if c[0] in DEF_SPELLS and not c[0] in effects:
                if c[0] == 1019 and not self.range == 'SR':
                    continue
                if c[0] == 1004 and self.ctx.author.id not in other.met_user:
                    continue
                effects.append(c[0])

        await self._wait_for_defense(ctx, other, effects)

    def _permission_check(self, ctx:commands.Context, member:discord.Member) -> None:
        perms = ctx.channel.permissions_for(member)
        if not perms.send_messages or not perms.read_messages:
            raise InvalidUsage(f'You can only attack a user in a channel they have read and write permissions to which isn\'t the case with {self.Member.display_name}') 

    def _has_cards_check(self, cards:List[list], card_type:str="", is_self:bool=False, uses_up:bool=False) -> None:
        if len(cards) == 0:
            raise CheckFailure((f"You do not have cards{card_type}!" if is_self else f"This user does not have any cards{card_type}!") + f" This information uses up card {self.name}." if uses_up else "")

    def _has_any_card(self, card_id:int, user:User) -> None:
        if not user.has_any_card(card_id):
            raise CheckFailure("The specified user doesn't have this card")

    def _has_met_check(self, prefix:str, author:User, other:discord.Member) -> None:
        if not author.has_met(other.id):
            raise CheckFailure(f"You haven\'t met this user yet! Use `{prefix}meet <@someone>` if they send a message in a channel to be able to use this card on them")

    def _has_other_card_check(self, cards:List[list]) -> None:
        if len(cards) < 2:
            raise CheckFailure(f"You don't have any cards other than card {self.name}!")

    def _is_maxed_check(self, card:int) -> None:
        c = Card(card)
        if len(c.owners) >= c.limit * ALLOWED_AMOUNT_MULTIPLE:
            raise CheckFailure(f'The maximum amount of existing cards with id {card_id} is reached!')

    def _is_full_check(self, user:User) -> None:
        if len(user.fs_cards) >= FREE_SLOTS:
            raise CheckFailure("You don't have any space in your free slots left!")

    def _is_valid_card_check(self, card_id:int) -> None:
        try:
            Card(card_id)
        except CardNotFound:
            raise CheckFailure("Specified card is invalid!")

    def _has_effect_check(self, user:User, effect:str) -> None:
        if user.has_effect(effect)[0]:
            raise CheckFailure("You already have this effect in place!")

    def _get_analysis_embed(self, card_id:int) -> discord.Embed:
        card = Card(card_id)
        fields = [
            {"name": "Name", "value": card.name  + " " + card.emoji, "inline": True},
            {"name": "Type", "value": card.type.replace("normal", "item"), "inline": True},
            {"name": "Rank", "value": card.rank, "inline": True},
            {"name": "Limit", "value": str(card.limit*ALLOWED_AMOUNT_MULTIPLE), "inline": True}
        ]
        if card.type == "spell":
            fields.append({"name": "Class", "value": ", ".join(card.cls), "inline": True})
            fields.append({"name": "Range", "value": card.range, "inline": True})

        embed = discord.Embed.from_dict({
            'title': f'Info about card {card_id}',
            'thumbnail': {'url': card.image_url},
            'color': 0x1400ff,
            "description": card.description,
            'fields': fields
        })
        return embed

    def _get_list_embed(self, card_id:int) -> discord.Embed:
        card = Card(card_id)

        real_owners = []
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
        return embed

class Card1001(Card):

    def __init__(self, ctx: commands.Context, **kwargs) -> None:
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, member:discord.Member) -> None:
        author = User(self.ctx.author.id)
        other = User(member.id)

        self._has_met_check(self.ctx.bot.command_prefix(self.ctx.bot, self.ctx.message)[2], author, member)

        self._permission_check(self.ctx, member)
        author.remove_card(self.id)
        await self._view_defense_check(self.ctx, other)

        self._has_cards_check(other.fs_cards, " in their free slots", uses_up=True)

        async def make_embed(page, embed, pages):
            return await Book(self.ctx.bot.session).create(member, page, True)

        await Paginator(self.ctx, max_pages=math.ceil(len(other.fs_cards)/18), func=make_embed, has_file=True).start() 

class Card1002(Card):

    def __init__(self, ctx: commands.Context, **kwargs) -> None:
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, member:discord.Member) -> None:
        author = User(self.ctx.author.id)
        other = User(member.id)

        self._has_met_check(self.ctx.bot.command_prefix(self.ctx.bot, self.ctx.message)[2], author, member)
        
        self._permission_check(self.ctx, member)    
        author.remove_card(self.id)
        await self._view_defense_check(self.ctx, other)

        async def make_embed(page, embed, pages):
            return await Book(self.ctx.bot.session).create(member, page)

        await Paginator(self.ctx, max_pages=6, func=make_embed, has_file=True).start() 

class Card1007(Card):

    def __init__(self, ctx: commands.Context, **kwargs) -> None:
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, member:discord.Member):
        self._permission_check(self.ctx, member)

        author = User(self.ctx.author.id)
        other = User(member.id)

        self._has_cards_check(other.rs_cards, " in their restricted slots")

        target_card = random.choice([x[0] for x in other.rs_cards])
        author.remove_card(self.id)
        await self._attack_defense_check(self.ctx, other, target_card)

        removed_card = other.remove_card(target_card, restricted_slot=True)
        author.add_card(target_card, removed_card[1]["fake"])
        await self.ctx.send(f'Successfully stole card number `{target_card}` from `{member}`!')

class Card1008(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, member:discord.Member) -> None:
        self._permission_check(self.ctx, member)

        author = User(self.ctx.author.id)
        other = User(member.id)

        self._has_cards_check(other.all_cards)
        self._has_other_card_check(author.all_cards)

        target_card = random.choice([x[0] for x in other.all_cards if x[0] != 1008])
        await self._attack_defense_check(self.ctx, other, target_card)

        author.remove_card(self.id)
        removed_card_other = other.remove_card(target_card)
        removed_card_author = author.remove_card(random.choice([x[0] for x in author.all_cards]))
        other.add_card(removed_card_author[0], removed_card_author[1]["fake"])
        author.add_card(removed_card_other[0], removed_card_other[1]["fake"])

        await self.ctx.send(f'Successfully swapped cards! Gave {member} the card `{removed_card_author[0]}` and took card number `{removed_card_other[0]}` from them!')

class Card1010(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, card_id:int) -> None:
        user = User(self.ctx.author.id)

        if not user.has_any_card(card_id, False):
            raise CheckFailure('Seems like you don\'t own this card You already need to own a (non-fake) copy of the card you want to duplicate')

        self._is_maxed_check(card_id)
        user.remove_card(self.id)
        user.add_card(card_id, clone=True)

        await self.ctx.send(f'Successfully added another copy of {card_id} to your book!') 

class Card1011(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, member:discord.Member) -> None:
        author = User(self.ctx.author.id)
        other = User(member.id)
        author.remove_card(self.id)

        self._has_cards_check(other.rs_cards, f" in their restricted slots!", uses_up=True)
        card = random.choice([x for x in other.rs_cards if x[0] != 0])
        self._is_maxed_check(card[0])

        author.add_card(card[0], card[1]["fake"], True)
        await self.ctx.send(f'Successfully added another copy of card No. {card[0]} to your book! This card is {"not" if card[1]["fake"] is False else ""} a fake!')

class Card1015(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, member:discord.Member) -> None:
        author = User(self.ctx.author.id)
        other = User(member.id)

        self._has_met_check(self.ctx.bot.command_prefix(self.ctx.bot, self.ctx.message)[2], author, member)

        author.remove_card(self.id)

        self._has_cards_check(other.all_cards)

        async def make_embed(page, embed, pages):
            return await Book(self.ctx.bot.session).create(member, page)

        return await Paginator(self.ctx, max_pages=6+math.ceil(len(other.fs_cards)/18), func=make_embed, has_file=True).start()

class Card1018(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self) -> None:
        author = User(self.ctx.author.id)
        author.remove_card(self.id)

        users = []
        stolen_cards = []

        async for message in self.ctx.channel.history(limit=20):
            if message.author not in users and message.author.bot is False and message.author != self.ctx.author:
                users.append(message.author)

        for user in users:
            try:
                self._permission_check(self.ctx, user)
                u = User(user.id)
                self._has_cards_check(u.all_cards)
                target = random.choice(u.all_cards)
                await self._attack_defense_check(self.ctx, u, target)
                r = u.remove_card(target[0], target[1]["fake"])
                stolen_cards.append(r)
            except Exception as e:
                continue

        if len(stolen_cards) > 0:
            author.add_multi(stolen_cards)
            await self.ctx.send(f'Success! Stole the card{"s" if len(stolen_cards) > 1 else ""} {", ".join([str(x[0]) for x in stolen_cards])} from {len(stolen_cards)} user{"s" if len(users) > 1 else ""}!')
        else:
            await self.ctx.send('All targetted users were able to defend themselves!')

class Card1020(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, card_id:int) -> None:
        self._is_valid_card_check(card_id)

        if card_id > 99:
            raise CheckFailure(f"You can only use \"{self.name}\" on a card with id between 1 and 99!")

        author = User(self.ctx.author.id)

        author.remove_card(self.id)
        author.add_card(card_id, True)
        await self.ctx.send(f'Created a fake of card No. {card_id}! Make sure to remember that it\'s a fake, fakes don\'t count towards completion of the album')

class Card1021(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, member:discord.Member, card_id:int) -> None:
        self._permission_check(self.ctx, member)

        author = User(self.ctx.author.id)
        other = User(member.id)

        self._has_any_card(card_id, other)
        author.remove_card(self.id)
        await self._attack_defense_check(self.ctx, other, card_id)

        stolen = other.remove_card(card_id)
        author.add_card(stolen[0], stolen[1]["fake"])
        await self.ctx.send(f"Stole card number {card_id} successfully!")

class Card1024(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, member:discord.Member) -> None:
        other = User(member.id)
        author = User(self.ctx.author.id)

        tbr = [x for x in other.all_cards if x[1]["fake"] or x[1]["clone"]]

        if len(tbr) == 0:
            raise CheckFailure("This user does not have any cards you could target with this spell!")

        author.remove_card(self.id)

        rs_tbr = [x for x in other.rs_cards if x[1]["fake"] is True or x[1]["clone"] is True]
        fs_tbr = [x for x in other.fs_cards if x[1]["fake"] is True or x[1]["clone"] is True]

        for c in rs_tbr:
            other.rs_cards.remove(c)
        for c in fs_tbr:
            other.fs_cards.remove(c)

        other._update_val('cards', {'rs': other.rs_cards, 'fs': other.fs_cards, 'effects': other.effects}) 
        await self.ctx.send(f'Successfully removed all cloned and fake cards from `{member}`. Cards removed in total: {len(tbr)}')

class Card1026(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self) -> None:
        author = User(self.ctx.author.id)
        try:
            self._has_effect_check(author, str(self.id))
        except CheckFailure:
            if not author.count_card(self.id) > 1:
                raise CheckFailure("You don't have another copy of this card to renew the effect")
            view = ConfirmButton(user_id=self.ctx.author.id)
            msg = await self.ctx.send(f"You still have {author.has_effect(str(self.id))[1]} protections left. Do you really want to use this card now and overwrite the current protection?", view=view)
            await view.wait()
            await view.disable(msg)

            if view.timed_out:
                raise CheckFailure("Timed out!")
            elif view.value is False:
                raise CheckFailure("Successfully canceled!")

        if author.has_effect(str(self.id)):
            author.remove_effect(str(self.id))

        # if (amount:=author.count_card(self.id)) > 1:
        #     for i in range(amount):
        #         author.remove_card(self.id)

        author.add_effect(str(self.id), 10)

        await self.ctx.send('Done, you will be automatically protected from the next 10 attacks! You need to keep the card in your inventory until all 10 defenses are used up')

class Card1028(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, member:discord.Member) -> None:
        self._permission_check(self.ctx, member)

        other = User(member.id)
        author = User(self.ctx.author.id)

        self._has_cards_check(other.fs_cards, " in their free slots")

        target_card = random.choice([x for x in other.fs_cards if not x[0] in INDESTRUCTABLE])
        author.remove_card(self.id)
        await self._attack_defense_check(self.ctx, other, target_card)
        other.remove_card(target_card[0], remove_fake=target_card[1]["fake"], restricted_slot=False, clone=target_card[1]["clone"])
        await self.ctx.send(f'Success, you destroyed card No. {target_card[0]}!')

class Card1029(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, member:discord.Member) -> None:
        self._permission_check(self.ctx, member)

        other = User(member.id)
        author = User(self.ctx.author.id)

        self._has_cards_check(other.rs_cards, " in their restricted slots")

        target_card = random.choice([x for x in other.rs_cards if not x[0] in INDESTRUCTABLE])
        author.remove_card(self.id)
        await self._attack_defense_check(self.ctx, other, target_card)
        other.remove_card(target_card[0], remove_fake=target_card[1]["fake"], restricted_slot=True, clone=target_card[1]["clone"])
        await self.ctx.send(f'Success, you destroyed card No. {target_card[0]}!')

class Card1031(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, card_id:int) -> None:
        self._is_valid_card_check(card_id)

        author = User(self.ctx.author.id)
        author.remove_card(self.id)
        embed = self._get_analysis_embed(card_id)
        await self.ctx.send(embed=embed)

class Card1032(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self) -> None:
        author = User(self.ctx.author.id)
        self._is_full_check(author)

        target = random.choice([x['_id'] for x in items.find({'type': 'normal'}) if x['rank'] != 'SS']) # random card for lottery
        author.remove_card(self.id)
        self._is_maxed_check(target)
        author.add_card(target)

        await self.ctx.send(f'Successfully added card No. {target} to your inventory')

class Card1035(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, page:int) -> None:
        author = User(self.ctx.author.id)

        if page > 6 or page < 1:
            raise CheckFailure('You need to choose a page between 1 and 6')
        self._has_effect_check(author, f"page_protection_{page}")
        author.remove_card(self.id)
        author.add_effect(f'page_protection_{page}', datetime.now()) # The value doesn't matter here
        await self.ctx.send(f'Success! Page {page} is now permanently protected')

class Card1036(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, effect:str, card_id:int) -> None:
        author = User(self.ctx.author.id)

        if not str(self.id) in author.effects and not author.has_fs_card(self.id):
            raise CheckFailure(f'You need to have used the card {self.id} once to use this command')

        if author.has_fs_card(self.id) and not str(self.id) in author.effects:
            author.remove_card(self.id)
        author.add_effect(str(self.id), datetime.now())

        if not effect.lower() in ["list", "analysis", "1031", "1038"]:
            raise CheckFailure(f'Invalid effect to use! You can use either `analysis` or `list` with this card. Usage: `{self.client.command_prefix(self.client, ctx.message)[2]}use {self.id} <list/analysis> <card_id>`')

        if effect.lower() in ["list", "1038"]:
            embed = self._get_list_embed(card_id)
        if effect.lower() in ["analysis", "1031"]:
            embed = self._get_analysis_embed(card_id)
        await self.ctx.send(embed=embed)

class Card1038(Card):

    def __init__(self, ctx: commands.Context, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    async def exec(self, card_id:int) -> None:
        self._is_valid_card_check(card_id)

        if card_id == 0:
            raise CheckFailure("Redacted card!")

        User(self.ctx.author.id).remove_card(self.id)

        embed = self._get_list_embed(card_id)
        await self.ctx.send(embed=embed)