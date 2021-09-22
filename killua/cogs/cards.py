import discord
from discord.ext import commands
import random
from datetime import datetime, timedelta
import math

from typing import Union, List, Optional, Tuple, Optional

from killua.utils.checks import check
from killua.utils.paginator import Paginator
from killua.utils.classes import User, CardNotFound, Category, CheckFailure, Book, ConfirmButton, NoMatches
from killua.static.cards import Card
from killua.static.constants import ALLOWED_AMOUNT_MULTIPLE, FREE_SLOTS, DEF_SPELLS, VIEW_DEF_SPELLS, PRICES, BOOK_PAGES, items, LOOTBOXES


class Cards(commands.Cog):

    def __init__(self, client):
        self.client = client

    def _get_single_reward(self, score:int) -> dict:
            if score == 1:
                if random.randint(1,10) < 5:
                    return 1, random.choice([x['_id'] for x in items.find({'type': 'normal', 'rank': { "$in": ['A', 'B', 'C']}})])
                else:
                    return 1, random.choice([x['_id'] for x in items.find({'type': 'spell', 'rank': {"$in": ['B', 'C']}})])

            if score < 3000/10000:
                rarities = ['E', 'G', 'H']
            elif score < 7000/10000:
                rarities = ['D', 'E', 'F']
            else:
                rarities = ['C', 'D', 'E']

            amount = math.ceil(score*(score*random.randint(2, 10)))
            card = random.choice([x['_id'] for x in items.find({'type': 'monster', 'rank': {"$in": rarities}})])
            return amount, card
    
    def _construct_rewards(self, score:int) -> List[Tuple[int, int]]:
        # reward_score will be minutes/10000 which equals a week. Max rewards will get returned once a user has hunted for a week
        rewards = []

        if score >= 1:
            rewards.append(self._get_single_reward(1))
            score = 0.5

        for i in range(math.ceil(score*(score*random.randint(2, 10)))):
            r = self._get_single_reward(score)
            rewards.append(r)
    
        final_rewards = []
        for reward in rewards: 
            # This avoid duplicates e.g. 4xPaladins Necklace, 2xPaladins Necklace => 6xPaladins Necklace
            if reward[1] in (l:= [y for x, y in final_rewards]):
                index = l.index(reward[1])
                final_rewards[index] = (final_rewards[index][0]+reward[0], final_rewards[index][1])
            else:
                final_rewards.append(reward)
        return final_rewards

    def _format_rewards(self, rewards:List[Tuple[int, int]], user:User, score:float) -> Tuple[List[list], List[str], bool]:
        """Formats the generated rewards for further use"""
        formatted_rewards = []
        formatted_text = []
        for reward in rewards:
            for i in range(reward[0]):
                if len([*user.fs_cards,*[x for x in rewards if x[1] > 99 and not user.has_rs_card(x[0])]]) >= 40 and (reward[1] > 99 or (not user.has_rs_card(reward[1]) and reward[1] < 100)):
                    return rewards, formatted_text, True
                formatted_rewards.append([reward[1], {"fake": False, "clone": False}])
            card = Card(reward[1])
            formatted_text.append(f"{reward[0]}x **{card.name}**{card.emoji}")

        return formatted_rewards, formatted_text, False

    @check(3)
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @commands.command(extras={"category":Category.CARDS}, usage="book <page(optional)>")
    async def book(self, ctx, page:int=1):
        """Allows you to take a look at your cards"""
        user = User(ctx.author.id)

        if len(user.all_cards) == 0:
            return await ctx.send('You don\'t have any cards yet!')

        if page:
            if page > 7+math.ceil(len(user.fs_cards)/18) or page < 1:
                return await ctx.send(f'Please choose a page number between 1 and {6+math.ceil(len(user.fs_cards)/18)}')

        async def make_embed(page, embed, pages):
            return await Book(self.client.session).create(ctx.author, page)
        return await Paginator(ctx, page=page, func=make_embed, max_pages=6+math.ceil(len(user.fs_cards)/18), has_file=True).start()

    @check(2)
    @commands.command(extras={"category":Category.CARDS}, usage="sell <card_id> <amount(optional)>")
    async def sell(self, ctx, item:int, amount=1):
        """Sell any amount of cards you own"""
        
        user = User(ctx.author.id)
        if amount < 1:
            amount = 1
        if len(user.all_cards) == 0:
            return await ctx.send('You don\'t have any cards yet!')
        try:
            card = Card(item)
        except CardNotFound:
            return await ctx.send(f'A card with the id `{item}` does not exist', allowed_mentions=discord.AllowedMentions.none())

        in_possesion = user.count_card(card.id, including_fakes=False)

        if in_possesion < amount:
            return await ctx.send(f'Seems you don\'t own enough copies of this card. You own {in_possesion} cop{"y" if in_possesion == 1 else "ies"} of this card')
        
        if item == 0:
            return await ctx.send("You cannot sell this card!")

        jenny = int((PRICES[card.rank]*amount)/10)
        if user.is_entitled_to_double_jenny:
            jenny *= 2
        view = ConfirmButton(ctx.author.id, timeout=80)
        msg = await ctx.send(f"You will receive {jenny} Jenny for selling {'this card' if amount == 1 else 'those cards'}, do you want to proceed?", view=view)
        await view.wait()
        await view.disable(msg)

        if not view.value:
            if view.timed_out:
                return await ctx.send(f'Timed out!')
            else:
                return await ctx.send(f"Successfully canceled!")
            
        card_amount = user.count_card(item, False)

        if not card_amount >= amount:
            return await ctx.send('Seems like you don\'t own enough non-fake copies of this card you try to sell')
        else:
            for i in range(amount):
                user.remove_card(item, False)
            user.add_jenny(jenny)
            await ctx.send(f'Successfully sold {amount} cop{"y" if amount == 1 else "ies"} of card number {item} for {jenny} Jenny!')

    @check(20)
    @commands.command(extras={"category":Category.CARDS}, usage="swap <card_id>")
    async def swap(self, ctx, card_id:int):
        """Allows you to swap cards from your free slots with the restricted slots and the other way around"""
        
        user = User(ctx.author.id)
        if len(user.all_cards) == 0:
            return await ctx.send('You don\'t have any cards yet!')
        try:
            card = Card(card_id)
        except CardNotFound:
            return await ctx.send('Please use a valid card number!')

        if card_id == 0:
            return await ctx.send("You cannot swap out card No. 0!")

        sw = user.swap(card_id)

        if sw is False:
            return await ctx.send(f'You don\'t own a fake and real copy of card `{card.name}` you can swap out!')
        
        await ctx.send(f'Successfully swapped out card No. {card_id}')

    @check()
    @commands.command(extras={"category":Category.CARDS}, usage="hunt <end/time(optional)>")
    async def hunt(self, ctx, end:str=None):
        """Go on a hunt! The longer you are on the hunt, the better the rewards!"""
        
        user = User(ctx.author.id)
        has_effect, value = user.has_effect('hunting')

        if end:

            if end.lower() == 'time':
                if not has_effect:
                    return await ctx.send('You are not on a hunt yet!')
                difference = datetime.now() - value
                return await ctx.send(f'You\'ve been hunting for {difference.days} days, {int((difference.seconds/60)/60)} hours, {int(difference.seconds/60)-(int((difference.seconds/60)/60)*60)} minutes and {int(difference.seconds)-(int(difference.seconds/60)*60)} seconds.')

            if not end.lower() == 'end':
                pass
            elif has_effect is True:
                difference = datetime.now() - value
                if int(difference.seconds/60/60+difference.days*24*60*60) < 12: # I don't think timedelta has an hours or minutes property :c
                    return await ctx.send('You must be at least hunting for twelve hours!')

                minutes = int(difference.seconds/60+difference.days*24*60)
                score = minutes/10800 # There are 10080 minutes in a week if I'm not completely wrong
                
                rewards = self._construct_rewards(score)
                formatted_rewards, formatted_text, hit_limit = self._format_rewards(rewards, user, score)
                text = f'You\'ve been hunting for {difference.days} days, {int((difference.seconds/60)/60)} hours, {int(difference.seconds/60)-(int((difference.seconds/60)/60)*60)} minutes and {int(difference.seconds)-(int(difference.seconds/60)*60)} seconds. You brought back the following items from your hunt: \n\n'
                if hit_limit:
                    text += f":warning:Your free slot limit has been reached! Sell some cards with `{self.client.command_prefix(self.client, ctx.message)[2]}sell` :warning:\n\n"

                if hit_limit and len(user.fs_cards) == 40:
                    text += f"Could not carry anything from your hunt in your free slots so you gained no cards.."

                embed = discord.Embed.from_dict({
                    'title': 'Hunt returned!',
                    'description': text + "\n".join(formatted_text),
                    'color': 0x1400ff
                })
                user.remove_effect('hunting')
                user.add_multi(formatted_rewards)
                return await ctx.send(embed=embed)
                
            elif end.lower() == 'end': 
                return await ctx.send(f'You aren\'t on a hunt yet! Start one with `{self.client.command_prefix(self.client, ctx.message)[2]}hunt`', allowed_mentions=discord.AllowedMentions.none())

        if has_effect:
            return await ctx.send(f'You are already on a hunt! Get the results with `{self.client.command_prefix(self.client, ctx.message)[2]}hunt end`', allowed_mentions=discord.AllowedMentions.none())
        user.add_effect('hunting', datetime.now())
        await ctx.send('You went hunting! Make sure to claim your rewards at least twelve hours from now, but remember, the longer you hunt, the more you get')

    @check(120)
    @commands.command(aliases=['approach'], extras={"category":Category.CARDS}, usage="meet <user>")
    async def meet(self, ctx, user:discord.Member):
        """Meet a user who has recently send a message in this channel to enable certain spell card effects"""

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
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass
            return await ctx.send(f'You already have `{user}` in the list of users you met, {ctx.author.name}', delete_after=2, allowed_mentions=discord.AllowedMentions.none())

        author.add_met_user(user.id)
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
        return await ctx.send(f'Done {ctx.author.mention}! Successfully added `{user}` to the list of people you\'ve met', delete_after=5, allowed_mentions=discord.AllowedMentions.none())
            
    @check()
    @commands.command(extras={"category":Category.CARDS}, usage="discard <card_id>")
    async def discard(self, ctx, card:int):
        """Discard a card you want to get rid of with this command. If you want to throw a fake away, make sure it's in the free slots"""
        
        user = User(ctx.author.id)
        try:
            card = Card(card)
        except CardNotFound:
            return await ctx.send('This card does not exist!')

        if not user.has_any_card(card.id):
            return await ctx.send('You are not in possesion of this card!')

        if card.id == 0:
            return await ctx.send("You cannot discard this card!")

        view = ConfirmButton(ctx.author.id, timeout=20)
        msg = await ctx.send(f"Do you really want to throw this card away? (if you want to throw a fake aware, make sure it's in the free slots (unless it's the only copy you own. You can switch cards between free and restricted slots with `{self.client.command_prefix(self.client, ctx.message)[2]}swap <card_id>`)", view=view, allowed_mentions=discord.AllowedMentions.none())
        await view.wait()
        await view.disable(msg)

        if not view.value:
            if view.timed_out:
                return await ctx.send(f'Timed out!')
            else:
                return await ctx.send(f"Successfully canceled!")

        try:
            user.remove_card(card.id, remove_fake=True, restricted_slot=False)
            # essentially here it first looks for fakes in your free slots and tried to remove them. If it doesn't find any fakes in the free slots, it will remove the first match of the card it finds in free or restricted slots
        except NoMatches:
            user.remove_card(card.id)
        await ctx.send(f'Successfully thrown away card No. `{card.id}`')

    @commands.command(aliases=["read"], extras={"category": Category.CARDS}, usage="cardinfo <card_id>")
    async def cardinfo(self, ctx, card:int):
        """Check card info out about any card you own"""
        try:
            c = Card(card)
        except CardNotFound:
            return await ctx.send("Invalid card")

        author = User(ctx.author.id)
        if not author.has_any_card(c.id):
            return await ctx.send("You don't own a copy of this card so you can't view it's infos")

        embed = c._get_analysis_embed(c.id)
        if c.type == "spell" and c.id not in [*DEF_SPELLS, *VIEW_DEF_SPELLS]:
            card_class = [c for c in Card.__subclasses__() if c.__name__ == f"Card{card}"][0]
            usage = f"`{self.client.command_prefix(self.client, ctx.message)[2]}use {card} " + " ".join([f"[{k}: {v.__name__}]" for k, v in card_class.exec.__annotations__.items() if not str(k) == "return"]) + "`"
            embed.add_field(name="Usage", value=usage, inline=False)

        await ctx.send(embed=embed)

    @check()
    @commands.command(name="check", extras={"category": Category.CARDS}, usage="check <card_id>")
    async def _check(self, ctx, card_id:int):
        """Lets you see how many copies of the specified card are fakes"""
        try:
            Card(card_id)
        except CardNotFound:
            return await ctx.send("Invalid card")

        author = User(ctx.author.id)

        if not author.has_any_card(card_id, only_allow_fakes=True):
            return await ctx.send("You don't any copies of this card which are fake")

        text = ""

        if len([x for x in author.rs_cards if x[1]["fake"] is True and x[0] == card_id]) > 0:
            text += f"The card in your restricted slots is fake"

        if (fs:= len([x for x in author.fs_cards if x[1]["fake"] is True and x[0] == card_id])) > 0:
            text += (" and " if len(text) > 0 else "") + f"{fs} cop{'ies' if fs > 1 else 'y'} of this card in your free slots {'are' if fs > 1 else 'is'} fake"

        if len(text) == 0:
            text = "No fake copies of that card!"

        await ctx.send(text)

    def _use_check(self, ctx, item:int, args:Optional[Union[discord.Member, int, str]], add_args: Optional[int]) -> None:
        """Makes sure the inputs are valid if they exist"""
        if item in [*DEF_SPELLS, *VIEW_DEF_SPELLS]:
            raise CheckFailure('You can only use this card in response to an attack!')

        try:
            if Card(item).type != "spell":
                raise CheckFailure("You can only use spell cards!")
        except CardNotFound:
            raise CheckFailure("Invalid card id")

        if not item in [x[0] for x in User(ctx.author.id).fs_cards] and not item in [1036]:
            raise CheckFailure('You are not in possesion of this card!')

        if args:
            if isinstance(args, discord.Member):
                if args.id == ctx.author.id:
                    raise CheckFailure('You can\'t use spell cards on yourself')
                elif args.bot:
                    raise CheckFailure("You can't use spell cards on bots")

            if isinstance(args, int):
                if args < 1:
                    raise CheckFailure('You can\'t use an integer less than 1')

        if add_args:
            if add_args < 1:
                raise CheckFailure('You can\'t use an integer less than 1')

    async def _use_core(self, ctx, item:int, *args) -> None:
        """This passes the execution to the right class """
        card_class = [c for c in Card.__subclasses__() if c.__name__ == f"Card{item}"][0]
        
        l = []
        for p, (k, v) in enumerate([x for x in card_class.exec.__annotations__.items() if not str(x[0]) == "return"]):
            if len(args) > p and isinstance(args[p], v):
                l.append({k: args[p]})
            else:
                l.append(None)

        if None in l:
            return await ctx.send(f"Invalid arguments provided! Usage: `{self.client.command_prefix(self.client, ctx.message)[2]}use {item} " + " ".join([f"[{k}: {v.__name__}]" for k, v in card_class.exec.__annotations__.items() if not str(k) == "return"]) + "`", allowed_mentions=discord.AllowedMentions.none())
        kwargs = {k: v for d in l for k, v in d.items()}
        try:
            await card_class(ctx, card_id=item).exec(**kwargs)
        except Exception as e:
            await ctx.send(e.message, allowed_mentions=discord.AllowedMentions.none())

    @check()
    @commands.command(extras={"category":Category.CARDS}, usage="use <card_id> <required_arguments>")
    async def use(self, ctx, item: Union[int,str], args: Union[discord.Member, int, str]=None, add_args:int=None):
        """Use spell cards you own with this command! Focus on offense or defense, team up with your friends or steal their cards in their sleep!"""
        
        if isinstance(item, str):
            if not item.lower() == 'booklet':
                return await ctx.send('Either use a spell card with this command or the booklet')

            def make_embed(page, embed, pages):
                embed.title = "Introduction booklet"
                embed.description = pages[page-1]
                embed.set_image(url="https://cdn.discordapp.com/attachments/759863805567565925/834794115148546058/image0.jpg")
                return embed

            return await Paginator(ctx, BOOK_PAGES, func=make_embed).start()

        try:
            self._use_check(ctx, item, args, add_args)
        except CheckFailure as e:
            return await ctx.send(e.message)

        args = [x for x in [args, add_args] if x]

        await self._use_core(ctx, item, *args)

    @commands.is_owner()
    @commands.command(extras={"category":Category.CARDS}, usage="gain <type> <card_id/amount/lootbox>", hidden=True)
    async def gain(self, ctx, t:str, item:str):
        """An owner restricted command allowing the user to obtain any card or amount of jenny or any lootbox"""
        user = User(ctx.author.id)
        if not t.lower() in ["jenny", "card", "lootbox"]:
            return await ctx.send(f'You need to provide a valid type! `{self.client.command_prefix(self.client, ctx.message)[2]}gain <jenny/card/lootbox> <amount/id>`', allowed_mentions=discord.AllowedMentions.none())
        if t.lower() == 'card':
            try:
                item = int(item)
                card = Card(item)
            except CardNotFound:
                return await ctx.send('Invalid card id')
            if card.id == 0:
                return await ctx.send("No")
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
            if item > 69420:
                return await ctx.send('Be reasonable.')
            user.add_jenny(item)
            return await ctx.send(f'Added {item} Jenny to your account')

        if t.lower() == "lootbox":
            if not item.isdigit() or not int(item) in list(LOOTBOXES.keys()):
                return await ctx.send("Invalid lootbox!")
            user.add_lootbox(int(item))
            return await ctx.send(f"Done! Added lootbox \"{LOOTBOXES[int(item)]['name']}\" to your inventory")

Cog = Cards

def setup(client):
    client.add_cog(Cards(client))
