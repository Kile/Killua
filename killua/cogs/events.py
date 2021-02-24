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
from killua.functions import custom_cooldown, blcheck, p
with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())

premium = {
    759891477269839926 : "one_star_hunter",
    798279223344889957 : "two_star_hunter",
    798279346389254174 : "triple_star_hunter",
    769622564648648744 : "server_booster"
}

cluster = MongoClient(config['mongodb'])
db = cluster['Killua']
server = db['guilds']
teams = db['teams']
generaldb = cluster['general']
blacklist = generaldb['blacklist']
pr = generaldb['presence']

class Events(commands.Cog):
  
  def __init__(self, client):
    self.client = client
    self.token = config['dbl']
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
      prefix = ID['prefix']#This is a dumb way to do it and will be optimised when I have time
    except UnboundLocalError:
      server.update_many({'id': guild.id},{'$set':{'points': 0,'items': '','badges': [], 'prefix': 'k!'}}, upsert=True)
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
    server.delete_one({'id': guild.id})

  @commands.Cog.listener()
  async def on_member_update(self, before, after):
    try:
      if not before.guild.id == 715358111472418908:
        return
    except:
      s = list(premium.keys())
      b = []
      a = []
      for role in before.roles:
        b.append(role.id)
      for role in after.roles:
        a.append(role.id)

      common_elements = set(s).intersection(b)
      if common_elements:
        for element in common_elements:
          if element in s and not element in a:
            await remove_premium(before, element)

      common_elements = set(s).intersection(a)
      if common_elements:
        for element in common_elements:
          if element in s and not element in b:
            await add_premium(after, element) 
  
async def remove_premium(member:discord.Member, s_id:int):
  user = teams.find_one({'id': member.id})
  badges = user['badges']
  badges.remove('premium')
  badges.remove(premium[s_id])
  teams.update_one({'id': member.id}, {'$set': {'badges': badges}})
  try:
    await member.send('Your Killua premium subscription ran out! Your premium permissions have sadly been taken :c. I hope you enjoyed your time as Killua supporter. (If you see this message after this you left Killuas server please rejoin to get Premium permissions again as you need to be on the server for that)')
  except:
    pass
  return

async def add_premium(member:discord.Member, s_id:int):
  user = teams.find_one({'id': member.id})
  badges = user['badges']
  if not "premium" in user["badges"]:
    badges.append('premium')
  badges.append(premium[s_id])
  teams.update_one({'id': member.id}, {'$set': {'badges': badges}})
  try:
    await member.send('Thank you for becoming a premium supporter! Check out your shiney badges with `k!profile` and have fun with your new perks!')
  except:
    pass
  return
  
Cog = Events


def setup(client):
  client.add_cog(Events(client))
