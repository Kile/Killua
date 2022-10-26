import re
import discord
import logging
from random import randint, choice
from discord.ext import commands, tasks
from datetime import datetime
from typing import Union, Tuple, List

from killua.bot import BaseBot
from killua.static.cards import Card
from killua.static.constants import FREE_SLOTS, ALLOWED_AMOUNT_MULTIPLE, PRICES, LOOTBOXES, DB, editing
from killua.utils.classes import User, TodoList, CardNotFound, CardLimitReached
from killua.static.enums import Category, PrintColors, TodoAddons
from killua.utils.interactions import Button, ConfirmButton
from killua.utils.checks import check
from killua.utils.paginator import DefaultEmbed, Paginator
from killua.utils.interactions import Select, View

class ShopPaginator(Paginator):
    """A normal paginator with a button that returns to the original shop select menu"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.view.add_item(Button(label="Menu", style=discord.ButtonStyle.blurple, custom_id="menu"))

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

    def __init__(self, client: BaseBot):
        self.client = client

    def _format_offers(self, offers: list, reduced_item: int = None, reduced_by: int = None) -> list:
        """Formats the offers for the shop"""
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

    def _format_item(self, offer: int, reduced_item: int = None, reduced_by: int = None, number: int = None) -> dict:
        """Formats a single item for the shop"""
        item = DB.items.find_one({"_id": int(offer)})
        if reduced_item:
            if number == reduced_item:
                return {"name":f"**Number {item['_id']}: {item['name']}** |{item['emoji']}|", 'value': f"**Description:** {item['description']}\n**Price:** {PRICES[item['rank']]-int(PRICES[item['rank']]*(reduced_by/100))} (Reduced by **{reduced_by}%**) Jenny\n**Type:** {item['type'].replace('normal', 'item')}\n**Rarity:** {item['rank']}"}  
        
        return {"name":f"**Number {item['_id']}: {item['name']}** |{item['emoji']}|", "value": f"**Description:** {item['description']}\n**Price:** {PRICES[item['rank']]} Jenny\n**Type:** {item['type'].replace('normal', 'item')}\n**Rarity:** {item['rank']}"}


    async def cog_load(self):
        self.cards_shop_update.start()
    
    @tasks.loop(hours=6)
    async def cards_shop_update(self):
        # There have to be 4-5 shop items, inserted into the db as a list with the card numbers
        # the challenge is to create a balanced system with good items rare enough but not too rare
        try:
            shop_items:list = []
            number_of_items = randint(3,5) # How many items the shop has
            if randint(1,100) > 95:
                # Add a S/A card to the shop
                thing = [i["_id"] for i in DB.items.find({"type": "normal", "rank": {"$in": ["A", "S"], "available": True}})]
                shop_items.append(choice(thing))
            if randint(1,100) > 20: # 80% chance for spell
                if randint(1, 100) > 95: # 5% chance for a good spell (they are rare)
                    spells = [s["_id"] for s in DB.items.find({"type": "spell", "rank": "A", "available": True})]
                    shop_items.append(choice(spells))
                elif randint(1,10) > 5: # 50% chance of getting a medium good card
                    spells = [s["_id"] for s in DB.items.find({"type": "spell", "rank": {"$in": ["B", "C"]}, "available": True})]
                    shop_items.append(choice(spells))
                else: # otherwise getting a fairly normal card
                    spells = [s["_id"] for s in DB.items.find({"type": "spell", "rank": {"$in": ["D", "E", "F", "G"]}, "available": True})]
                    shop_items.append(choice(spells))

                while len(shop_items) != number_of_items: # Filling remaining spots
                    thing = [t["_id"] for t in DB.items.find({"type": "normal", "rank": {"$in": ["D", "B"]}, "available": True})] 
                    # There is just one D item so there is a really high probability of it being in the shop EVERY TIME
                    t = choice(thing)
                    if not t in shop_items:
                        shop_items.append(t)

                log = DB.shop.find_one({"_id": "daily_offers"})["log"]
                if randint(1, 10) > 6: # 40% to have an item in the shop reduced
                    reduced_item = randint(0, len(shop_items)-1)
                    reduced_by = randint(15, 40)
                    logging.info(f"{PrintColors.OKBLUE}Updated shop with following cards: " + ", ".join([str(x) for x in shop_items])+f", reduced item number {shop_items[reduced_item]} by {reduced_by}%{PrintColors.ENDC}")
                    log.append({"time": datetime.now(), "items": shop_items, "reduced": {"reduced_item": reduced_item, "reduced_by": reduced_by}})
                    DB.shop.update_many({"_id": "daily_offers"}, {"$set": {"offers": shop_items, "log": log, "reduced": {"reduced_item": reduced_item, "reduced_by": reduced_by}}})
                else:
                    logging.info(f"{PrintColors.OKBLUE}Updated shop with following cards: {', '.join([str(x) for x in shop_items])}{PrintColors.ENDC}")
                    log.append({"time": datetime.now(), "items": shop_items, "redued": None})
                    DB.shop.update_many({"_id": "daily_offers"}, {"$set": {"offers": shop_items, "log": log, "reduced": None}})
        except (IndexError, TypeError):
            logging.error(f"{PrintColors.WARNING}Shop could not be loaded, card data is missing{PrintColors.ENDC}")

    def _get_view(self, ctx) -> View:
        """Creates a view for the shop"""
        view = View(ctx.author.id)
        view.add_item(Button(label="Menu", style=discord.ButtonStyle.blurple, custom_id="menu"))
        return view

    async def _shop_menu(self, ctx, msg, view) -> None:
        """Handles the shop menu"""
        await view.wait()
        await view.disable(msg)
        if view.value:
            await msg.delete()
            if ctx.command.parent:
                await ctx.invoke(ctx.command.parent) #in case the menu was invoked by a subcommand
            else:
                await ctx.invoke(ctx.command) # in case the menu was invoked by the parent

    @commands.hybrid_group(aliases=["store"])
    async def shop(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            if ctx.command.parent:
                subcommands = [c for c in ctx.command.parent.commands]
            else:
                subcommands = [c for c in ctx.command.commands]

            view = View(ctx.author.id)
            view.add_item(Select(options=[discord.SelectOption(label=f"{c.name} shop", value=str(i)) for i, c in enumerate(subcommands)]))
            embed = discord.Embed.from_dict({
                "title": "Shop menu",
                "description": "Select the shop you want to visit",
                "image": {"url": "https://cdn.discordapp.com/attachments/795448739258040341/885927080410361876/image0.png"},
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
    async def cards_shop(self, ctx: commands.Context):
        """Shows the current cards for sale"""
        
        sh = DB.shop.find_one({"_id": "daily_offers"})
        shop_items:list = sh["offers"]

        if not sh["reduced"] is None:
            reduced_item = sh["reduced"]["reduced_item"]
            reduced_by = sh["reduced"]["reduced_by"]
            formatted = self._format_offers(shop_items, reduced_item, reduced_by)
            embed = discord.Embed(title="Current Card shop", description=f"**{DB.items.find_one({'_id': shop_items[reduced_item]})['name']} is reduced by {reduced_by}%**")
        else:
            formatted:list = self._format_offers(shop_items)
            embed = discord.Embed(title="Current Card shop")

        embed.color = 0x1400ff
        embed.set_thumbnail(url="https://static.wikia.nocookie.net/hunterxhunter/images/0/08/Spell_Card_Store.png/revision/latest?cb=20130328063032")
        for item in formatted:
            embed.add_field(name=item["name"], value=item["value"], inline=True)
        view = self._get_view(ctx)
        msg = await self.client.send_message(ctx, embed=embed, view=view)
        await self._shop_menu(ctx, msg, view)

    @check()
    @shop.command(name="todo", extras={"category": Category.TODO}, usage="todo")
    async def todo_shop(self, ctx: commands.Context):
        """Get some info about what cool stuff you can buy for your todo list with this command"""
        prefix = self.client.command_prefix(self.client, ctx.message)[2]
        embed = discord.Embed.from_dict({
            "title": "**The todo shop**",
            "description": f"""You can buy the following items with `{prefix}buy todo <item>` while you are in the edit menu for the todo list you want to buy the item for
            
