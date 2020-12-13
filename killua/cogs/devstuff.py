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
with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())


cluster = MongoClient(config['mongodb'])
db = cluster['Killua']
collection = db['teams']
top =db['teampoints']
server = db['guilds']

class devstuff(commands.Cog):

    def __init__(self, client):
        self.client = client


    @commands.command()
    async def eval(self, ctx, *, c):
        if ctx.author.id == 606162661184372736:
            try:
                global bot
                await ctx.channel.send(f'```py\n{eval(c)}```')
            except Exception as e:
                await ctx.channel.send(str(e))

    @commands.command()
    async def source(self, ctx, name):
        if ctx.author.id == 606162661184372736 or ctx.author.id == 383790610727043085:
            func = self.client.get_command(name).callback
            code = inspect.getsource(func)
            await ctx.send('```python\n{}```'.format(code.replace('```', '``')))

    @commands.command()
    async def codeinfo(self, ctx, content):
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
		    await ctx.send('Invalid command')



Cog = devstuff

def setup(client):
    client.add_cog(devstuff(client))
