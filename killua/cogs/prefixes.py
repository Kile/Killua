import discord
from discord.ext import commands
import pymongo
import json
from json import loads
from functions import custom_cooldown, blcheck
from pymongo import MongoClient
with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())

cluster = MongoClient(config['mongodb'])
db = cluster['Killua']
collection = db['teams']
top =db['teampoints']
server = db['guilds']
items = db['items']
generaldb = cluster['general']
blacklist = generaldb['blacklist']


class prefix(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_message_create(self, message):
      if message.content == 'k!default pref' and message.author.guild_permissions.administrator:
        server.update_many({'id': message.guild.id},{'$set':{'prefix': 'k!'}}, upsert=True)

        await message.channel.send('Set prefix to default `k!`')
      await bot.process_commands(message)

    @commands.command(aliases = ['pref'])
    async def prefix(self, ctx, prefix=None):
      if blcheck(ctx.author.id) is True:
        return
        #r to the guild administrator
        #t Around 2-4 hours
        #c Custom prefixes!
        #h Set your server prefix with this command
      results = server.find({'id': ctx.guild.id})
      for result in results:
        pref = result['prefix']
      if prefix:
        if ctx.author.guild_permissions.administrator:

          server.update_many({'id': ctx.guild.id},{'$set':{'prefix': str(prefix)}}, upsert=True)
          await ctx.send(f'Changed server prefix to `{prefix}`')

        else: 
          await ctx.send('Missing permissions')
      else:
        await ctx.send(f'The current server prefix is `{pref}`')

Cog = prefix

def setup(client):
    client.add_cog(prefix(client))
