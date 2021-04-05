from discord.ext import commands
import io
import aiohttp
import time
import discord
import random
import json
from json import loads
from datetime import datetime, date, timedelta
from discord.ext import tasks
import pymongo
from pymongo import MongoClient
from pprint import pprint
import asyncio
import inspect
from inspect import getsource
from discord.utils import find
from numpy import *
from matplotlib.pyplot import *
import matplotlib.pyplot as plt
import numpy as np
import numexpr as ne
import re
import math
from killua.functions import custom_cooldown, blcheck, p
from killua.cogs.cards import Card, User
with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())


cluster = MongoClient(config['mongodb'])
db = cluster['Killua']
teams = db['teams']
top =db['teampoints']
server = db['guilds']
generaldb = cluster['general']
blacklist = generaldb['blacklist']
pr = generaldb['presence']
items = db['items']
updates = generaldb['updates']


class DevStuff(commands.Cog):

    def __init__(self, client):
        self.client = client

    #Eval command, unecessary with the jsk extension but useful for databse stuff
    @commands.command()
    async def eval(self, ctx, *, c):
        if blcheck(ctx.author.id) is True:
            return
        #h Standart eval command, me restricted ofc
        #u eval <code>
        if ctx.author.id == 606162661184372736:
            try:
                global bot
                await ctx.channel.send(f'```py\n{eval(c)}```')
            except Exception as e:
                await ctx.channel.send(str(e))


    @commands.command()
    async def codeinfo(self, ctx, *,content):
        #h Gives you some information to a specific command like how many lines, how much time I spend on it etc
        #u codeinfo <command>
        # Using the K!source principle I can get infos about code with this
	    try:
		    func = ctx.bot.get_command(content).callback
		    code = getsource(func)
		    linecount = code.splitlines()
		    time= ''
		    restricted = ''
		    comment = ''
		    for item in linecount:
			    firstt, middlet, lastt = item.partition("#t")
			    firstr, middler, lastr = item.partition("#r")
			    firstc, middlec, lastc = item.partition("#c")
			    if lastt == '':
				    pass
			    else:
				    time = lastt
			    if lastr == '':
				    pass
			    else:
				    restricted = lastr
			    if lastc == '':
				    pass
			    else:
				    comment = lastc
			    #c this very code
			    #t 1-2 hours
		    if restricted == '' or restricted is None or restricted == '")':
			    realrestricted = ''
		    else:
			    realrestricted = f'**Restricted to:** {restricted}'

		    embed= discord.Embed.from_dict({
			    'title': f'Command **{content}**',
			    'color': 0x1400ff,
			    'description': f'''**Characters:** {len(code)}
			    **Lines:**  {len(linecount)}


			    **Time spend on code:** {time or 'No time provided'}
			    **Comments:** {comment or 'No comment'}

			    {realrestricted}'''
			})
		    await ctx.send(embed=embed)
	    except Exception as e:
		    await ctx.send(f'Invalid command. Error: {e}')

    @commands.command()
    async def publish_update(self, ctx, version:str, *, update):
        #h Allows me to publish Killua updates in a handy formart
        #r user ID 606162661184372736
        if ctx.author.id != 606162661184372736:
            return
        old = updates.find_one({'_id':'current'})
        log = updates.find_one({'_id': 'log'})
        embed = discord.Embed.from_dict({
                        'title': f'Killua Update `{old["version"]}`->`{version}`',
                        'description': update,
                        'color': 0x1400ff,
                        'footer': {'text': f'Update by {ctx.author}', 'icon_url': str(ctx.author.avatar_url)},
                        'image': {'url': 'https://cdn.discordapp.com/attachments/780554158154448916/788071254917120060/killua-banner-update.png'}
                    })
        try:
            log.append(old)
        except:
            log = [old]
        updates.update_one({'_id': 'current'}, {'$set': {'version': version, 'description': update, 'published_on': datetime.now(), 'published_by': ctx.author.id}})
        updates.update_one({'_id': 'log'}, {'$set': {'past_updates': log}})
        channel = self.client.get_channel(757170264294424646)
        msg = await channel.send(content= '<@&795422783261114398>', embed=embed)
        await msg.publish()

    @commands.command()
    async def update(self, ctx, version:str=None):
        #h Allows you to view current and past updates
        #u update <version(optional)>
        if version == None:
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
            'footer': {'icon_url': str(author.avatar_url), 'text': f'Published on {data["published_on"].strftime("%b %d %Y %H:%M:%S")}'}
        })
        await ctx.send(embed=embed)

    @commands.command()
    async def blacklist(self, ctx, id:int, *,reason=None):
        #h Blacklisting bad people like Hisoka. Owner restricted
        #u blacklist <user>
        if blcheck(ctx.author.id) is True:
            return
        if ctx.author.id != 606162661184372736:
            return
        try:
            user = await self.client.fetch_user(id)
        except Exception as e:
            return await ctx.send(e)
        today = date.today()
        # Inserting the bad person into my databse
        blacklist.insert_one({'id': id, 'reason':reason or "No reason provided", 'date': today.strftime("%B %d, %Y")})

        await ctx.send(f'Blacklisted user `{user}` for reason: {reason}')
        
    @commands.command()
    async def whitelist(self, ctx, id:int):
        # One of the only commands I don't check the blacklist on because I couldn't whitelist myself if
        # I'd have blacklisted myself for testing
        #u whitelist <user>
        #h Whitelists a user. Owner restricted

        if ctx.author.id != 606162661184372736:
            return
        try:
            user = await self.client.fetch_user(id)
        except Exception as e:
            return await ctx.send(e)

        blacklist.delete_one({'id': id})
        await ctx.send(f'Successfully whitelisted `{user}`')

    @commands.command(aliases=['st', 'pr', 'status'])
    async def presence(self, ctx, *, status):
        #h Changes the presence of Killua. Owner restricted 
        #u pr <text>
        if ctx.author.id != 606162661184372736:
            return
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
