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

    async def _get_user(self, user_id:int) -> Union[discord.User, None]:
        u = self.client.get_user(user_id)
        if not u:
            u = await self.client.fetch_user(user_id)
        return u

    def _fieldify_lootboxes(self, lootboxes:List[int]):
        """Creates a list of fields from the lootboxes in the passed list"""
        lbs:List[Tuple[int, int]] = []
        res: List[dict] = []

        for lb in lootboxes:
            if not lb in (l:= [y for x, y in lbs]):
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
        """ a function to handle getting infos about a user for less messy code """
        joined = self.client.convert_to_timestamp(user.id)
        
        info = User(user.id)
        flags = [USER_FLAGS[x[0]] for x in user.public_flags if x[1]]
        if (user.avatar and user.avatar.is_animated()) or len([x for x in self.client.guilds if user.id in [y.id for y in x.premium_subscribers]]) > 0: # A very simple nitro check that is not too accurate
            flags.append(USER_FLAGS["nitro"])
        badges = [(KILLUA_BADGES[PREMIUM_ALIASES[x]] if x in PREMIUM_ALIASES.keys() else KILLUA_BADGES[x]) for x in info.badges]
        
        if str(datetime.utcnow()) > str(info.daily_cooldown):
            cooldown = 'Ready to claim!'
        else:
            cooldown = f"<t:{int(info.daily_cooldown.timestamp())}:R>"

        embed = discord.Embed.from_dict({
                'title': f'Information about {user}',
                'description': f'{user.id}\n{" ".join(flags)}',
                "fields": [{"name": "Killua Badges", "value": " ".join(badges) if len(badges) > 0 else "No badges", "inline": False}, {"name": "Jenny", "value": str(info.jenny), "inline": False}, {"name": "Account created at", "value": joined, "inline": False}, {"name": "daily cooldown", "value": cooldown or "Never claimed `k!daily` before", "inline": False}],
                'thumbnail': {'url': str(user.avatar.url) if user.avatar else None},
                "image": {"url": user.banner.url if user.banner else None},
                'color': 0x1400ff
            })
        return embed

    def _lb(self, ctx, limit=10):
        """Creates a list of the top members regarding jenny in a server"""
        members = teams.find({'id': {'$in': [x.id for x in ctx.guild.members]} })
        top = sorted(members, key=lambda x: x['points'], reverse=True)
        points = 0
        for m in top:
            points = points + m['points']
        data = {
            "points": points,
            "top": [{"name": ctx.guild.get_member(x['id']), "points": x["points"]} for x in top][:(limit or len(top))]
        }
        return data

    @check()
    @commands.guild_only()
    @commands.command(aliases=['server'], extras={"category":Category.ECONOMY}, usage="guild")
    async def guild(self, ctx):
        """Displays infos about the current guild"""
        top = self._lb(ctx, limit=1)
        guild = Guild(ctx.guild.id)
        badges = ' '.join([GUILD_BADGES[b] for b in guild.badges])

        embed = discord.Embed.from_dict({
            "title": f"Information about {ctx.guild.name}",
            "fields": [
                {"name": "Owner", "value": str(ctx.guild.owner)},
                {"name": "Killua Badges", "value": (badges if len(badges) > 0 else "No badges")},
                {"name": "Combined Jenny", "value": top["points"]},
                {"name": "Richest Member", "value": f'{top["top"][0]["name"]} with {top["top"][0]["points"]} jenny'},
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
    @commands.command(aliases=['lb', 'top'], extras={"category":Category.ECONOMY}, usage="leaderboard")
    async def leaderboard(self, ctx):
        """Get a leaderboard of members with the most jenny"""
        top = self._lb(ctx)
        if len(top) == 0:
            return await ctx.send(f"Nobody here has any jenny! Be the first to claim some with `{self.client.command_prefix(self.client, ctx.message)[2]}daily`!", allowed_mentions=discord.AllowedMentions.none())
        embed = discord.Embed.from_dict({
            "title": f"Top users on guild {ctx.guild.name}",
            "description": '\n'.join([f'#{p+1} `{x["name"]}` with `{x["points"]}` jenny' for p, x in enumerate(top["top"])]),
            "color": 0x1400ff,
            "thumbnail": {"url": str(ctx.guild.icon.url)}
        })
        await self.client.send_message(ctx, embed=embed)

    @check()
    @commands.command(aliases=["whois", "p", "user"], extras={"category":Category.ECONOMY}, usage="profile <user(optional)>")
    async def profile(self, ctx, user: Union[discord.Member, int]=None):
        """Get infos about a certain discord user with ID or mention"""
        if user is None:
            res = ctx.author
        elif isinstance(user, discord.Member):
            res = user
        else:
            res = self.client.get_user(user)
            if not res:
                try:
                    res = await self.client.fetch_user(user)
                except discord.NotFound:
                    return await ctx.send("Could not find anyone with this name/id")

        embed = self._getmember(res)
        return await self.client.send_message(ctx, embed=embed)

    @check()
    @commands.command(aliases=['bal', 'balance', 'points'], extras={"category":Category.ECONOMY}, usage="balance <user(optional)>")
    async def jenny(self, ctx, user: Union[discord.User, int]=None):
        """Gives you a users balance"""
        
        if not user:
            user_id = ctx.author.id
        if isinstance(user, discord.User):
            user_id = user.id
        elif user:
            user_id = user
        try:
            self.client.get_user(user_id) or await self.client.fetch_user(user_id)
            real_user = User(user_id)
        except discord.NotFound:
            return await ctx.send('User not found')

        return await ctx.send(f'{user or ctx.author}\'s balance is {real_user.jenny} Jenny')
        
    @check()
    @commands.command(extras={"category":Category.ECONOMY}, usage="daily")
    async def daily(self, ctx):
        """Claim your daily Jenny with this command!"""
        now = datetime.utcnow()
        user = User(ctx.author.id)
        min = 50
        max = 100
        if user.is_premium:
            min*=2
            max*=2
        if ctx.guild and Guild(ctx.guild.id).is_premium:
            min*=2
            max*=2
        daily = randint(min, max)
        if user.is_entitled_to_double_jenny:
            daily *= 2
        if str(user.daily_cooldown) < str(now):
            user.claim_daily()
            user.add_jenny(daily)
            await ctx.send(f'You claimed your {daily} daily Jenny and hold now on to {user.jenny}')
        else:
            cooldown = f"<t:{int(user.daily_cooldown.timestamp())}:R>"
            await ctx.send(f'You can claim your daily Jenny the next time in {cooldown}')

    @check()
    @commands.command(extras={"category": Category.ECONOMY}, usage="open")
    async def open(self, ctx):
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

        if hasattr(view, "value"):
            user.remove_lootbox(view.value)
            values = LootBox.generate_rewards(view.value)
            box = LootBox(ctx, values)
            return await box.open()

        await ctx.send("Timed out!")

    @check()
    @commands.command(aliases=["lootboxes", "inv"], extras={"category": Category.ECONOMY}, usage="inventory")
    async def inventory(self, ctx):
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
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)

    @check()
    @commands.command(extras={"category": Category.ECONOMY}, usage="boxinfo <box_id>")
    async def boxinfo(self, ctx, box:int):
        """Get infos about any box you desire"""
        if not box in LOOTBOXES.keys():
            return await ctx.send("Invalid box id")

        data = LOOTBOXES[box]

        c_min, c_max = data["cards_total"]
        j_min, j_max = data["rewards"]["jenny"]
        contains = f"{data['rewards_total']} total rewards\n{f'{c_min}-{c_max}' if c_max != c_min else c_min} cards\n{j_min}-{j_max} jenny per field\n" + ("" if c_max == 0 else f"card rarities: {' or '.join(data['rewards']['cards']['rarities'])}\ncard types: {' or '.join(data['rewards']['cards']['types'])}")
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

def setup(client):
  client.add_cog(Economy(client))

