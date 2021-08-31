import discord
from random import randint, choice
from discord.ext import commands, tasks
from datetime import datetime
from typing import Union, Tuple

from killua.cards import Card
from killua.classes import Category, User, TodoList, PrintColors, CardNotFound, Button
from killua.constants import items, shop, FREE_SLOTS, ALLOWED_AMOUNT_MULTIPLE, PRICES, LOOTBOXES, editing
from killua.checks import check
from killua.paginator import DefaultEmbed, View, Paginator
from killua.help import Select

class ShopPaginator(Paginator):
    """A normal paginator with a button that returns to the original shop select menu"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.view.add_item(Button(label="Menu", style=discord.ButtonStyle.blurple, custom_id="1"))

    async def start(self):
        view = await self._start()

        if view.ignore:
            return
        
        await self.view.message.delete()
        if self.ctx.command.parent:
            await self.ctx.invoke(self.ctx.command.parent)
        else:
            await self.ctx.invoke(self.ctx.command)

class Shop(commands.Cog):

    def __init__(self, client):
        self.client = client

    def _format_offers(self, offers:list, reduced_item:int=None, reduced_by:int=None):
        formatted:list = []
        if reduced_item and reduced_by:
            x:int = 0
            for offer in offers:
                formatted.append(self._format_item(offer, reduced_item, reduced_by, x))
                x = x+1
        else:
            for offer in offers:
                formatted.append(self._format_item(offer))

        return formatted

    def _format_item(self, offer:int, reduced_item:int=None, reduced_by:int=None, number:int=None):
        item = items.find_one({'_id': int(offer)})
        if reduced_item:
            if number == reduced_item:
                return {'name':f'**Number {item["_id"]}: {item["name"]}** |{item["emoji"]}|', 'value': f'**Description:** {item["description"]}\n**Price:** {PRICES[item["rank"]]-int(PRICES[item["rank"]]*(reduced_by/100))} (Reduced by **{reduced_by}%**) Jenny\n**Type:** {item["type"].replace("normal", "item")}\n**Rarity:** {item["rank"]}'}  
        
        return {'name':f'**Number {item["_id"]}: {item["name"]}** |{item["emoji"]}|', 'value': f'**Description:** {item["description"]}\n**Price:** {PRICES[item["rank"]]} Jenny\n**Type:** {item["type"].replace("normal", "item")}\n**Rarity:** {item["rank"]}'}


    @commands.Cog.listener()
    async def on_connect(self):
        #if not self.client.user.id == 758031913788375090:
        self.cards_shop_update.start()
    
    @tasks.loop(hours=6)
    async def cards_shop_update(self):
        #There have to be 4-5 shop items, inserted into the db as a list with the card numbers
        #the challenge is to create a balanced system with good items rare enough but not too rare
        try:
            shop_items:list = []
            number_of_items = randint(3,5) #How many items the shop has
            if randint(1,100) > 95:
                #Add a S/A card to the shop
                thing = [i['_id'] for i in items.find({'type': 'normal', 'rank': {"$in": ['A', 'S']}})]
                shop_items.append(choice(thing))
            if randint(1,100) > 20: #80% chance for spell
                if randint(1, 100) > 95: #5% chance for a good spell (they are rare)
                    spells = [s['_id'] for s in items.find({'type': 'spell', 'rank': 'A'})]
                    shop_items.append(choice(spells))
                elif randint(1,10) > 5: #50% chance of getting a medium good card
                    spells = [s['_id'] for s in items.find({'type': 'spell', 'rank': {"$in": ['B', 'C']}})]
                    shop_items.append(choice(spells))
                else: #otherwise getting a fairly normal card
                    spells = [s['_id'] for s in items.find({'type': 'spell', 'rank': {"$in": ['D', 'E', 'F', 'G']}})]
                    shop_items.append(choice(spells))

                while len(shop_items) != number_of_items: #Filling remaining spots
                    thing = [t['_id'] for t in items.find({'type': 'normal', 'rank': {"$in": ['D', 'B']}})] 
                    #There is just one D item so there is a really high probability of it being in the shop EVERY TIME
                    t = choice(thing)
                    if not t in shop_items:
                        shop_items.append(t)

                log = shop.find_one({'_id': 'daily_offers'})['log']
                if randint(1, 10) > 6: #40% to have an item in the shop reduced
                    reduced_item = randint(0, len(shop_items)-1)
                    reduced_by = randint(15, 40)
                    print(f'{PrintColors.OKBLUE}Updated shop with following cards: ' + ', '.join([str(x) for x in shop_items])+f', reduced item number {shop_items[reduced_item]} by {reduced_by}%{PrintColors.ENDC}')
                    log.append({'time': datetime.now(), 'items': shop_items, 'reduced': {'reduced_item': reduced_item, 'reduced_by': reduced_by}})
                    shop.update_many({'_id': 'daily_offers'}, {'$set': {'offers': shop_items, 'log': log, 'reduced': {'reduced_item': reduced_item, 'reduced_by': reduced_by}}})
                else:
                    print(f"{PrintColors.OKBLUE}Updated shop with following cards: {', '.join([str(x) for x in shop_items])}{PrintColors.ENDC}")
                    log.append({'time': datetime.now(), 'items': shop_items, 'redued': None})
                    shop.update_many({'_id': 'daily_offers'}, {'$set': {'offers': shop_items, 'log': log, 'reduced': None}})
        except IndexError:
            print(f"{PrintColors.WARNING}Shop could not be loaded, card data is missing{PrintColors.ENDC}")

    def _get_view(self, ctx) -> View:
        view = View(ctx.author.id)
        view.add_item(Button(label="Menu", style=discord.ButtonStyle.blurple))
        return view

    async def _shop_menu(self, ctx, msg, view) -> None:
        await view.wait()
        await view.disable(msg)
        if view.value:
            await msg.delete()
            if ctx.command.parent:
                await ctx.invoke(ctx.command.parent) #in case the menu was invoked by a subcommand
            else:
                await ctx.invoke(ctx.command) # in case the menu was invoked by the parent

    @commands.group(aliases=["store"])
    async def shop(self, ctx):
        if not ctx.invoked_subcommand:
            subcommands = [c for c in ctx.command.commands]

            view = View(ctx.author.id)
            view.add_item(Select(options=[discord.SelectOption(label=f"{c.name} shop", value=str(i)) for i, c in enumerate(subcommands)]))
            embed = discord.Embed.from_dict({
                "title": "Shop menu",
                "description": "Select the shop you want to visit",
                "image": {"url": "https://static.wikia.nocookie.net/hunterxhunter/images/0/08/Spell_Card_Store.png/revision/latest?cb=20130328063032"},
                "color": 0x1400ff
            })
            msg = await ctx.send(embed=embed, view=view)
            await view.wait()

            await view.disable(msg)
            if view.value is None:
                return

            await msg.delete()
            await ctx.invoke(subcommands[int(view.value)]) # calls a shop subcommand if a shop was specified

    @check()
    @shop.command(name="cards", extras={"category":Category.CARDS}, usage="cards")
    async def cards_shop(self, ctx):
        """Shows the current cards for sale"""
        
        sh = shop.find_one({'_id': 'daily_offers'})
        shop_items:list = sh['offers']

        if not sh['reduced'] is None:
            reduced_item = sh['reduced']['reduced_item']
            reduced_by = sh['reduced']['reduced_by']
            formatted = self._format_offers(shop_items, reduced_item, reduced_by)
            embed = discord.Embed(title='Current Card shop', description=f'**{items.find_one({"_id": shop_items[reduced_item]})["name"]} is reduced by {reduced_by}%**')
        else:
            formatted:list = self._format_offers(shop_items)
            embed = discord.Embed(title='Current Card shop')

        embed.color = 0x1400ff
        embed.set_thumbnail(url='https://static.wikia.nocookie.net/hunterxhunter/images/0/08/Spell_Card_Store.png/revision/latest?cb=20130328063032')
        for item in formatted:
            embed.add_field(name=item['name'], value=item['value'], inline=False)
        view = self._get_view(ctx)
        msg = await ctx.send(embed=embed, view=view)
        await self._shop_menu(ctx, msg, view)

    @check()
    @shop.command(name="todo", extras={"category": Category.TODO}, usage="todo")
    async def todo_shop(self, ctx):
        """Get some info about what cool stuff you can buy for your todo list with this command"""
        prefix = self.client.command_prefix(self.client, ctx.message)[2]
        embed = discord.Embed.from_dict({
            'title': '**The todo shop**',
            'description': f'''You can buy the following items with `{prefix}buy todo <item>` while you are in the edit menu for the todo list you want to buy the item for
            
**Cost**: 1000 Jenny
`color` change the color of the embed which displays your todo list!

**Cost**: 1000 Jenny
`thumbnail` add a neat thumbnail to your todo list (small image on the top right)

**Cost**: 1000 Jenny
`description` add a description to your todo list (recommended for public lists with custom id)

**Cost**: number of current spots * 50
`space` buy 10 more spots for todo's for your list''',
            'color': 0x1400ff
        })
        view = self._get_view(ctx)
        msg = await ctx.send(embed=embed, view=view)
        await self._shop_menu(ctx, msg, view)

    @check()
    @shop.command(name="lootboxes", aliases=["boxes"], extras={"category": Category.ECONOMY}, usage="lootboxes")
    async def lootboxes_shop(self, ctx):
        """Get the current lootbox shop with this command"""
        prefix = self.client.command_prefix(self.client, ctx.message)[2]
        fields = [{"name": data["emoji"] + " " + data["name"] + " (id: " + str(id) + ")", "value": f"{data['description']}\nPrice: {data['price']}"} for id, data in LOOTBOXES.items() if data["available"]]

        def make_embed(page, embed, pages):
            embed.title = "Current lootbox shop"
            embed.description = f"To get infos about what a lootbox contains, use `{prefix}boxinfo <box_id>`\nTo buy a box, use `{prefix}buy lootbox <box_id>`"
            embed.clear_fields()
            if len(pages)-page*10+10 > 10:
                for x in pages[page*10-10:-(len(pages)-page*10)]:
                    embed.add_field(name=x["name"], value=x["value"], inline=False)
            elif len(pages)-page*10+10 <= 10:
                for x in pages[-(len(pages)-page*10+10):]:
                    embed.add_field(name=x["name"], value=x["value"], inline=False)

            return embed

        if len(fields) <= 10:
            embed = make_embed(1, DefaultEmbed(), fields)
            view = self._get_view(ctx)
            msg = await ctx.send(embed=embed, view=view)
            return await self._shop_menu(ctx, msg, view)

        await ShopPaginator(ctx, fields, func=make_embed).start() # currently only 10 boxes exist so this is not necessary

####################################### Buy commands ################################################

    async def _wait_for_response(self, step, check) -> Union[discord.Message, None]:
        """Waits for a response and returns the response message"""
        try:
            confirmmsg = await self.client.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            await step.delete()
            await step.channel.send('Too late...', delete_after=5)
            return None
        else:
            await step.delete()
            try:
                await confirmmsg.delete()
            except discord.HTTPException:
                pass
            return confirmmsg

    async def buy_color(self, ctx):
        """outsourcing todo buy in smaller functions. Will be rewritten once discord adds text input interaction"""
        list_id = editing[ctx.author.id]
        todo_list = TodoList(list_id)
        user = User(ctx.author.id)
        if user.jenny < 1000:
            return await ctx.send('You don\'t have enough Jenny to buy a color for your todo list. You need 1000 Jenny')
        
        if todo_list.color:
            return await ctx.send(f'You already have bought a color for this list! Update it with `{self.client.command_prefix(self.client, ctx.message)[2]}todo color <color>`', allowed_mentions=discord.AllowedMentions.none())

        step = await ctx.send('Please provide a color you want your todo list to have, you can always change it later')
        def check(m):
            return m.author.id == ctx.author.id

        confirmmsg = await self._wait_for_response(step, check)
        if not confirmmsg:
            return
        c = f'0x{confirmmsg.content}'
        try:
            if not int(c, 16) <= 16777215:
                await ctx.send('You need to provide a valid color! (Default color is 1400ff f.e.)')
                return await self.buy_color(ctx)
        except Exception:
            await ctx.send('You need to provide a valid color! (Default color is 1400ff f.e.)')
            return await self.buy_color(ctx)

        user.remove_jenny(1000)
        todo_list.set_property('color', int(c, 16))
        return await ctx.send(f'Successfully bought the color {confirmmsg.content} for your list! You can change it with `{self.client.command_prefix(self.client, ctx.message)[2]}todo color <color>`', allowed_mentions=discord.AllowedMentions.none())


    async def buy_thumbnail(self, ctx):
        """outsourcing todo buy in smaller functions. Will be rewritten once discord adds text input interaction"""
        list_id = editing[ctx.author.id]
        todo_list = TodoList(list_id)
        user = User(ctx.author.id)
        if user.jenny < 1000:
            return await ctx.send('You don\'t have enough Jenny to buy a thumbnail for your todo list. You need 1000 Jenny')

        if todo_list.thumbnail:
            return await ctx.send(f'You already have bought a thumbnail for this list! Update it with `{self.client.command_prefix(self.client, ctx.message)[2]}todo thumbnail <url>`', allowed_mentions=discord.AllowedMentions.none())

        step = await ctx.send('Please provide a thumbnail you want your todo list to have, you can always change it later')
        def check(m):
            return m.author.id == ctx.author.id

        confirmmsg = await self._wait_for_response(step, check)
        if not confirmmsg:
            return

        url = re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))', confirmmsg.content)

        if url:
            image = re.search(r'png|jpg|gif|svg', confirmmsg.content)
        else:
            await ctx.send('You didn\'t provide a valid url with an image! Please make sure your url is valid')
            return await self.buy_thumbnail(ctx)
                
        if image:
            user.remove_jenny(1000)
            todo_list.set_property('thumbnail', confirmmsg.content)
            return await ctx.send(f'Successfully bought the thumbmail `{confirmmsg.content}` for your list! You can change it with `{self.client.command_prefix(self.client, ctx.message)[2]}todo thumbnail <url>`', allowed_mentions=discord.AllowedMentions.none())
        else:
            await ctx.send('You didn\'t provide a valid url with an image! Please make sure you your url is valid')
            return await self.buy_thumbnail(ctx)

    async def buy_space(self, ctx):
        # This is the best thing to buy for your todo list
        """outsourcing todo buy in smaller functions"""
        list_id = editing[ctx.author.id]
        todo_list = TodoList(list_id)
        user = User(ctx.author.id)

        if user.jenny < (todo_list.spots * 100 * 0.5):
            return await ctx.send(f'You don\'t have enough Jenny to buy more space for your todo list. You need {todo_list["spots"]*100} Jenny')

        if todo_list.spots >= 100:
            return await ctx.send('You can\'t buy more than 100 spots')

        view = ConfirmButton(ctx.author.id, timeout=10)
        msg = await ctx.send(f'Do you want to buy 10 more to-do spots for this list? \nCurrent spots: {todo_list.spots} \nCost: {int(todo_list.spots*100*0.5)} points', view=view)
        await view.wait()
        await view.disable(msg)

        if not view.value:
            if view.timed_out:
                return await ctx.send(f'Timed out')
            else:
                return await ctx.send(f"Alright, see you later then :3")

        user.remove_jenny(int(100*todo_list.spots*0.5))
        todo_list.add_spots(10)
        return await ctx.send('Congrats! You just bought 10 more todo spots for the current todo list!')

    async def buy_description(self, ctx):
        #Hi! You found a random comment! Now you have to vote for Killua :3 (Also thanks for checking out my code)
        """outsourcing todo buy in smaller functions"""
        list_id = editing[ctx.author.id]
        todo_list = TodoList(list_id)
        user = User(ctx.author.id)
        if user.jenny < 1000:
            return await ctx.send('You don\'t have enough Jenny to buy a thumbnail for your todo list. You need 1000 Jenny')
        
        step = await ctx.send(f'What should the description of your todo list be? (max 200 characters)')
        def check(m):
            return m.author.id == ctx.author.id
        
        confirmmsg = await self._wait_for_response(step, check)
        if not confirmmsg:
            return

        if len(confirmmsg.content) > 200:
            await ctx.send('Your description can\'t be over 200 characters!')
            return await self.buy_description(ctx)
        user.remove_jenny(1000)
        todo_list.set_property('description', description)
        return await ctx.send('Congrats! You bought a description for your current todo list')

    @commands.group()
    async def buy(self, ctx):
        # have a shop for everything, you also need a buy for everything 
        if not ctx.invoked_subcommand:
            return await ctx.send("You need to provide a valid subcommand! Subcommands are: `card`, `lootbox` and `todo`")

    @check(2)
    @buy.command(extras={"category": Category.CARDS}, usage="card <card_id>")
    async def card(self, ctx, item:int):
        """Buy a card from the shop with this command"""
        
        shop_data = shop.find_one({'_id': 'daily_offers'})
        shop_items = shop_data['offers']
        user = User(ctx.author.id)

        try:
            card = Card(item)
        except CardNotFound:
            return await ctx.send(f'This card is not for sale at the moment! Find what cards are in the shop with `{self.client.command_prefix(self.client, ctx.message)[2]}shop`', allowed_mentions=discord.AllowedMentions.none())

        if not item in shop_items:
            return await ctx.send(f'This card is not for sale at the moment! Find what cards are in the shop with `{self.client.command_prefix(self.client, ctx.message)[2]}shop`', allowed_mentions=discord.AllowedMentions.none())

        if not shop_data['reduced'] is None:
            if shop_items.index(card.id) == shop_data['reduced']['reduced_item']:
                price = int(PRICES[card.rank] - int(PRICES[card.rank] * shop_data['reduced']['reduced_by']/100))
            else:
                price = PRICES[card.rank]
        else:
            price = PRICES[card.rank]

        if len(card.owners) >= (card.limit * ALLOWED_AMOUNT_MULTIPLE):
            return await ctx.send('Unfortunately the global maximal limit of this card is reached! Someone needs to sell their card for you to buy one or trade/give it to you')

        if len(user.fs_cards) >= FREE_SLOTS:
            return await ctx.send(f'Looks like your free slots are filled! Get rid of some with `{self.client.command_prefix(self.client, ctx.message)[2]}sell`', allowed_mentions=discord.AllowedMentions.none())

        if user.jenny < price:
            return await ctx.send(f'I\'m afraid you don\'t have enough Jenny to buy this card. Your balance is {user.jenny} while the card costs {price} Jenny')
        try:
            user.add_card(item)
        except Exception as e:
            if isinstance(e, CardLimitReached):
                return await ctx.send(f'Free slots card limit reached (`{FREE_SLOTS}`)! Get rid of one card in your free slots to add more cards with `{self.client.command_prefix(self.client, ctx.message)[2]}sell <card>`', allowed_mentions=discord.AllowedMentions.none())
            else:
                print(e)

        user.remove_jenny(price) #Always putting substracting points before giving the item so if the payment errors no item is given
        return await ctx.send(f'Successfully bought card number `{card.id}` {card.emoji} for {price} Jenny. Check it out in your inventory with `{self.client.command_prefix(self.client, ctx.message)[2]}book`!', allowed_mentions=discord.AllowedMentions.none())

    @check(2)
    @buy.command(aliases=["box"], extras={"category": Category.ECONOMY}, usage="lootbox <item>")
    async def lootbox(self, ctx, box:int):
        """Buy a lootbox with this command"""
        if not box in LOOTBOXES or not LOOTBOXES[box]["available"]:
            return await ctx.send("This lootbox is not for sale!")

        user = User(ctx.author.id)

        if user.jenny < (price:=LOOTBOXES[box]["price"]):
            return await ctx.send(f"You don't have enough jenny to buy this box (You have: {user.jenny}, cost: {price})")

        user.remove_jenny(price)
        user.add_lootbox(box)
        return await ctx.send(f"Successfully bought lootbox {LOOTBOXES[box]['emoji']} {LOOTBOXES[box]['name']}!")


    @check(2)
    @buy.command(name="todo",extras={"category": Category.TODO}, usage="todo <item>")
    async def _todo(self, ctx, what:str):
        """Buy cool stuff for your todo list with this command! (Only in editor mode)"""
        try:
            editing[ctx.author.id]
        except KeyError:
            return await ctx.send(f'You have to be in the editor mode to use this command! Use `{self.client.command_prefix(self.client, ctx.message)[2]}todo edit <todo_list_id>`', allowed_mentions=discord.AllowedMentions.none())
        
        if not what.lower() in ['color', 'thumbnail', 'space', 'description']:
            return await ctx.send('You need to provide a valid thing you want to buy (color, thumbnail, space)')

        if what.lower() == 'color':
            return await self.buy_color(ctx)
        elif what.lower() == 'thumbnail':
            return await self.buy_thumbnail(ctx)
        elif what.lower() == 'space':
            return await self.buy_space(ctx)
        elif what.lower() == 'description':
            return await self.buy_description(ctx)


########################## Give commands ###################################

    @commands.group()
    async def give(self, ctx):
        if not ctx.invoked_subcommand:
            return await ctx.send("You need to provide a valid subcommand! Subcommands are: `card`, `lootbox` and `jenny`")

    async def _validate(self, ctx:commands.Context, other:discord.Member) -> Union[discord.Message, Tuple[User, User]]:
        """Validates if someone is a bot or the author and returns a tuple of users if correct, else a message"""
        if other == ctx.author:
            return await ctx.send('You can\'t give yourself anything!')
        if other.bot:
            return await ctx.send('🤖')

        return User(ctx.author.id), User(other.id)      

    @check()
    @give.command(extras={"category":Category.ECONOMY}, usage="jenny <user> <amount>")
    async def jenny(self, ctx, other:discord.Member, item:int):
        """If you're feeling generous give another user jenny"""
        
        if isinstance((val:=await self._validate(ctx, other)), discord.Message):
            return
        else:
            user, o = val

        if item < 1:
            return await ctx.send(f'You can\'t transfer less than 1 Jenny!')
        if user.jenny < item:
            return await ctx.send('You can\'t transfer more Jenny than you have')
        o.add_jenny(item)
        user.remove_jenny(item)
        return await ctx.send(f'✉️ transferred {item} Jenny to `{other}`!', allowed_mentions=discord.AllowedMentions.none())

    @check()
    @give.command(name="card", extras={"category":Category.CARDS}, usage="card <user> <card_id>")
    async def _card(self, ctx, other:discord.Member, item:int):
        """If you're feeling generous give another user a card"""

        if isinstance((val:=await self._validate(ctx, other)), discord.Message):
            return
        else:
            user, o = val

        try:
            Card(item)
        except CardNotFound:
            return await ctx.send('Invalid card number')
        if user.has_any_card(item, False) is False:
            return await ctx.send('You don\'t have any not fake copies of this card!')
        if (len(o.fs_cards) >= 40 and item < 100 and o.has_rs_card(item)) or (len(o.fs_cards) >= 40 and item > 99):
            return await ctx.send('The user you are trying to give the cards\'s free slots are full!')

        removed_card = user.remove_card(item)
        o.add_card(item, clone=removed_card[1]["clone"])
        return await ctx.send(f'✉️ gave `{other}` card No. {item}!', allowed_mentions=discord.AllowedMentions.none())

    @check()
    @give.command(name="lootbox", aliases=["box"], extras={"category":Category.ECONOMY}, usage="lootbox <user> <box_id>")
    async def _lootbox(self, ctx, other:discord.Member, item:int):
        """If you're feeling generous give another user a lootbox, maybe they have luck"""

        if isinstance((val:=await self._validate(ctx, other)), discord.Message):
            return
        else:
            user, o = val

        if item not in LOOTBOXES:
            return await ctx.send("Invalid lootbox. ")
        if item not in user.lootboxes:
            return await ctx.send("You don't own this lootbox!")
        user.remove_lootbox(item)
        o.add_lootbox(item)
        await ctx.send(f"✉️ gave {other.display_name} the box \"{LOOTBOXES[item]['name']}\"", allowed_mentions=discord.AllowedMentions.none())



Cog = Shop

def setup(client):
    client.add_cog(Shop(client))