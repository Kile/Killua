import discord
from discord.ext import commands
import pymongo
from pymongo import MongoClient

cluster = MongoClient('mongodb+srv://Kile:Kile2-#2@cluster0.q9qss.mongodb.net/teams?retryWrites=true&w=majority')
db = cluster['Killua']
collection = db['teams']
top =db['teampoints']
server = db['guilds']
items = db['items']

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
        #r to the guild administrator
        #t Around 2-4 hours
        #c Custom prefixes!
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
<<<<<<< HEAD

=======
>>>>>>> ea404b285b0ca4aaf61355811118727e8a1affaf
