from discord.ext import commands
import discord
import json
from datetime import datetime, timedelta
from pymongo import MongoClient
import re
from killua.checks import check, p
from killua.cogs.cards import Card, User, Category#lgtm [py/unused-import]
from killua.cogs.pxlapi import PxlClient #lgtm [py/unused-import]
from killua.constants import teams, guilds, blacklist, presence as pr, items, updates #lgtm [py/unused-import]

class DevStuff(commands.Cog):

    def __init__(self, client):
        self.client = client

    #Eval command, unecessary with the jsk extension but useful for databse stuff
    @commands.is_owner()
    @commands.command(aliases=['exec'], extras={"category":Category.OTHER}, usage="eval <code>", hidden=True)
    async def eval(self, ctx, *, code):
        """Standart eval command, owner restricted ofc"""
        try:
            await ctx.channel.send(f'```py\n{eval(code)}```')
        except Exception as e:
            await ctx.channel.send(str(e))

    @commands.is_owner()
    @commands.command(extras={"category":Category.OTHER}, usage="publish update <version> <text>", hidden=True)
    async def publish_update(self, ctx, version:str, *, update):
        """Allows me to publish Killua updates in a handy formart"""

        old = updates.find_one({'_id':'current'})
        log = updates.find_one({'_id': 'log'})
        embed = discord.Embed.from_dict({
            'title': f'Killua Update `{old["version"]}` -> `{version}`',
            'description': update,
            'color': 0x1400ff,
            'footer': {'text': f'Update by {ctx.author}', 'icon_url': str(ctx.author.avatar.url)},
            'image': {'url': 'https://cdn.discordapp.com/attachments/780554158154448916/788071254917120060/killua-banner-update.png'}
        })
        try:
            log.append(old)
        except Exception:
            log = [old]
        updates.update_one({'_id': 'current'}, {'$set': {'version': version, 'description': update, 'published_on': datetime.now(), 'published_by': ctx.author.id}})
        updates.update_one({'_id': 'log'}, {'$set': {'past_updates': log}})
        channel = self.client.get_channel(757170264294424646)
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
            user = await self.client.fetch_user(id)
        except Exception as e:
            return await ctx.send(e)
        # Inserting the bad person into my databse
        blacklist.insert_one({'id': id, 'reason':reason or "No reason provided", 'date': datetime.now()})
        await ctx.send(f'Blacklisted user `{user}` for reason: {reason}')
        
    @commands.is_owner()
    @commands.command(extras={"category":Category.OTHER}, usage="whitelist <user_id>", hidden=True)
    async def whitelist(self, ctx, id:int):
        """Whitelists a user. Owner restricted"""

        try:
            user = await self.client.fetch_user(id)
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
            return await p(self)

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
        await p(self)
        await ctx.send(f'Succesfully changed Killua\'s status to `{text[0][3:-3]}`! (I hope people like it >-<)')



Cog = DevStuff

def setup(client):
    client.add_cog(DevStuff(client))
