from discord.ext import commands
import io
import aiohttp
import time
import discord
import random
import json
from json import loads
from random import randint
from datetime import datetime, date, timedelta
from discord.ext import tasks
import pymongo
from pymongo import MongoClient
from pprint import pprint
import asyncio
import inspect
from inspect import getsource
from discord.utils import find
from discord import client
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from numpy import *
from matplotlib.pyplot import *
import matplotlib.pyplot as plt
import numpy as np
import numexpr as ne
from killua.cogs.events import p
from killua.functions import custom_cooldown, blcheck
with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())


cluster = MongoClient(config['mongodb'])
db = cluster['Killua']
collection = db['teams']
top =db['teampoints']
server = db['guilds']
generaldb = cluster['general']
blacklist = generaldb['blacklist']

presence = None

class devstuff(commands.Cog):

    def __init__(self, client):
        self.client = client

    #Eval command, unecessary with the jsk extension but useful for databse stuff
    @commands.command()
    async def eval(self, ctx, *, c):
        if blcheck(ctx.author.id) is True:
            return
        #h Standart eval command, me restricted ofc
        if ctx.author.id == 606162661184372736:
            try:
                global bot
                await ctx.channel.send(f'```py\n{eval(c)}```')
            except Exception as e:
                await ctx.channel.send(str(e))

    @commands.command()
    async def source(self, ctx, name):
        if blcheck(ctx.author.id) is True:
            return
        #h Displays the source code to a command, if discord allows it :3
        # Idk what that does tbh
        func = self.client.get_command(name).callback
        code = inspect.getsource(func)
        await ctx.send('```python\n{}```'.format(code.replace('```', '``')))

    @commands.command()
    async def codeinfo(self, ctx, content):
        #h Gives you some information to a specific command like how many lines, how much time I spend on it etc

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
    async def update(self, ctx, *, update):
        if blcheck(ctx.author.id) is True:
            return
        #h Allows me to publish Killua updates in a handy formart 
        #r user ID 606162661184372736
        if ctx.author.id != 606162661184372736:
            return
        embed = discord.Embed.from_dict({
                        'title': 'Killua Update',
                        'description': update,
                        'color': 0x1400ff,
                        'footer': {'text': f'Update by {ctx.author}', 'icon_url': str(ctx.author.avatar_url)},
                        'image': {'url': 'https://cdn.discordapp.com/attachments/780554158154448916/788071254917120060/killua-banner-update.png'}
                    })
        # #updates in my dev
        channel = self.client.get_channel(757170264294424646)
        msg = await channel.send(content= '<@&795422783261114398>', embed=embed)
        await msg.publish()
        await ctx.message.delete()

    @commands.command()
    async def blacklist(self, ctx, id:int, *,reason=None):
        #h Blacklisting bad people like Hisoka
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
        if ctx.author.id != 606162661184372736:
            return
        try:
            user = await self.client.fetch_user(id)
        except Exception as e:
            return await ctx.send(e)

        blacklist.delete_one({'id': id})
        await ctx.send(f'Successfully whitelisted `{user}`')

    @commands.command()
    async def presence(self, ctx, *, status):
        if ctx.author.id != 606162661184372736:
            return
        if status == '-rm':
            presence = None
            return await p()

        presence = status
        await p()
        await ctx.send(f'Succesfully changed Killua\'s status to `{status}`! (I hope people like it >-<)')

Cog = devstuff

def setup(client):
    client.add_cog(devstuff(client))