**Cost**: 1000 Jenny
`color` change the color of the embed which displays your todo list!

**Cost**: 1000 Jenny
`thumbnail` add a neat thumbnail to your todo list (small image on the top right)

**Cost**: 1000 Jenny
`description` add a description to your todo list (recommended for public lists with custom id)

**Timed todos**: 2000 Jenny
`timed` add todos with deadline to your list and get notified when the deadline is reached

**Cost**: number of current spots * 50
`space` buy 10 more spots for todo"s for your list""",
            "color": 0x1400ff
        })
        view = self._get_view(ctx)
        msg = await self.client.send_message(ctx, embed=embed, view=view)
        await self._shop_menu(ctx, msg, view)

    @check()
    @shop.command(name="lootboxes", aliases=["boxes"], extras={"category": Category.ECONOMY}, usage="lootboxes")
    async def lootboxes_shop(self, ctx: commands.Context):
        """Get the current lootbox shop with this command"""
        prefix = self.client.command_prefix(self.client, ctx.message)[2]
        fields = [{"name": data["emoji"] + " " + data["name"] + " (id: " + str(id) + ")", "value": f"{data['description']}\nPrice: {data['price']}"} for id, data in LOOTBOXES.items() if data["available"]]

        def make_embed(page, embed, pages):
            embed.title = "Current lootbox shop"
            embed.description = f"To get infos about what a lootbox contains, use `{prefix}boxinfo <box_id>`\nTo buy a box, use `{prefix}buy lootbox <box_id>`"
            embed.clear_fields()
            if len(pages)-page*10+10 > 10:
                for x in pages[page*10-10:-(len(pages)-page*10)]:
                    embed.add_field(name=x["name"], value=x["value"], inline=True)
            elif len(pages)-page*10+10 <= 10:
                for x in pages[-(len(pages)-page*10+10):]:
                    embed.add_field(name=x["name"], value=x["value"], inline=True)

            return embed

        if len(fields) <= 10:
            embed = make_embed(1, DefaultEmbed(), fields)
            view = self._get_view(ctx)
            msg = await self.client.send_message(ctx, embed=embed, view=view)
            return await self._shop_menu(ctx, msg, view)

        await ShopPaginator(ctx, fields, func=make_embed).start() # currently only 10 boxes exist so this is not necessary, but supports more than 10 if ever necessary

