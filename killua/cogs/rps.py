import pymongo
from pymongo import MongoClient
import discord
from discord.ext import commands
import random
from random import randint
import asyncio
import json
from killua.functions import custom_cooldown, blcheck
from json import loads

with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())

cluster = MongoClient(config['mongodb'])
db = cluster['Killua']
teams = db['teams']
server = db['guilds']


class rps(commands.Cog):

  def __init__(self, client):
    self.client = client
    
  @commands.command()
  @custom_cooldown(30)
  async def rps(self, ctx, member: discord.User, points: int=None):
    if blcheck(ctx.author.id) is True:
      return
    #c The most complicated command I ever made
    #t a week
    #h Play Rock Paper Scissors with your friends! You can play investing points or just for fun.
    
    if member.id == ctx.author.id:
      return await ctx.send('Baka! You can\'t play against yourself')
    
    resultsopp = teams.find_one({'id': member.id})
    if resultsopp is None and member != ctx.me and points:
        return await ctx.send('The opponed needs to be registered to play with points (use `k!daily` once)')

    if member != ctx.me and not resultsopp is None:
        p2 = resultsopp['points']
    elif member == ctx.me:
        p2 = False

    results = teams.find_one({'id': ctx.author.id})
    if results is None and points:
        return await ctx.send('You need to be registered to play with points (use `k!daily` once)')

    p1 = results['points']
 
    if points:
        if points <= 0 or points > 100:
            return await ctx.send(f'You can only play using 1-100 points')

        if p1 < points:
            return await ctx.send(f'You do not have enough points for that. Your current balance is `{p1}`')
        if not p2 is False and p2 < points:
            return await ctx.send(f'Your opponent does not have enough points for that. Their current balance is `{p2}`')
  
       
    if member == ctx.me:
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
        c2 = random.choice(['paper', 'rock', 'scissors'])
        winlose = await rpsf(msg.content, c2)
        await evaluate(ctx, winlose, msg.content.lower(), c2, ctx.author, ctx.me, points)
    else:
        if await dmcheck(ctx.author) is False:
            return await ctx.send(f'You need to open your dm to Killua to play {ctx.author.mention}')
        if await dmcheck(member) is False:
            return await ctx.send(f'{member.name} needs to open their dms to Killua to play')

        await ctx.send(f'{ctx.author.mention} challanged {member.mention} to a game of Rock Papaper Scissors! Will **{member.name}** accept the challange?\n **[y/n]**')
        def check(m1):
            return m1.content.lower() in ["n", "y"] and m1.author.id == member.id

        try:
            confirmmsg = await self.client.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.send('Sadly no answer, try it later bud')

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
                winlose = await rpsf(r1.content, r2.content)
                await evaluate(ctx, winlose, r1.content.lower(), r2.content.lower(), r1.author, r2.author, points)
            else:
                await ctx.send(f'{member.name} does not want to play...')


    
def rpsemote(choice):
    if choice == 'paper':
        return '📄'
    if choice == 'rock':
        return '🗿'
    if choice == 'scissors':
        return '✂️'


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

async def evaluate(ctx, winlose:int, choice1, choice2, player1:discord.User, player2:discord.User, points:int=None):
    p1 = teams.find_one({'id': player1.id})
    p2 = teams.find_one({'id': player2.id})
    if winlose == 1:
        if points:
            teams.update_one({'id': player1.id}, {'$set':{'points': p1['points'] + points}})
            if player2 != ctx.me:
                teams.update_one({'id': player2.id}, {'$set':{'points': p2['points'] - points}})
            return await ctx.send(f'{rpsemote(choice1)} > {rpsemote(choice2)}: {player1.mention} won against {player2.mention} winning {points} points which adds to a total of {p1["points"]+ points}')
        else:
            return await ctx.send(f'{rpsemote(choice1)} > {rpsemote(choice2)}: {player1.mention} won against {player2.mention}')
    if winlose == 2:
        return await ctx.send(f'{rpsemote(choice1)} = {rpsemote(choice2)}: {player1.mention} tied against {player2.mention}')
    if winlose == 3:
        if points:
            teams.update_one({'id': player1.id}, {'$set':{'points': p1['points'] - points}})
            if player2 != ctx.me:
                teams.update_one({'id': player2.id}, {'$set':{'points': p2['points'] + points}})
            return await ctx.send(f'{rpsemote(choice1)} < {rpsemote(choice2)}: {player1.mention} lost against {player2.mention} losing {points} points which leaves them a total of {p1["points"]- points}')
        else:
            return await ctx.send(f'{rpsemote(choice1)} < {rpsemote(choice2)}: {player1.mention} lost against {player2.mention}')
       
async def dmcheck(user:discord.User):
    try:
        await user.send('')
    except Exception as e:
        if isinstance(e, discord.Forbidden):
            return False
        if isinstance(e, discord.HTTPException):
            return True
        return True

Cog = rps

def setup(client):
    client.add_cog(rps(client))
