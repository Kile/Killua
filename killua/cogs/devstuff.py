from discord.ext import commands
import discord
from datetime import datetime, timedelta
import re

from killua.utils.checks import check
from killua.utils.classes import User, Category #lgtm [py/unused-import]
from killua.static.cards import Card #lgtm [py/unused-import]
from killua.static.constants import teams, guilds, blacklist, presence as pr, items, updates, UPDATE_CHANNEL #lgtm [py/unused-import]

class DevStuff(commands.Cog):

    def __init__(self, client):
        self.client = client

    #Eval command, unnecessary with the jsk extension but useful for database stuff
    @commands.is_owner()
    @commands.command(aliases=['exec'], extras={"category":Category.OTHER}, usage="eval <code>", hidden=True)
    async def eval(self, ctx, *, code):
        """Standart eval command, owner restricted"""
        try:
            await ctx.channel.send(f'```py\n{eval(code)}```')
        except Exception as e:
            await ctx.channel.send(str(e))

    @commands.is_owner()
    @commands.command(aliases=["publish-update", "pu"], extras={"category":Category.OTHER}, usage="publish_update <version> <text>", hidden=True)
    async def publish_update(self, ctx, version:str, *, update):
        """Allows me to publish Killua updates in a handy formart"""

        old = updates.find_one({'_id':'current'})
        old_version = old["version"] if "version" in old else "No version"

        if version in [*[old_version],*[x["version"] for x in updates.find_one({"_id": "log"})["past_updates"]]]:
            return await ctx.send("This is an already existing version")

        embed = discord.Embed.from_dict({
            'title': f'Killua Update `{old_version}` -> `{version}`',
            'description': update,
            'color': 0x1400ff,
            'footer': {'text': f'Update by {ctx.author}', 'icon_url': str(ctx.author.avatar.url)},
            'image': {'url': 'https://cdn.discordapp.com/attachments/780554158154448916/788071254917120060/killua-banner-update.png'}
        })

        data = {'version': version, 'description': update, 'published_on': datetime.utcnow(), 'published_by': ctx.author.id}
        updates.update_one({'_id': 'current'}, {'$set': data})
        updates.update_one({'_id': 'log'}, {'$push': {'past_updates': data}})
        channel = self.client.get_channel(UPDATE_CHANNEL)
        msg = await channel.send(content= '<@&795422783261114398>', embed=embed)
        await ctx.message.delete()
        await msg.publish()

    @check()
    @commands.command(extras={"category":Category.OTHER}, usage="update <version(optional)>")
    async def update(self, ctx, version:str=None):
        """Allows you to view current and past updates"""
        if version is None:
            data = updates.find_one({'_id': 'current'})
        else:
            d = [x for x in updates.find_one({'_id': 'log'})['past_updates'] if x['version'] == version]
            if len(d) == 0:
                return await ctx.send('Invalid version!')
            data = d[0]
            
        author = await self.client.fetch_user(data["published_by"])
        embed = discord.Embed.from_dict({
            'title': f'Infos about version `{data["version"]}`',
            'description': str(data["description"]),
            'color': 0x1400ff,
            'footer': {'icon_url': str(author.avatar.url), 'text': f'Published on {data["published_on"].strftime("%b %d %Y %H:%M:%S")}'}
        })
        await ctx.send(embed=embed)

    @commands.is_owner() 
    @commands.command(extras={"category":Category.OTHER}, usage="blacklist <user_id>", hidden=True)
    async def blacklist(self, ctx, id:int, *,reason=None):
        """Blacklisting bad people like Hisoka. Owner restricted"""
        try:
            user = self.client.get_user(id) or await self.client.fetch_user(id)
        except Exception as e:
            return await ctx.send(e)
        # Inserting the bad person into my database
        blacklist.insert_one({'id': id, 'reason': reason or "No reason provided", 'date': datetime.utcnow()})
        await ctx.send(f'Blacklisted user `{user}` for reason: {reason}')
        
    @commands.is_owner()
    @commands.command(extras={"category":Category.OTHER}, usage="whitelist <user_id>", hidden=True)
    async def whitelist(self, ctx, id:int):
        """Whitelists a user. Owner restricted"""

        try:
            user = self.client.get_user(id) or await self.client.fetch_user(id)
        except Exception as e:
            return await ctx.send(e)

        blacklist.delete_one({'id': id})
        await ctx.send(f'Successfully whitelisted `{user}`')
    
    @commands.is_owner()
    @commands.command(extras={"category":Category.OTHER}, usage="say <text>", hidden=True)
    async def say(self, ctx, *, content):
        """Let's Killua say what is specified with this command. Possible abuse leads to this being restricted"""

        await ctx.message.delete()
        await ctx.send(content, reference=ctx.message.reference)

    @commands.is_owner()
    @commands.command(aliases=['st', 'pr', 'status'], extras={"category":Category.OTHER}, usage="pr <text>", hidden=True)
    async def presence(self, ctx, *, status):
        """Changes the presence of Killua. Owner restricted"""

        if status == '-rm':
            pr.update_many({}, {'$set': {'text': None, 'activity': None, 'presence': None}})
            await ctx.send('Done! reset Killua\'s presence')
            return await self.client.update_presence()

        activity = re.search(r'as\(.*?\)ae', status)
        if activity:
            activity = activity[0].lower()[3:-3]
            if not activity in ['playing', 'listening', 'watching', 'competing']:

                return await ctx.send('Invalid activity!')
        presence = re.search(r'ps\(.*?\)pe', status)
        if presence:
            presence = presence[0].lower()[3:-3]
            if not presence in ['dnd', 'idle', 'online']:
                return await ctx.send('Invalid presence!')
        text = re.search(r'ts\(.*?\)te', status)
        pr.update_many({}, {'$set': {'text': text[0][3:-3], 'presence': presence, 'activity': activity}})
        await self.client.update_presence()
        await ctx.send(f'Successfully changed Killua\'s status to `{text[0][3:-3]}`! (I hope people like it >-<)')



Cog = DevStuff

def setup(client):
    client.add_cog(DevStuff(client))