################################################ Buy commands ################################################

    @commands.hybrid_group()
    async def buy(self, ctx):
        # have a shop for everything, you also need a buy for everything 
        if not ctx.invoked_subcommand:
            return await ctx.send("You need to provide a valid subcommand! Subcommands are: `card`, `lootbox` and `todo`")

    @check(2)
    @buy.command(extras={"category": Category.CARDS}, usage="card <card_id>")
    @discord.app_commands.describe(item="The card to buy")
    async def card(self, ctx: commands.Context, item: str):
        """Buy a card from the shop with this command"""
        
        shop_data = DB.shop.find_one({"_id": "daily_offers"})
        shop_items: list = shop_data["offers"]
        user = User(ctx.author.id)

        try:
            card = Card(item)
        except CardNotFound:
            return await ctx.send(f"This card is not for sale at the moment! Find what cards are in the shop with `{self.client.command_prefix(self.client, ctx.message)[2]}shop`", allowed_mentions=discord.AllowedMentions.none())

        if not item in shop_items:
            return await ctx.send(f"This card is not for sale at the moment! Find what cards are in the shop with `{self.client.command_prefix(self.client, ctx.message)[2]}shop`", allowed_mentions=discord.AllowedMentions.none())

        if not shop_data["reduced"] is None:
            if shop_items.index(card.id) == shop_data["reduced"]["reduced_item"]:
                price = int(PRICES[card.rank] - int(PRICES[card.rank] * (shop_data["reduced"]["reduced_by"]/100)))
            else:
                price = PRICES[card.rank]
        else:
            price = PRICES[card.rank]

        if len(card.owners) >= (card.limit * ALLOWED_AMOUNT_MULTIPLE):
            return await ctx.send("Unfortunately the global maximal limit of this card is reached! Someone needs to sell their card for you to buy one or trade/give it to you")

        if len(user.fs_cards) >= FREE_SLOTS:
            return await ctx.send(f"Looks like your free slots are filled! Get rid of some with `{self.client.command_prefix(self.client, ctx.message)[2]}sell`", allowed_mentions=discord.AllowedMentions.none())

        if user.jenny < price:
            return await ctx.send(f"I'm afraid you don't have enough Jenny to buy this card. Your balance is {user.jenny} while the card costs {price} Jenny")
        try:
            user.add_card(item)
        except Exception as e:
            if isinstance(e, CardLimitReached):
                return await ctx.send(f"Free slots card limit reached (`{FREE_SLOTS}`)! Get rid of one card in your free slots to add more cards with `{self.client.command_prefix(self.client, ctx.message)[2]}sell <card>`", allowed_mentions=discord.AllowedMentions.none())
            else:
                raise

        user.remove_jenny(price) #Always putting substracting points before giving the item so if the payment errors no item is given
        return await ctx.send(f"Successfully bought card number `{card.id}` {card.emoji} for {price} Jenny. Check it out in your inventory with `{self.client.command_prefix(self.client, ctx.message)[2]}book`!", allowed_mentions=discord.AllowedMentions.none())

    async def lootbox_autocomplete(
        self,
        _: discord.Interaction,
        current:str
    ) -> List[discord.app_commands.Choice[str]]:
        """A function to autocomplete the lootbox name"""
        options = []
        for lb in LOOTBOXES.values():
            if not lb["available"]: continue
            if current in lb["name"]:
                options.append(discord.app_commands.Choice(name=lb["name"], value=lb["name"]))
        return options

    @check(2)
    @buy.command(aliases=["box"], extras={"category": Category.ECONOMY}, usage="lootbox <item>")
    @discord.app_commands.describe(box="The lootbox to buy")
    @discord.app_commands.autocomplete(box=lootbox_autocomplete)
    async def lootbox(self, ctx: commands.Context, box: str):
        """Buy a lootbox with this command"""
        if not box.isdigit():
            box = self.client.get_lootbox_from_name(box)
            if not box:
                return await ctx.send("This lootbox is not for sale!")

        if not int(box) in LOOTBOXES or not LOOTBOXES[int(box)]["available"]:
            return await ctx.send("This lootbox is not for sale!")

        user = User(ctx.author.id)

        if user.jenny < (price:=LOOTBOXES[int(box)]["price"]):
            return await ctx.send(f"You don't have enough jenny to buy this box (You have: {user.jenny}, cost: {price})")

        user.remove_jenny(price)
        user.add_lootbox(int(box))
        return await ctx.send(f"Successfully bought lootbox {LOOTBOXES[int(box)]['emoji']} {LOOTBOXES[box]['name']}!")


    @check(2)
    @buy.command(name="todo",extras={"category": Category.TODO}, usage="todo <item>")
    @discord.app_commands.describe(what="The todo addon to buy")
    async def _todo(self, ctx: commands.Context, what: TodoAddons):
        """Buy cool stuff for your todo list with this command! (Only in editor mode)"""
        try:
            todo_list = TodoList(editing[ctx.author.id])
        except KeyError:
            return await ctx.send(f"You have to be in the editor mode to use this command! Use `{self.client.command_prefix(self.client, ctx.message)[2]}todo edit <todo_list_id>`", allowed_mentions=discord.AllowedMentions.none())

        user = User(ctx.author.id)

        if what.name == "space":
            if user.jenny < (todo_list.spots * 100 * 0.5):
                return await ctx.send(f"You don't have enough Jenny to buy more space for your todo list. You need {todo_list['spots']*100} Jenny")

            if todo_list.spots >= 100:
                return await ctx.send("You can't buy more than 100 spots")

            view = ConfirmButton(ctx.author.id, timeout=10)
            msg = await ctx.send(f"Do you want to buy 10 more to-do spots for this list? \nCurrent spots: {todo_list.spots} \nCost: {int(todo_list.spots*100*0.5)} points", view=view)
            await view.wait()
            await view.disable(msg)

            if not view.value:
                if view.timed_out:
                    return await ctx.send(f"Timed out")
                else:
                    return await ctx.send(f"Alright, see you later then :3")

            user.remove_jenny(int(100*todo_list.spots*0.5))
            todo_list.add_spots(10)
            return await ctx.send("Congrats! You just bought 10 more todo spots for the current todo list!")
        elif what.name == "timing":
            if todo_list.has_addon("due_in"):
                return await ctx.send("You already have this addon!")
            if user.jenny < 2000:
                return await ctx.send(f"You don't have enough Jenny to buy this item. You need 2000 Jenny while you currently have {user.jenny}")
            user.remove_jenny(2000)
            todo_list.enable_addon("due_in")
            return await ctx.send("Congrats! You just bought the timing addon for the current todo list! You can now specifiy the `due_in` parameter when adding a todo.")
        else:
            if todo_list.has_addon(what.name):
                return await ctx.send("You already have this addon!")
            if user.jenny < 1000:
                return await ctx.send(f"You don't have enough Jenny to buy this item. You need 1000 Jenny while you currently have {user.jenny}")
            user.remove_jenny(1000)
            todo_list.enable_addon(what.name)
            return await ctx.send(f"Successfully bought {what.name} for 1000 Jenny! Customize it with `{self.client.command_prefix(self.client, ctx.message)[2]}todo update {what.name}`")


