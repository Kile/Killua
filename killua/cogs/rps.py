import discord
from discord.ext import commands
import random
import asyncio
from killua.functions import blcheck, check
from killua.classes import User
from killua.constants import teams

class Rps(commands.Cog):

    def __init__(self, client):
        self.client = client
    
    @check(60)
    @commands.command()
    async def rps(self, ctx, member: discord.Member, points: int=None):
        #h Play Rock Paper Scissors with your friends! You can play investing Jenny or just for fun.
        #u rps <user> <points(optional)
        
        if member.id == ctx.author.id:
            return await ctx.send('Baka! You can\'t play against yourself')
        
        if not member.bot:
            opponent = User(member.id)
        elif member.bot and member != ctx.me:
            return await ctx.send('Beep-boop, if you wanna play against a bot, play against me!')
        
        p2 = opponent.jenny if member != ctx.me else False

        user = User(ctx.author.id)

        p1 = user.jenny
    
        if points:
            if points <= 0 or points > 100:
                return await ctx.send(f'You can only play using 1-100 Jenny')

            if p1 < points:
                return await ctx.send(f'You do not have enough Jenny for that. Your current balance is `{p1}`')
            if not p2 is False and p2 < points:
                return await ctx.send(f'Your opponent does not have enough Jenny for that. Their current balance is `{p2}`')
    
        if member == ctx.me:
            await ctx.author.send('You chose to play Rock Paper Scissors against me, what\'s your choice? **[Rock] [Paper] [Scissors]**')

            embed = discord.Embed.from_dict({
                'title': f'{ctx.author.name} against Killua: **Rock... Paper... Scissors!**',
                'image': {'url': 'https://media1.tenor.com/images/dc503adb8a708854089051c02112c465/tenor.gif?itemid=5264587'},
                'color': 0x1400ff
            })

            await ctx.send(embed= embed)
        
            def check(m):
                return (m.content.lower() == 'scissors' or m.content.lower() == 'paper' or m.content.lower() == 'rock') and m.author == ctx.author
                    
            msg = await self.client.wait_for('message', check=check, timeout=60) 
            c2 = random.choice(['paper', 'rock', 'scissors'])
            winlose = await rpsf(msg.content, c2)
            await evaluate(ctx, winlose, msg.content.lower(), c2, ctx.author, ctx.me, points)
        else:
            if await dmcheck(ctx.author) is False:
                return await ctx.send(f'You need to open your dm to Killua to play {ctx.author.mention}')
            if await dmcheck(member) is False:
                return await ctx.send(f'{member.name} needs to open their dms to Killua to play')
            if blcheck(member.id) is True:
                return await ctx.send('You can\'t play against someone blacklisted')

            await ctx.send(f'{ctx.author.mention} challanged {member.mention} to a game of Rock Paper Scissors! Will **{member.name}** accept the challange?\n **[y/n]**')
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

'''function rpsemote
Input: 
choice: the choice a user made

Returns:
the fitting emoji

Purpose: Display the users choices as emojis
'''
    
def rpsemote(choice):
    if choice == 'paper':
        return '📄'
    if choice == 'rock':
        return '🗿'
    if choice == 'scissors':
        return '✂️'

'''async function rpsf
Input:
choice1: The choice of the first player
choice2: The choice of the second player

Returns: 
Either 1, 2 or 3; 1 stands for choice1 > choice2, 2 for choice1 = choice2 and 3 for choice1 < choice2

Purpose:
Evaluating who won
'''

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

'''async function evaluate
Input:
ctx: to get author and ctx.me
winlose (int): the result who won and lost
choice1: Player one's choice
choice2: Player two's choice
player1 (discord.User): a discord.User object of player 1
player2 (discord.User): a discord.User object of player 2
points (int); amount of Jenny the game is about

Returns:
Sending an embed

Purpose:
To evaluate the outcome, inform the players and handle the points
'''

async def evaluate(ctx, winlose:int, choice1, choice2, player1:discord.User, player2:discord.User, points:int=None):
    p1 = User(player1.id)
    p2 = User(player2.id)
    if winlose == 1:
        if points:
            p1.add_jenny(points)
            if player2 != ctx.me:
                p2.remove_jenny(points)
            return await ctx.send(f'{rpsemote(choice1)} > {rpsemote(choice2)}: {player1.mention} won against {player2.mention} winning {points} Jenny which adds to a total of {p1.jenny+ points}')
        else:
            return await ctx.send(f'{rpsemote(choice1)} > {rpsemote(choice2)}: {player1.mention} won against {player2.mention}')
    if winlose == 2:
        return await ctx.send(f'{rpsemote(choice1)} = {rpsemote(choice2)}: {player1.mention} tied against {player2.mention}')
    if winlose == 3:
        if points:
            p1.remove_jenny(points)
            if player2 != ctx.me:
                p2.add_jenny(points)
            return await ctx.send(f'{rpsemote(choice1)} < {rpsemote(choice2)}: {player1.mention} lost against {player2.mention} losing {points} Jenny which leaves them a total of {p1.jenny- points}')
        else:
            return await ctx.send(f'{rpsemote(choice1)} < {rpsemote(choice2)}: {player1.mention} lost against {player2.mention}')
       
'''async function dmcheck
Input:
user (discord.User): the user the check will be used on

Returns:
(boolean): if the user has their dms open or not

Purpose:
Checks if a users dms are open by sending them an empty message and either recieving an error for can't send
an empty message or for not allowed; dms closed
'''

async def dmcheck(user:discord.User):
    try:
        await user.send('')
    except Exception as e:
        if isinstance(e, discord.Forbidden):
            return False
        if isinstance(e, discord.HTTPException):
            return True
        return True

Cog = Rps

def setup(client):
    client.add_cog(Rps(client))