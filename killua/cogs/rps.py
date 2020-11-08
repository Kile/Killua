import pymongo
from pymongo import MongoClient
import discord
from discord.ext import commands
import random
from random import randint
import asyncio

cluster = MongoClient('mongodb+srv://Kile:Kile2-#2@cluster0.q9qss.mongodb.net/teams?retryWrites=true&w=majority')
db = cluster['Killua']
collection = db['teams']
top =db['teampoints']
server = db['guilds']

class rps(commands.Cog):

  def __init__(self, client):
    self.client = client
    
  @commands.command()
  async def rps(self, ctx, member: discord.User, points: int=None):
    #c The most complicated command I ever made
    #t a week
    
    if member.id == ctx.author.id:
      return await ctx.send('Baka! You can\'t play against yourself')
    
    t2 = None
    p2 = 0

    resultsopp = collection.find({'id': member.id})
    for resulte in resultsopp:
        p2 = resulte['points']
        t2 = resulte['team']

    print(t2)

    results = collection.find({'id': ctx.author.id})
    for result in results:
        p1 = result['points']
        t1 = result['team']

    try:

        if t1 == None and points:
            await ctx.send('You need to join a team to play Rock Paper Scissors')
            return
        
        if points:
            if points <= 0 or points > 100:
                await ctx.send(f'You can only play using 1-100 points')
                return

        if points:
            if p1 < points or p1 is None:
                await ctx.send(f'You do not have enough points for that. Your current balance is `{str(p1)}`')
                return

        
        channel = ctx.message.channel
       

        if member.id == 756206646396452975:
            await ctx.author.send('You chose to play Rock Paper Scissors against me, what\'s your choice? **[Rock] [Paper] [Scissors]**')

            embed = discord.Embed.from_dict({
                'title': f'{ctx.author.name} against Killua-dev: **Rock... Paper... Scissors!**',
                'image': {'url': 'https://media1.tenor.com/images/dc503adb8a708854089051c02112c465/tenor.gif?itemid=5264587'},
                'color': 0x1400ff
                })

            await ctx.send(embed= embed)
            def check(m):
                return m.content.lower() == 'scissors' or m.content.lower() == 'paper' or m.content.lower() == 'rock' and m.author == ctx.author
                
            msg = await self.client.wait_for('message', check=check, timeout=60) 

            winlose = await rpsf(msg.content, random.choice(['paper', 'rock', 'scissors']))
            
            if winlose == 1:
                result = botemote(msg.content, 1)
                if points:
                    collection.update_one({'id': ctx.author.id}, {'$set':{'points': p1 + points}})
                    await channel.send(f'{rpsemote(msg.content.lower())} > {rpsemote(result)}: {ctx.author.mention} won against <@756206646396452975> winning {points} points')
                else:
                    await channel.send(f'{rpsemote(msg.content.lower())} > {rpsemote(result)}: {ctx.author.mention} won against <@756206646396452975>')
            if winlose == 2:
                result = botemote(msg.content, 2)
                await channel.send(f'{rpsemote(msg.content.lower())} = {rpsemote(result)}: {ctx.author.mention} tied against <@756206646396452975>')
            if winlose == 3:
                result = botemote(msg.content, 3)
                if points:
                    collection.update_one({'id': ctx.author.id}, {'$set':{'points': p1 - points}})
                    await channel.send(f'{rpsemote(msg.content.lower())} < {rpsemote(result)}: {ctx.author.mention} lost against <@756206646396452975> losing {points} points')
                else:
                    await channel.send(f'{rpsemote(msg.content.lower())} < {rpsemote(result)}: {ctx.author.mention} lost against <@756206646396452975>')
        else:
            
            
            if t2 is None and points:

                await ctx.send(f'{member.mention} is not part of a team yet')
                return

            if points:
                if int(p2) < points or p2 is None and points:

                    await ctx.send(f'{member.mention} does not have enough points for that. Their current balance is `{str(p2)}`')
                    return
            

            await ctx.send(f'{ctx.author.mention} challanged {member.mention} to a game of Rock Papaper Scissors! Will **{member.name}** accept the challange?\n **[y/n]**')
            def check(m1):
                    return m1.content.lower() in ["n", "y"] and m1.author.id == member.id

            try:
                    confirmmsg = await self.client.wait_for('message', check=check, timeout=60)

            except asyncio.TimeoutError:

                await ctx.send('Sadly no answer, try it later bud')

            else:
                if confirmmsg.content.lower() == 'y':

                    embed = discord.Embed.from_dict({
                        'title': f'{ctx.author.name} against {member.name}: **Rock... Paper... Scissors!**',
                        'image': {'url': 'https://media1.tenor.com/images/dc503adb8a708854089051c02112c465/tenor.gif?itemid=5264587'},
                        'color': 0x1400ff
                    })
                        
                    await ctx.send(embed= embed)
                    await ctx.author.send('You chose to play Rock Paper Scissors, what\'s your choice Hunter? **[Rock] [Paper] [Scissors]**') 
                    await member.send('You chose to play Rock Paper Scissors, what\'s your choice Hunter? **[Rock] [Paper] [Scissors]**') 


                    def checkauthor(m2):
                        
                        return  m2.content.lower() in ["rock", "paper", "scissors"] and m2.author == ctx.author and m2.guild is None
                    def checkopp(m3):
                       
                        return  m3.content.lower() in ["rock", "paper", "scissors"] and m3.author == member and m3.guild is None
                    

                    done, pending = await asyncio.wait([
                        self.client.wait_for('message', check= checkauthor),
                        self.client.wait_for('message', check= checkopp)
                    ], return_when=asyncio.ALL_COMPLETED)

                    
                    
                    r1, r2 = [r.result() for r in done]

                    
                    
                    winlose = await rpsf(str(r1.content), str(r2.content))
                    if winlose == 1:
                        if points:
                            collection.update_one({'id': ctx.author.id}, {'$set':{'points': p1 + points}})
                            collection.update_one({'id': member.id}, {'$set':{'points': p2 - points}})
                            await channel.send(f'{rpsemote(r1.content.lower())} > {rpsemote(r2.content.lower())}: {ctx.author.mention} won against {member.mention} winning {points} points')
                        else:
                             await channel.send(f'{rpsemote(r1.content.lower())} > {rpsemote(r2.content.lower())}: {ctx.author.mention} won against {member.mention}')
                    if winlose == 2:
                        await channel.send(f'{rpsemote(r1.content.lower())} = {rpsemote(r2.content.lower())}: {ctx.author.mention} tied against {member.mention}')
                    if winlose == 3:
                        if points:
                            collection.update_one({'id': ctx.author.id}, {'$set':{'points': p1 - points}})
                            collection.update_one({'id': member.id}, {'$set':{'points': p2 + points}})
                            await channel.send(f'{rpsemote(r1.content.lower())} < {rpsemote(r2.content.lower())}: {ctx.author.mention} lost against {member.mention} losing {points } points')
                        else:
                            await channel.send(f'{rpsemote(r1.content.lower())} < {rpsemote(r2.content.lower())}: {ctx.author.mention} lost against {member.mention}')
                else:
                    await ctx.send(f'{member.name} does not want to play...')

    except Exception as e:
        await ctx.send(e)

    
