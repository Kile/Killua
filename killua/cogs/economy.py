import discord
from discord.ext import commands
from typing import Union, List, Tuple
from datetime import datetime, timedelta
from random import randint

from killua.utils.checks import check
from killua.utils.interactions import View
from killua.utils.interactions import Select
from killua.utils.classes import User, Guild, LootBox
from killua.static.enums import Category
from killua.static.constants import USER_FLAGS, KILLUA_BADGES, GUILD_BADGES, teams, LOOTBOXES, PREMIUM_ALIASES

class Economy(commands.Cog):

    def __init__(self, client):
        self.client = client
        self._init_menus()

    def _init_menus(self) -> None:
        menus = []
        menus.append(discord.app_commands.ContextMenu(
            name='profile',
            callback=self.client.callback_from_command(self.profile, message=False),
            # guild_ids=[...],
        ))
        menus.append(discord.app_commands.ContextMenu(
            name='balance',
            callback=self.client.callback_from_command(self.jenny, message=False),
        ))

        for menu in menus:
            self.client.tree.add_command(menu)


    async def _get_user(self, user_id: int) -> Union[discord.User, None]:
        u = self.client.get_user(user_id)
        if not u:
            u = await self.client.fetch_user(user_id)
        return u

    def _fieldify_lootboxes(self, lootboxes: List[int]):
        """Creates a list of fields from the lootboxes in the passed list"""
        lbs: List[Tuple[int, int]] = [] # A list containing the a tuple with the amount and id of the lootboxes owned
        res: List[dict] = [] # The fields to be returned

        for lb in lootboxes:
            if not lb in (l:= [y for _, y in lbs]):
                lbs.append((1, lb))
            else:
                indx = l.index(lb)
                lbs[indx] = (lbs[indx][0]+1, lb)
                
        for lb in lbs:
            n, i = lb
            data = LOOTBOXES[i]
            res.append({"name": f"{n}x {data['emoji']} {data['name']} (id:{i})", "value": data["description"], "inline": False})

        return res
         
    def _getmember(self, user: Union[discord.Member, discord.User]) -> discord.Embed:
        """A function to handle getting infos about a user for less messy code """
        joined = self.client.convert_to_timestamp(user.id)
        
        info = User(user.id)
        flags = [USER_FLAGS[x[0]] for x in user.public_flags if x[1]]
        if (user.avatar and user.avatar.is_animated()) or len([x for x in self.client.guilds if user.id in [y.id for y in x.premium_subscribers]]) > 0: # A very simple nitro check that is not too accurate
            flags.append(USER_FLAGS["nitro"])
        badges = [(KILLUA_BADGES[PREMIUM_ALIASES[x]] if x in PREMIUM_ALIASES.keys() else KILLUA_BADGES[x]) for x in info.badges]
        
        if str(datetime.now()) > str(info.daily_cooldown):
            cooldown = "Ready to claim!"
        else:
            cooldown = f"<t:{int(info.daily_cooldown.timestamp())}:R>"

        return discord.Embed.from_dict({
                "title": f"Information about {user}",
                "description": f"{user.id}\n{' '.join(flags)}",
                "fields": [{"name": "Killua Badges", "value": " ".join(badges) if len(badges) > 0 else "No badges", "inline": False}, {"name": "Jenny", "value": str(info.jenny), "inline": False}, {"name": "Account created at", "value": joined, "inline": False}, {"name": "daily cooldown", "value": cooldown or "Never claimed `k!daily` before", "inline": False}],
                "thumbnail": {"url": str(user.avatar.url) if user.avatar else None},
                "image": {"url": user.banner.url if user.banner else None},
                "color": 0x1400ff
            })

    def _lb(self, ctx: commands.Context, limit: int = 10) -> dict:
        """Creates a list of the top members regarding jenny in a server"""
        members = teams.find({"id": {"$in": [x.id for x in ctx.guild.members]} })
        top = sorted(members, key=lambda x: x["points"], reverse=True) # Bringing it in a nice lederboard order
        points = 0
        for m in top:
            points += m["points"] # Working out total points in the server

        return {
            "points": points,
            "top": [{"name": ctx.guild.get_member(x["id"]), "points": x["points"]} for x in top][:(limit or len(top))]
        }

    async def lootbox_autocomplete(
        self,
        _: discord.Interaction,
        current:str
    ) -> List[discord.app_commands.Choice[str]]:
        """A function to autocomplete the lootbox name"""
        options = []
        for lb in LOOTBOXES:
            if current in lb["name"]:
                options.append(discord.app_commands.Choice(lb["name"], lb["id"]))
        return options

    @commands.hybrid_group()
    async def economy(self, _: commands.Context):
        """' commands resolving around jenny, lootboxes and the general economy"""
        ...

    @check()
    @commands.guild_only()
    @economy.command(aliases=["server"], extras={"category":Category.ECONOMY}, usage="guild")
    async def guild(self, ctx: commands.Context):
        """Displays infos about the current guild"""
        top = self._lb(ctx, limit=1)
        guild = Guild(ctx.guild.id)
        badges = " ".join([GUILD_BADGES[b] for b in guild.badges])

        embed = discord.Embed.from_dict({
            "title": f"Information about {ctx.guild.name}",
            "fields": [
                {"name": "Owner", "value": str(ctx.guild.owner)},
                {"name": "Killua Badges", "value": (badges if len(badges) > 0 else "No badges")},
                {"name": "Combined Jenny", "value": top["points"]},
                {"name": "Richest Member", "value": f"{top['top'][0]['name']} with {top['top'][0]['points']} jenny"},
                {"name": "Server created at", "value": self.client.convert_to_timestamp(ctx.guild.id)},
                {"name": "Members", "value": ctx.guild.member_count}
            ],
            "description": str(ctx.guild.id),
            "thumbnail": {"url": str(ctx.guild.icon.url)},
            "color": 0x1400ff
        })
        await self.client.send_message(ctx, embed=embed)

    @check()
    @commands.guild_only()
    @economy.command(aliases=["lb", "top"], extras={"category":Category.ECONOMY}, usage="leaderboard")
    async def leaderboard(self, ctx: commands.Context):
        """Get a leaderboard of members with the most jenny"""
        top = self._lb(ctx)
        if top["points"] == 0:
            return await ctx.send(f"Nobody here has any jenny! Be the first to claim some with `{self.client.command_prefix(self.client, ctx.message)[2]}daily`!", allowed_mentions=discord.AllowedMentions.none())
        embed = discord.Embed.from_dict({
            "title": f"Top users on guild {ctx.guild.name}",
            "description": "\n".join([f"#{p+1} `{x['name']}` with `{x['points']}` jenny" for p, x in enumerate(top["top"])]),
            "color": 0x1400ff,
            "thumbnail": {"url": str(ctx.guild.icon.url)}
        })
        await self.client.send_message(ctx, embed=embed)

    @check()
    @economy.command(aliases=["whois", "p", "user"], extras={"category":Category.ECONOMY}, usage="profile <user(optional)>")
    @discord.app_commands.describe(user="The user to get infos about")
    async def profile(self, ctx, user: str = None):
        """Get infos about a certain discord user with ID or mention"""
        if user is None:
            res = ctx.author
        else:
            res = await self.client.find_user(ctx, user)

            if not res:
                return await ctx.send(f"Could not find user `{user}`", allowed_mentions=discord.AllowedMentions.none(), ephemeral=True)

        embed = self._getmember(res)
        return await self.client.send_message(ctx, embed=embed, ephemeral=hasattr(ctx, "invoked_by_modal"))

    @check()
    @economy.command(aliases=["bal", "balance", "points"], extras={"category":Category.ECONOMY}, usage="balance <user(optional)>")
    @discord.app_commands.describe(user="The user to see the number of jenny of")
    async def jenny(self, ctx: commands.Context, user: str = None):
        """Gives you a users balance"""
        
        if not user:
            res = ctx.author
        else:
            res = await self.client.find_user(ctx, user)

            if not res:
                return await ctx.send("User not found", ephemeral=True)

        balance = User(res.id).jenny
        return await ctx.send(f"{res}'s balance is {balance} Jenny", aphemeral=hasattr(ctx, "invoked_by_modal"))
        
    @check()
    @economy.command(extras={"category":Category.ECONOMY}, usage="daily")
    async def daily(self, ctx: commands.Context):
        """Claim your daily Jenny with this command!"""
        now = datetime.now()
        user = User(ctx.author.id)

        if str(user.daily_cooldown) > str(now): # When the cooldown is still active
            return await ctx.send(f"You can claim your daily Jenny the next time in <t:{int(user.daily_cooldown.timestamp())}:R>")

        min, max = 50, 100
        if user.is_premium:
            min, max = min*2, max*2 # Sadly `min, max *= 2` does not work, this is the only way to fit it in one line
        if ctx.guild and Guild(ctx.guild.id).is_premium:
            min, max = min*2, max*2
        daily = randint(min, max)
        if user.is_entitled_to_double_jenny:
            daily *= 2

        user.claim_daily()
        user.add_jenny(daily)
        await ctx.send(f"You claimed your {daily} daily Jenny and hold now on to {user.jenny}")

    @check()
    @economy.command(extras={"category": Category.ECONOMY}, usage="open")
    async def open(self, ctx: commands.Context):
        """Open a lootbox with an interactive UI"""
        if len((user:=User(ctx.author.id)).lootboxes) == 0:
            return await ctx.send("Sadly you don't have any lootboxes!")

        lootboxes = self._fieldify_lootboxes(user.lootboxes)
        embed = discord.Embed.from_dict({
            "title": "Choose a lootbox to open!",
            "fields": lootboxes,
            "color": 0x1400ff
        })
        lbs = []
        for l in user.lootboxes:
            if l not in lbs:
                lbs.append(l)

        view = View(ctx.author.id)
        select = Select(options=[discord.SelectOption(label=LOOTBOXES[lb]["name"], emoji=LOOTBOXES[lb]["emoji"], value=str(lb), description=d if len((d:=LOOTBOXES[lb]["description"])) < 47 else d[:47] + "...") for lb in lbs], placeholder="Select a box to open")
        view.add_item(item=select)

        msg = await ctx.send(embed=embed, view=view)
        await view.wait()

        await view.disable(msg)
        if view.timed_out:
            await ctx.send("Timed out!", ephemeral=True)

        user.remove_lootbox(view.value)
        values = LootBox.generate_rewards(view.value)
        box = LootBox(ctx, values)
        return await box.open()

    @check()
    @economy.command(aliases=["lootboxes", "inv"], extras={"category": Category.ECONOMY}, usage="inventory")
    async def inventory(self, ctx: commands.Context):
        """Displays the owned lootboxes"""
        if len((user:=User(ctx.author.id)).lootboxes) == 0:
            return await ctx.send("Sadly you don't have any lootboxes!")

        lootboxes = self._fieldify_lootboxes(user.lootboxes)
        embed = discord.Embed.from_dict({
            "title": "Lootbox inventory",
            "description": f"open a lootbox with `{self.client.command_prefix(self.client, ctx.message)[2]}open`",
            "color": 0x1400ff,
            "fields": lootboxes
        })
        embed.timestamp = datetime.now()
        await ctx.send(embed=embed)

    @check()
    @economy.command(extras={"category": Category.ECONOMY}, usage="boxinfo <box_id>")
    @discord.app_commands.autocomplete(box=lootbox_autocomplete)
    @discord.app_commands.describe(box="The box to get infos about")
    async def boxinfo(self, ctx: commands.Context, box: str):
        """Get infos about any box you desire"""
        if box.isdigit() and not int(box) in LOOTBOXES.keys():
            box = self.client.get_lootbox_from_name(box)
            if not box:
                return await ctx.send("Invalid box name or id", ephemeral=True)

        data = LOOTBOXES[int(box)]

        c_min, c_max = data["cards_total"]
        j_min, j_max = data["rewards"]["jenny"]
        contains = f"{data['rewards_total']} total rewards\n{f'{c_min}-{c_max}' if c_max != c_min else c_min} cards\n{j_min}-{j_max} jenny per field\n" + ('' if c_max == 0 else f"card rarities: {' or '.join(data['rewards']['cards']['rarities'])}\ncard types: {' or '.join(data['rewards']['cards']['types'])}")
        embed = discord.Embed.from_dict({
            "title": f"Infos about lootbox {data['emoji']} {data['name']}",
            "description": data["description"],
            "fields": [
                {"name": "Contains", "value": contains, "inline": False},
                {"name": "Price", "value": data["price"], "inline": False},
                {"name": "Buyable", "value": "Yes" if data["available"] else "No"},
            ],
            "color": 0x1400ff,
            "image": {"url": data["image"]}
        })
        await ctx.send(embed=embed)


Cog = Economy

async def setup(client):
  await client.add_cog(Economy(client))

