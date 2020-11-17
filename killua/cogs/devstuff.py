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


Cog = devstuff

def setup(client):
    client.add_cog(devstuff(client))