def rpsemote(choice):
    if choice == 'paper':
        return '📄'
    if choice == 'rock':
        return '🗿'
    if choice == 'scissors':
        return ':scissors:'

def botemote(playeremote, winlose):
    print(playeremote)
    if playeremote.lower() == 'paper':
        if winlose == 1:
            return 'rock'
        if winlose == 2:
            return 'paper'
        if winlose == 3:
            return 'scissors'

    if playeremote.lower() == 'rock':
        if winlose == 1:
            return 'scissors'
        if winlose == 2:
            return 'rock'
        if winlose == 3:
            return 'paper'

    if playeremote.lower() == 'scissors':
        if winlose == 1:
            return 'paper'
        if winlose == 2:
            return 'scissors'
        if winlose == 3:
            return 'rock'

async def rpsf(choice1, choice2):

    if choice1.lower() == 'rock' and choice2.lower() == 'scissors':
        return 1
    if choice1.lower() == 'rock' and choice2.lower() == 'rock':
        return 2
    if choice1.lower() == 'rock' and choice2.lower() == 'paper':
        return 3
    if choice1.lower() == 'paper' and choice2.lower() == 'rock':
        return 1
    if choice1.lower() == 'paper' and choice2.lower() == 'paper':
        return 2
    if choice1.lower() == 'paper' and choice2.lower() == 'scissors':
        return 3
    if choice1.lower() == 'scissors' and choice2.lower() == 'paper':
        return 1
    if choice1.lower() == 'scissors' and choice2.lower() == 'scissors':
        return 2
    if choice1.lower() == 'scissors' and choice2.lower() == 'rock':
        return 3

Cog = rps

def setup(client):
    client.add_cog(rps(client))
