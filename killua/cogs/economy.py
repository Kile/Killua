import discord
from discord.ext import commands
from killua.functions import check
import typing
from datetime import datetime, timedelta
from random import randint
from killua.classes import User, Guild
from killua.constants import USER_FLAGS, KILLUA_BADGES, teams, guilds

class Economy(commands.Cog):

    def __init__(self, client):
        self.client = client

    def _getmember(self, user: discord.Member):
        """ Input: 
            user (discord.User): the user to get info about and return it

            Returns:
            embed: An embed with the users information

            Purpose:
            To have a function handle getting infos about a user for less messy code
        """
        av = user.avatar_url
        joined = (user.created_at).strftime("%b %d %Y %H:%M:%S")
        
        info = User(user.id)

        flags = [USER_FLAGS[x[0]] for x in user.public_flags if x[1]]
        badges = [KILLUA_BADGES[x] for x in info.badges]
        bal = info.jenny
        
        if str(datetime.now()) > str(info.daily_cooldown):
            cooldown = 'Ready to claim!'
        else:
            cd = info.daily_cooldown - datetime.now()
            cooldown = f'{int((cd.seconds/60)/60)} hours, {int(cd.seconds/60)-(int((cd.seconds/60)/60)*60)} minutes and {int(cd.seconds)-(int(cd.seconds/60)*60)} seconds'

        embed = discord.Embed.from_dict({
                'title': f'Information about {user}',
                'description': f'{user.id}\n{" ".join(flags)}\n\n**Killua Badges**\n{" ".join(badges) if len(badges) > 0 else "No badges"}\n\n**Jenny**\n{bal}\n\n**Account created at**\n{joined}\n\n**`k!daily` cooldown**\n{cooldown or "Never claimed `k!daily` before"}',
                'thumbnail': {'url': str(av)},
                'color': 0x1400ff
            })
        return embed

    def _lb(self, ctx, limit=10):
        members = teams.find({'id': {'$in': [x.id for x in ctx.guild.members]} })
        top = sorted(members, key=lambda x: x['points'], reverse=True)
        points = 0
        for m in top:
            points = points + m['points']
        data = {
            "points": points,
            "top": [{"name": ctx.guild.get_member(x['id']), "points": x["points"]} for x in top][:limit]
        }
        return data

    @check()
    @commands.command(aliases=['server'])
    async def guild(self, ctx):
        #h Displays infos about the current guild
        #u guild
        top = self._lb(ctx, limit=1)

        guild = guilds.find_one({'id': ctx.guild.id})
        if not guild is None:
            badges = '\n'.join(guild['badges'])

        embed = discord.Embed.from_dict({
            'title': f'Information about {ctx.guild.name}',
            'description': f'{ctx.guild.id}\n\n**Owner**\n{ctx.guild.owner}\n\n**Killua Badges**\n{badges or "No badges"}\n\n**Combined Jenny**\n{top["points"]}\n\n**Richest member**\n{top["top"][0]["name"]} with {top["top"][0]["points"]} jenny\n\n**Server created at**\n{(ctx.guild.created_at).strftime("%b %d %Y %H:%M:%S")}\n\n**Members**\n{ctx.guild.member_count}',
            'thumbnail': {'url': str(ctx.guild.icon_url)},
            'color': 0x1400ff
        })
        await ctx.send(embed=embed)

    @check()
    @commands.command(aliases=['lb', 'top'])
    async def leaderboard(self, ctx):
        #h Get a leaderboard of members with the most jenny
        #u leaderboard
        top = self._lb(ctx)
        if len(top) == 0:
            return await ctx.send(f"Nobody here has any jenny! Be the first to claim some with `{self.client.command_prefix(self.client, ctx.message)[2]}daily`!")
        embed = discord.Embed.from_dict({
            "title": f"Top users on guild {ctx.guild.name}",
            "description": '\n'.join([f'#{p+1} `{x["name"]}` with `{x["points"]}` jenny' for p, x in enumerate(top["top"])]),
            "color": 0x1400ff,
            "thumbnail": {"url": str(ctx.guild.icon_url)}
        })
        await ctx.send(embed=embed)

    @check()
    @commands.command()
    async def profile(self, ctx,user: typing.Union[discord.Member, int]=None):
        #h Get infos about a certain discord user with ID or mention
        #u profile <user(optional)>
        if user is None:
            embed = self._getmember(ctx.author)
            return await ctx.send(embed=embed)
        else: 
            if isinstance(user, discord.Member):
                embed = self._getmember(user)
                return await ctx.send(embed=embed)
            else:
                try:
                    newuser = await self.client.fetch_user(user)
                    embed = self._getmember(newuser)
                    return await ctx.send(embed=embed)
                except Exception as e:
                    await ctx.send(f'```diff\n-{e}\n```')

    @check()
    @commands.command(aliases=['bal', 'balance', 'points'])
    async def jenny(self, ctx, user: typing.Union[discord.User, int]=None):
        #h Gives you a users balance
        #u balance <user(optional)>
        
        if not user:
            user_id = ctx.author.id
        if isinstance(user, discord.User):
            user_id = user.id
        elif user:
            user_id = user
        try:
            await self.client.fetch_user(user_id)
            real_user = User(user_id)
        except discord.NotFound:
            return await ctx.send('User not found')

        return await ctx.send(f'{user or ctx.author}\'s balance is {real_user.jenny} Jenny')
        
    @check()
    @commands.command()
    async def daily(self, ctx):
        #h Claim your daily points with this command!
        #u daily
        now = datetime.today()
        later = datetime.now()+timedelta(hours=24)
        user = User(ctx.author.id)
        min = 50
        max = 100
        if user.is_premium:
            min = min+ 50
            max = max+50
        if Guild(ctx.guild.id).is_premium:
            min = min+ 50
            max = max+50
        daily = randint(min, max)
        if str(user.daily_cooldown) < str(now):
            teams.update_one({'id': ctx.author.id},{'$set':{'cooldowndaily': later,'points': user.jenny + daily}})
            await ctx.send(f'You claimed your {daily} daily Jenny and hold now on to {int(user.jenny) + int(daily)}')
        else:
            cd = user.daily_cooldown-datetime.now()
            cooldown = f'{int((cd.seconds/60)/60)} hours, {int(cd.seconds/60)-(int((cd.seconds/60)/60)*60)} minutes and {int(cd.seconds)-(int(cd.seconds/60)*60)} seconds'
            await ctx.send(f'You can claim your daily Jenny the next time in {cooldown}')

Cog = Economy

def setup(client):
  client.add_cog(Economy(client))