################################################ Give commands ################################################

    @commands.hybrid_group()
    async def give(self, ctx: commands.Context):
        if not ctx.invoked_subcommand:
            return await ctx.send("You need to provide a valid subcommand! Subcommands are: `card`, `lootbox` and `jenny`")

    async def _validate(self, ctx: commands.Context, other: discord.Member) -> Union[discord.Message, Tuple[User, User]]:
        """Validates if someone is a bot or the author and returns a tuple of users if correct, else a message"""
        if other == ctx.author:
            return await ctx.send("You can't give yourself anything!")
        if other.bot:
            return await ctx.send("🤖")

        return User(ctx.author.id), User(other.id)      

    @check()
    @give.command(extras={"category":Category.ECONOMY}, usage="jenny <user> <amount>")
    @discord.app_commands.describe(
        other="The user to give jenny to",
        amount="The amount of jenny to give"
    ) 
    async def jenny(self, ctx: commands.Context, other: discord.Member, amount: int):
        """If you"re feeling generous give another user jenny"""
        
        if isinstance((val:=await self._validate(ctx, other)), discord.Message):
            return
        else:
            user, o = val

        if amount < 1:
            return await ctx.send(f"You can't transfer less than 1 Jenny!")
        if user.jenny < amount:
            return await ctx.send("You can't transfer more Jenny than you have")
        o.add_jenny(amount)
        user.remove_jenny(amount)
        return await ctx.send(f"✉️ transferred {amount} Jenny to `{other}`!", allowed_mentions=discord.AllowedMentions.none())

    async def all_cards_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[discord.app_commands.Choice[str]]:
        """Autocomplete for all cards"""
        if not self.cardname_cache:
            for card in DB.items.find({}):
                self.cardname_cache[card["_id"]] = card["name"], card["type"]

        name_cards = [(x[0], self.cardname_cache[x[0]][0]) for x in User(interaction.user.id).all_cards if self.cardname_cache[x[0]][0].lower().startswith(current.lower())]
        id_cards = [(x[0], self.cardname_cache[x[0]][0]) for x in User(interaction.user.id).all_cards if str(x[0]).startswith(current)]
        name_cards = list(dict.fromkeys(name_cards)) 
        id_cards = list(dict.fromkeys(id_cards)) # removing all duplicates from the list

        if current == "": # No ids AND names if the user hasn"t typed anything yet
            return [discord.app_commands.Choice(name=x[1], value=str(x[0])) for x in name_cards]
        return [*[discord.app_commands.Choice(name=n, value=str(i)) for i, n in name_cards], *[discord.app_commands.Choice(name=str(i), value=str(i)) for i, _ in id_cards]]

    @check()
    @give.command(name="card", extras={"category":Category.CARDS}, usage="card <user> <card_id>")
    @discord.app_commands.describe(
        other="The user to give the card to",
        card="What card to give"
    )
    @discord.app_commands.autocomplete(card=all_cards_autocomplete)
    async def _card(self, ctx: commands.Context, other: discord.Member, card: str):
        """If you"re feeling generous give another user a card"""

        if isinstance((val:=await self._validate(ctx, other)), discord.Message):
            return
        else:
            user, o = val

        try:
            item = Card(card).id
        except CardNotFound:
            return await ctx.send("Invalid card number")
        if user.has_any_card(item, False) is False:
            return await ctx.send("You don't have any not fake copies of this card!")
        if (len(o.fs_cards) >= 40 and item < 100 and o.has_rs_card(item)) or (len(o.fs_cards) >= 40 and item > 99):
            return await ctx.send("The user you are trying to give the cards's free slots are full!")

        removed_card = user.remove_card(item)
        o.add_card(item, clone=removed_card[1]["clone"])
        return await ctx.send(f"✉️ gave `{other}` card No. {item}!", allowed_mentions=discord.AllowedMentions.none())

    @check()
    @give.command(name="lootbox", aliases=["box"], extras={"category":Category.ECONOMY}, usage="lootbox <user> <box_id>")
    @discord.app_commands.describe(
        other="The user to give the lootbox to",
        box="What lootbox to give"
    )
    async def _lootbox(self, ctx: commands.Context, other: discord.Member, box: str):
        """If you"re feeling generous give another user a lootbox, maybe they have luck"""

        if isinstance((val:=await self._validate(ctx, other)), discord.Message):
            return
        else:
            user, o = val

        if box.isdigit() and int(box) not in LOOTBOXES:
            box = self.client.get_lootbox_from_name(box)
            if not box:
                return await ctx.send("Invalid lootbox. ")

        if int(box) not in user.lootboxes:
            return await ctx.send("You don't own this lootbox!")
        user.remove_lootbox(int(box))
        o.add_lootbox(int(box))
        await ctx.send(f"✉️ gave {other.display_name} the box '{LOOTBOXES[int(box)]['name']}'", allowed_mentions=discord.AllowedMentions.none())



Cog = Shop