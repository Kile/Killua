import discord
from discord.ext import commands, tasks
import random
from datetime import datetime, timedelta
import asyncio
import math
import typing
from PIL import Image, ImageFont, ImageDraw
import io
import aiohttp
import pathlib

from typing import Union, List, Optional

from killua.checks import check
from killua.paginator import Paginator
from killua.classes import User, Card, CardLimitReached, CardNotFound, Category
from killua.constants import ALLOWED_AMOUNT_MULTIPLE, FREE_SLOTS, DEF_SPELLS, VIEW_DEF_SPELLS, INDESTRUCTABLE, PRICES, BOOK_PAGES, teams, items, shop, LOOTBOXES

# I am NOT writing a detailed description of every function in here, just a brief description for functions in classes

class Cards(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.cached_cards = {}
        self.cached_background = {}

    # Contribution by DerUSBStick (Thank you!)
    async def _imagefunction(self, data, restricted_slots, page:int):
        background = await self._getbackground(0 if len(data) == 10 else 1)
        if len(data) == 18 and restricted_slots:
            background = await self._numbers(background, data, page)
        background = await self._cards(background, data, 0 if len(data) == 10 else 1)
        background = await self._setpage(background, page)
        return background

    def _get_from_cache(self, types:int) -> Union[Image.Image, None]:
        if types == 0:
            if "first_page" in self.cached_background:
                return self.cached_background["first_page"]
            return
        else:
            if "default_background" in self.cached_background:
                return self.cached_background["default_background"]
            return
        
    def _set_cache(self, data:Image, first_page:bool) -> None:
        self.cached_background["first_page" if first_page else "default_background"] = data

    async def _getbackground(self, types) -> Image.Image:
        url = ['https://alekeagle.me/XdYUt-P8Xv.png', 'https://alekeagle.me/wp2mKvzvCD.png']
        if (res:= self._get_from_cache(types)):
            return res.convert("RGB")

        async with self.client.session.get(url[types]) as res: 
            image_bytes = await res.read()
            background = (img:= Image.open(io.BytesIO(image_bytes))).convert('RGB') 

        self._set_cache(img, types == 0)
        return background

    async def _getcard(self, url) -> Image.Image:

        async with self.client.session.get(url) as res:
            image_bytes = await res.read()
            image_card = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            image_card = image_card.resize((80, 110), Image.ANTIALIAS)
        await asyncio.sleep(0.3) # This is to hopefully prevent aiohttp's "Response payload is not completed" bug
        return image_card

    async def _setpage(self, image, page):
        font = await self._getfont(20)
        draw = ImageDraw.Draw(image)
        draw.text((5, 385), f'{page*2-1}', (0,0,0), font=font)
        draw.text((595, 385), f'{page*2}', (0,0,0), font=font)
        return image

    async def _getfont(self, size) -> ImageFont.ImageFont:
        font = ImageFont.truetype(str(pathlib.Path(__file__).parent.parent) + "/font.ttf", size, encoding="unic") 
        return font

    async def _cards(self, image, data, option):

        card_pos:list = [
            [(113, 145),(320, 15),(418, 15),(516, 15),(320, 142),(418, 142),(516, 142),(320, 269),(418, 269),(516, 269)],
            [(15,17),(112,17),(210,17),(15,144),(112,144),(210,144),(15,274),(112,274),(210,274),(320,13),(418,13),(516,13),(320,143),(418,143),(516,143),(320,273),(418,273),(516,273)]
        ]
        for n, i in enumerate(data): 
            if i:
                if i[1]:
                    if not str(i[0]) in self.cached_cards: # Kile part (I wrote a small optimasation algorithm which avoids fetching the same card and just uses the same data)
                        self.cached_cards[str(i[0])] = await self._getcard(i[1])

                    image.paste(self.cached_cards[str(i[0])], (card_pos[option][n]))
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

        font = await self._getfont(35)
        draw = ImageDraw.Draw(image)
        for n, i in enumerate(data):
            if i[1] is None:
                draw.text(numbers_pos[page][n], f'0{i[0]}', (165,165,165), font=font)
        return image

    async def _get_book(self, user, page:int, just_fs_cards:bool=False):
        rs_cards = list()
        fs_cards = list()
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
                    rs_cards.append([i, Card(i).image_url])
                if page == 1 and len(rs_cards) == 10:
                    break
                i = i+1
        else:
            i = (page-7)*18 
            while (len(fs_cards) % 18 == 0) == False or (len(fs_cards) == 0) == True: 
                try:
                    fs_cards.append([person.fs_cards[i][0], Card(person.fs_cards[i][0]).image_url])
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

    @check(3)
    @commands.command(extras={"category":Category.CARDS}, usage="book <page(optional)>")
    async def book(self, ctx, page:int=1):
        """Allows you to take a look at your cards"""
        user = User(ctx.author.id)

        if len(user.all_cards) == 0:
            return await ctx.send('You don\'t have any cards yet!')

        if page:
            if page > 7+math.ceil(len(User(ctx.author.id).fs_cards)/18) or page < 1:
                return await ctx.send(f'Please choose a page number between 1 and {6+math.ceil(len(User(ctx.author.id).fs_cards)/18)}')

        async def make_embed(page, embed, pages):
            return await self._get_book(ctx.author, page)
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
            return await ctx.send(f'A card with the id `{item}` does not exist')
        in_possesion = user.count_card(card.id, including_fakes=False)

        if in_possesion < amount:
            return await ctx.send(f'Seems you don\'t own enough copis of this card. You own {in_possesion} cop{"y" if in_possesion == 1 else "ies"} of this card')
        

        view = ConfirmButton(ctx.author.id, timeout=80)
        msg = await ctx.send(f"You will recieve {int((PRICES[card.rank]*amount)/10)} Jenny for selling {'this card' if amount == 1 else 'those cards'}, do you want to proceed?", view=view)
        await view.wait()
        await view.disable(msg)

        if not view.value:
            if view.timed_out:
                return await ctx.send(f'Timed out!')
            else:
                return await ctx.send(f"Successfully canceled!")
            
        card_amount = user.count_card(item, False)

        if not card_amount >= amount:
            return await ctx.send('Seems like you don\'t own enoug ch non-fake copies of this card you try to sell')
        else:
            for i in range(amount):
                user.remove_card(item, False)
            user.add_jenny(int((PRICES[card.rank]*amount)/10))
            await ctx.send(f'Sucessfully sold {amount} cop{"y" if amount == 1 else "ies"} of card number {item} for {int((PRICES[card.rank]*amount)/10)} Jenny!')

    @check(20)
    @commands.command(extras={"category":Category.CARDS}, usage="swap <card_id>")
    async def swap(self, ctx, card_id:int):
        """Allows you to swap cards from your free slots with the restrcited slots and the other way around"""
        
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
            return await ctx.send(f'You already have `{user}` in the list of users you met, {ctx.author.name}', delete_after=2)

        author.add_met_user(user.id)
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
        return await ctx.send(f'Done {ctx.author.mention}! Successfully added `{user}` to the list of people you\'ve met', delete_after=5)
            
    @check()
    @commands.command(extras={"category":Category.CARDS}, usage="discard <card_id>")
    async def discard(self, ctx, card:int):
        """Discard a card you want to get rid of with this command"""
        
        user = User(ctx.author.id)
        try:
            card = Card(card)
        except CardNotFound:
            return await ctx.send('This card does not exist!')

        if not user.has_any_card(card.id):
            return await ctx.send('You are not in possesion of this card!')

        view = ConfirmButton(ctx.author.id, timeout=20)
        msg = await ctx.send(f"Do you really want to throw this card away? (be aware that this will throw the first card you own with this id away, if you want to get rid of a fake swap it out of your album with `{self.client.command_prefix(self.client, ctx.message)[2]}swap <card_id>`)", view=view)
        await view.wait()
        await view.disable(msg)

        if not view.value:
            if view.timed_out:
                return await ctx.send(f'Timed out!')
            else:
                return await sctx.send(f"Successfully canceled!")

            user.remove_card(card.id)
            await ctx.send(f'Successfully thrown away card No. `{card.id}`')

    @check()
    @commands.command(extras={"category":Category.CARDS}, usage="use <card_id> <required_arguments>")
    async def use(self, ctx, item: typing.Union[int,str], args: typing.Union[discord.Member, str, int]=None, add_args:int=None):
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

    @commands.has_role(874625525287649360)
    @commands.command(extras={"category":Category.CARDS}, usage="gain <type> <card_id/amount/lootbox>")
    async def gain(self, ctx, t:str, item:str):
        """An owner restricted command allowing the user to obtain any card or amount of jenny or any lootbox"""
        user = User(ctx.author.id)
        if not t.lower() in ["jenny", "card", "lootbox"]:
            return await ctx.send(f'You need to provide a valid type! `{self.client.command_prefix(self.client, ctx.message)[2]}gain <jenny/card/lootbox> <amount/id>`')
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

        if t.lower() == "lootbox":
            if not item.isdigit() or not int(item) in list(LOOTBOXES.keys()):
                return await ctx.send("Invalid lootbox!")
            user.add_lootbox(int(item))
            return await ctx.send(f"Done! Added lootbox \"{LOOTBOXES[int(item)]['name']}\" to your inventory")

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
    async def make_embed(page, embed, pages):
        return await self._get_book(member, page)

    return await Paginator(ctx, max_pages=6+math.ceil(len(User(member.id).fs_cards)/18), func=make_embed, has_file=True).start()

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

    await ctx.send(f'Successfully swapped cards! Gave {member} the card `{removed_attackist_card[0]}` and took card number `{removed_card_other[0]}` from them!')

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
    async def make_embed(page, embed, pages):
        return await self._get_book(member, page)

    return await Paginator(ctx, max_pages=6, func=make_embed, has_file=True).start()

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

    async def make_embed(page, embed, pages):
        return await self._get_book(member, page, True)

    return await Paginator(ctx, max_pages=math.ceil(len(User(member.id).fs_cards)/18), func=make_embed, has_file=True).start()  

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

    rewards = list()
    def rw(reward_score:int):
        if reward_score == 1:
            if random.randint(1,10) < 5:
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


Cog = Cards

def setup(client):
    client.add_cog(Cards(client))
