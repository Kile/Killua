import discord
from datetime import datetime, date, timedelta
import time
from discord.utils import find
from discord.ext import commands, tasks
import pymongo
from pymongo import MongoClient
import dbl
import json
from json import loads
from killua.functions import custom_cooldown, blcheck
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
    self.token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc1NjIwNjY0NjM5NjQ1Mjk3NSIsImJvdCI6dHJ1ZSwiaWF0IjoxNjA5Njc2NTA4fQ.zlAa_xAyxck-K_Am47l5hytJ2Nams3CxmXWLiyz1y3M' # set this to your DBL token
    self.dblpy = dbl.DBLClient(self.client, self.token, autopost=True)
    self.status.start()
    
  @commands.Cog.listener()
  async def on_ready(self):
    print('------')
    print('Logged in as: ' + self.client.user.name + f" (ID: {self.client.user.id})")
    print('------')
    self.client.startup_datetime = datetime.now()

  @tasks.loop(hours=12)
  async def status(self):
    await p(self)

  @status.before_loop
  async def before_status(self):
      await self.client.wait_until_ready()

  @commands.Cog.listener()
  async def on_guild_join(self, guild):
    #Changing the status
    await p(self)
    results = server.find({'id': guild.id})
    
    for result in results:
      ID = result
    #Inserting the guild in the databse if it doesn't exist
    try:
      prefix = ID['prefix']
    except UnboundLocalError:
      server.update_many({'id': guild.id},{'$set':{'points': 0,'items': '','badges': ['early supporter'], 'prefix': 'k!'}}, upsert=True)
      prefix = 'k!'
      
    general = find(lambda x: x.name == 'general',  guild.text_channels)
    if general and general.permissions_for(guild.me).send_messages:
        embed = discord.Embed.from_dict({
            'title': 'Hello {}!'.format(guild.name),
            'description': f'Hi, my name is Killua, thank you for choosing me! \n\nTo get some info about me, use `{prefix}info`\n\nTo change the server prefix, use `{prefix}prefix <new prefix>` (you need administrator perms for that\n\nFor more commands, use `{prefix}help` to see every command\n\nPlease consider leaving feeback with `k!fb` as this helps me improve Killua',
            'color': 0x1400ff
        })
        await general.send(embed=embed)
  
  @commands.Cog.listener()
  async def on_command_error(self, ctx, error):
    #This handels the k!bug cooldown
    if isinstance(error, discord.ext.commands.CommandOnCooldown):
      m, s = divmod(round(ctx.command.get_cooldown_retry_after(ctx)), 60)

      await ctx.send(f'Wait {m:02d} minutes and {s:02d} seconds before using the command again, thank you for helping to improve killua :3')
    else:
      print(error)

        
  @commands.Cog.listener()
  async def on_connect(self):
    #Changing Killua's status
    await p(self)
    

  @commands.Cog.listener()
  async def on_guild_remove(self, guild):
    #Changing Killua's status
    await p(self)
    
    
'''function p
Input:
self: taking in self because it is outside of a function

Returns:
Nothing

Purpose:
Changing Killuas presence freqently if he is adeed to a guild, removed or 12 hour pass
'''    

async def p(self):
  a = date.today()
  #The day Killua was born!!
  b = date(2020,9,17)
  delta = a - b
  playing = discord.Activity(name=f'over {len(self.client.guilds)} guilds | day {delta.days}', type=discord.ActivityType.watching)

  await self.client.change_presence(status=discord.Status.online, activity=playing)
  
  
Cog = events


def setup(client):
  client.add_cog(events(client))
