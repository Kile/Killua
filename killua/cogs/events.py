import discord
from datetime import datetime, date, timedelta
import time
from discord.utils import find
from discord.ext import commands
import pymongo
from pymongo import MongoClient
import json
from json import loads
from devstuff import blcheck
with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())


cluster = MongoClient(config['mongodb'])
db = cluster['Killua']
server = db['guilds']
generaldb = cluster['general']
blacklist = generaldb['blacklist']

class events(commands.Cog):
  
  def __init__(self, client):
    self.client = client
    
  @commands.Cog.listener()
  async def on_ready(self):
    print('------')
    print('Logged in as: ' + self.client.user.name + f" (ID: {self.client.user.id})")
    print('------')
    self.client.startup_datetime = datetime.now()
    
  @commands.Cog.listener()
  async def on_guild_join(self, guild):
    await p(self)
    results = server.find({'id': guild.id})
    
    for result in results:
      ID = result
    
    try:
      prefix = ID['prefix']
    except UnboundLocalError:
      server.update_many({'id': guild.id},{'$set':{'points': 0,'items': '','badges': '', 'prefix': 'k!'}}, upsert=True)
      prefix = 'k!'
      
    general = find(lambda x: x.name == 'general',  guild.text_channels)
    if general and general.permissions_for(guild.me).send_messages:
        embed = discord.Embed.from_dict({
            'title': 'Hello {}!'.format(guild.name),
            'description': f'Hi, my name is Killua, thank you for choosing me! \n\nTo get some info about me, use `{prefix}info`\n\nTo change the server prefix, use `{prefix}prefix <new prefix>` (you need administrator perms for that\n\nFor more commands, use `{prefix}help` to see every command',
            'color': 0x1400ff
        })
        await general.send(embed=embed)
  
  @commands.Cog.listener()
  async def on_command_error(self, ctx, error):
    if isinstance(error, discord.ext.commands.CommandOnCooldown):
      m, s = divmod(round(ctx.command.get_cooldown_retry_after(ctx)), 60)

      await ctx.send(f'Wait {m:02d} minutes and {s:02d} seconds before using the command again :3')

        
  @commands.Cog.listener()
  async def on_connect(self):
    await p(self)
    

  @commands.Cog.listener()
  async def on_guild_remove(self, guild):
    await p(self)
    
    
    
    

async def p(self):
  a = date.today()
  b = date(2020,9,17)
  delta = a - b


  playing = discord.Activity(name=f'over {len(self.client.guilds)} guilds | day {delta.days}', type=discord.ActivityType.watching)

  await self.client.change_presence(status=discord.Status.online, activity=playing)
  
  
Cog = events


def setup(client):
  client.add_cog(events(client))
