import inspect
import discord
from discord.ext import commands
import time
from datetime import datetime, timedelta
import random
from random import randint

topics = ['What\'s your favorite animal?', 'What is your favorite TV show?', 'If you could go anywhere in the world, where would you go?', 'What did you used to do, stopped and wish you hadn\'t?', 'What was the best day in your life?', 'For what person are you the most thankful for?', 'What is and has always been your least favorite subject?', 'What always makes you laugh and/or smile when you think about it?', 'Do you think there are aliens?', 'What is your earliest memory?', 'What\'s your favorite drink?', 'Where do you like going most for vacation?', 'What motivates you?', 'What is the best thing about school/work?', 'What\'s better, having high expectations or having low expectations?', 'What was the last movie you saw?', 'Have you read anything good recently?', 'What is your favorite day of the year?', 'What kind of music do you like to listen to?', 'What things are you passionate about?', 'What is your favorite childhood memory?', 'If you could acquire any skill, what would you choose?', 'What is the first thing that you think of in the morning?', 'What was the biggest life change you have gone through?', 'What is your favorite song of all time?', 'If you won $1 million playing the lottery, what would you do?', 'How would you know if you were in love?', 'If you could choose to have any useless super power, what would you pick?']


class smallcommands(commands.Cog):

    def __init__(self, client):
        self.client = client
        
    @commands.command()
    async def say(self, ctx, *, content):
      #r user ID: 606162661184372736
      #t 5 minutes
      if ctx.author.id == 606162661184372736:
        await ctx.message.delete()
        await ctx.send(content)
        
    @commands.command()
    async def ping(self, ctx):
      #c pong
      #t 5 min
    
      start = time.time()
      msg = await ctx.send('Pong!')
      end = time.time()
      await msg.edit(content = str('Pong in `' + str(1000 * (end - start))) + '` ms')
      
    @commands.command(name='topic')
    async def topic(self, ctx):
      #c constantly updating!
      await ctx.send(random.choice(topics))
      
    @commands.command()
    async def hi(self, ctx):
      #c The first command on Killua...
      #t 5 min
      await ctx.send("Hello " + str(ctx.author)) 
        
        
def setup(client):
    client.add_cog(smallcommands(client))
