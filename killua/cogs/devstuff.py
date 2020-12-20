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
from discord.utils import find
from discord import client
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from numpy import *
from matplotlib.pyplot import *
import matplotlib.pyplot as plt
import numpy as np
import numexpr as ne
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

class devstuff(commands.Cog):

    def __init__(self, client):
        self.client = client


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
        #h Displays the source code to a command, once Killua is open source this will be unrestricted
        if ctx.author.id == 606162661184372736 or ctx.author.id == 383790610727043085:
            func = self.client.get_command(name).callback
            code = inspect.getsource(func)
            await ctx.send('```python\n{}```'.format(code.replace('```', '``')))

    @commands.command()
    async def codeinfo(self, ctx, content):
        #h Gives you some information to a specific command like how many lines, how much time I spend on it etc
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



		    embed= Embed.from_dict({
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
    async def resetdaily(self, ctx, user:discord.User):
        if ctx.author.id != 606162661184372736:
            return
        try:
            teams.update_many({'id': user.id},{'$set':{'cooldowndaily': datetime.today()}}, upsert=True)
            await ctx.send(f'Success! `{user}` can their daily points again')
        except Exception as e:
            await ctx.send(e)

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
        channel = self.client.get_channel(757170264294424646)
        msg = await channel.send(embed=embed)
        await msg.publish()

    @commands.command()
    async def blacklist(self, ctx, id:int, *,reason=None):
        if blcheck(ctx.author.id) is True:
            return
        if ctx.author.id != 606162661184372736:
            return
        try:
            user = await self.client.fetch_user(id)
        except Exception as e:
            return await ctx.send(e)
        today = date.today()
        blacklist.insert_one({'id': id, 'reason':reason or "No reason provided", 'date': today.strftime("%B %d, %Y")})

        await ctx.send(f'Blacklisted user `{user}` for reason: {reason}')
        
    @commands.command()
    async def whitelist(self, ctx, id:int):
        if ctx.author.id != 606162661184372736:
            return
        try:
            user = await self.client.fetch_user(id)
        except Exception as e:
            return await ctx.send(e)

        blacklist.delete_one({'id': id})
        await ctx.send(f'Successfully whitelisted `{user}`')


Cog = devstuff

def setup(client):
    client.add_cog(devstuff(client))
