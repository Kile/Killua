import discord
from discord.ext import commands
import pymongo
import json
from json import loads
from killua.functions import custom_cooldown, blcheck
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



class Prefix(commands.Cog):

  def __init__(self, client):
    self.client = client

  @commands.command(aliases = ['pref'])
  async def prefix(self, ctx, prefix:str=None):
    if blcheck(ctx.author.id) is True:
      return
      #r to the guild administrator
      #t Around 2-4 hours
      #c Custom prefixes!
      #h Set your server prefix with this command
      #u prefix <prefix>
    results = server.find_one({'id': ctx.guild.id})
    if prefix:
      if ctx.author.guild_permissions.administrator:

        server.update_many({'id': ctx.guild.id},{'$set':{'prefix': prefix}}, upsert=True)
        await ctx.send(f'Changed server prefix to `{prefix}`')

      else: 
        await ctx.send('Missing permissions')
    elif results:
      await ctx.send(f'The current server prefix is `{results["prefix"]}`')
    else:
      await ctx.send(f'The current server prefix is `{results["prefix"]}`')

Cog = Prefix

def setup(client):
    client.add_cog(Prefix(client))
