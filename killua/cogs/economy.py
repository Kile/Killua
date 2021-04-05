import discord
from discord.ext import commands
import pymongo
from pymongo import MongoClient
from killua.functions import custom_cooldown, blcheck
import json
from json import loads
import typing
from datetime import datetime, timedelta
from random import randint
import random
import asyncio
from killua.cogs.cards import User


with open('config.json', 'r') as config_file:
    config = json.loads(config_file.read())

cluster = MongoClient(config['mongodb'])
db = cluster['Killua']
teams = db['teams']
server = db['guilds']

numbers = {
    1: '1️⃣',
    2: '2️⃣',
    3: '3️⃣',
    4: '4️⃣',
    5: '5️⃣',
    6: '6️⃣',
    7: '7️⃣',
    8: '8️⃣',
    9: '9️⃣'
}

class Economy(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(aliases=['server'])
    @custom_cooldown(6)
    async def guild(self, ctx):
        #h Displays infos about the current guild
        #u guild
        if blcheck(ctx.author.id) is True:
            return
        return await ctx.send('Command currently under maintenance')
        points = 0
        top = {
            'user': '',
            'points': 0
        }
        for member in ctx.guild.members: #On big servers I am making 13k requests to my db here which takes a bit, gotta think of a better solution
            user = teams.find_one({'id': member.id})
            if user is None:
                pass
            else:
                points = points + (user['points'] or 0)
                if user['points'] > top['points']:
                    top = {
                        'user': member,
                        'points': user['points']
                    }

        guild = server.find_one({'id': ctx.guild.id})
        if not guild is None:
            badges = '\n'.join(guild['badges'])

        embed = discord.Embed.from_dict({
            'title': f'Information about {ctx.guild.name}',
            'description': f'{ctx.guild.id}\n\n**Owner**\n{ctx.guild.owner}\n\n**Killua Badges**\n{badges or "No badges"}\n\n**Combined Jenny**\n{points}\n\n**Richest member**\n{top["user"] or "-"} with {top["points"] or "-"} points\n\n**Server created at**\n{(ctx.guild.created_at).strftime("%b %d %Y %H:%M:%S")}\n\n**Members**\n{ctx.guild.member_count}',
            'thumbnail': {'url': str(ctx.guild.icon_url)},
            'color': 0x1400ff
        })
        await ctx.send(embed=embed)

    @commands.command()
    @custom_cooldown(6)
    async def profile(self, ctx,user: typing.Union[discord.Member, int]=None):
        #h Get infos about a certain discord user with ID or mention
        #t Around 2 hours
        #u profile <user(optional)>
        if blcheck(ctx.author.id) is True:
            return
        if user is None:
            embed = getmember(ctx.author)
            return await ctx.send(embed=embed)
        else: 
            if isinstance(user, discord.Member):
                embed = getmember(user)
                return await ctx.send(embed=embed)
            else:
                try:
                    newuser = await self.client.fetch_user(user)
                    embed = getmember(newuser)
                    return await ctx.send(embed=embed)
                except Exception as e:
                    await ctx.send(f'```diff\n-{e}\n```')

    @commands.command(aliases=['bal', 'balance', 'points'])
    async def jenny(self, ctx, user: typing.Union[discord.User, int]=None):
        #h Gives you a users balance
        #u balance <user(optional)>
        if blcheck(ctx.author.id) is True:
            return
        
        if not user:
            user_id = ctx.author.id
        if isinstance(user, discord.User):
            user_id = user.id
        elif user:
            user_id = user
        real_user = User(ctx.author.id)

        return await ctx.send(f'{user or ctx.author}\'s balance is {real_user.jenny} Jenny')
        

    @commands.command()
    async def daily(self, ctx):
	    if blcheck(ctx.author.id) is True:
		return
	    #c I didn't know a daily command was that complicated
	    #t several hours
            #h Claim your daily point swith this command!
            #u daily
	    now = datetime.today()
	    later = datetime.now()+timedelta(hours=24)
	    user = User(ctx.author.id)
	    daily = randint(50, 100)

	    
	    if str(user.daily_cooldown) < str(now):

	        teams.update_many({'id': ctx.author.id},{'$set':{'cooldowndaily': later,'points': user.jenny + daily}}, upsert=True)
	        await ctx.send(f'You claimed your {daily} daily Jenny and hold now on to {int(user.jenny) + int(daily)}')
	    else:
	        cd = user.daily_cooldown -datetime.now()
	        cooldown = f'{int((cd.seconds/60)/60)} hours, {int(cd.seconds/60)-(int((cd.seconds/60)/60)*60)} minutes and {int(cd.seconds)-(int(cd.seconds/60)*60)} seconds'
	        await ctx.send(f'You can claim your daily Jenny the next time in {cooldown}')


    @commands.command(aliases=['ghosthunter'])
    @custom_cooldown(240)
    async def gh(self, ctx):
        #h Catch the ghosts fast enough! The faster the more points you get! This command is restricted to premium guilds as it is not fully developed
        #u gh
        guild = server.find_one({'id': ctx.guild.id})
        if guild is None or not 'partner' in guild['badges'] and not 'premium' in guild['badges']:
            return await ctx.send('Beta commands are a premium feature')

        data = teams.find_one({'id': ctx.author.id})
        if data is None:
            return await ctx.send('You need to be in the databse before playing a game, use `k!daily`')
        
        m = await ctx.send('Ready to play?')
        await m.add_reaction('\U00002705')

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '✅' and reaction.message.id == m.id

        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=60, check=check)
        except asyncio.TimeoutError:
            await m.remove_reaction('\U00002705', ctx.me)
            await ctx.send('I guess not')
        else:
            later = datetime.now()+timedelta(seconds=120)
            slots = ['o','o','o','o','o','o','o','o','o']

            embed = embedgenerator(slots)
            msg = await ctx.send(embed=embed)
            await addemojis(msg)

            score:int = await game(self, ctx, msg, 0, later)
            points = int(data['points'])
            teams.update_many({'id': ctx.author.id},{'$set':{'points': points+score}}, upsert=True)

            embed = discord.Embed.from_dict({
                'title': f'Results 🏆',
                'description': f'''-------------------------------------
Jenny added to your account: {score or 0}
Balance: {points+score}
-------------------------------------''',
                'color': 0x1400ff
            })
            await msg.edit(embed=embed)
            

'''async function game
Input:
self: because it is outside of a cog
ctx: to be able to use ctx.send()
msg (discord.Message): the message on which the game runs, used to edit it's content
score (int): to keep track of the score so far
later: to check if the game goes on for longer than 2 min

Returns:
s (int): resembeling the total game score

Purpose:
Calling itself until the game is over, making a user able to play and calculating their points
'''

async def game(self, ctx, msg:discord.Message, score:int, later):
    # If the time is up it will return the final score
    if later < datetime.now():
        return score
    slots = ['o','o','o','o','o','o','o','o','o']

    await msg.edit(embed=embedgenerator(slots))
    # Waits 5-20 seconds until a ghost spawns
    await asyncio.sleep(randint(5, 20))
    # Decides where the ghost is going to spawn
    ghost = randint(1,9)
    slots[ghost-1] = '<:ghosty:768253382665699329>'
    before = datetime.now()
    # Edits the ghost in 
    await msg.edit(embed=embedgenerator(slots))

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == numbers[ghost] and reaction.message.id == msg.id

    try:
        # 5 seconds to catch the ghost
        reaction, user = await self.client.wait_for('reaction_add', timeout=5, check=check)
    except asyncio.TimeoutError:
        # Gives you no points if you miss the ghost
        await ctx.send('Sadly too late...', delete_after=2)
        await asyncio.sleep(2)
        s:int = await game(self, ctx, msg, score, later)
        return s
    else:
        # Calculates the points based on how fast you were
        afterwards = datetime.now()
        timetaken = afterwards-before
        points = int((5-timetaken.seconds)*10)
        # Marks the ghost as hit
        slots[ghost-1] = ':x:'
        await msg.edit(embed=embedgenerator(slots))
        await asyncio.sleep(2)
        try:
            # If permission, removes the authors reaction
            await msg.remove_reaction(numbers[ghost], ctx.author)
        except:
            pass
        # Calls itself
        s:int = await game(self, ctx, msg, score+(points or 0), later)
        return s

'''function embedgenerator
input:
slots (list): Gives the embedgenerator the list where the ghost is in one of the spots

returns:
embed: a discord embed

Purpose:
Making the game work with just a list with 9 items
'''

def embedgenerator(slots:list):
    embed = discord.Embed.from_dict({
        'title': f'Catch the ghost',
        'description': f'''
        ╭ 1 ::: 2 ::: 3 ::: 4 ::: 5 ::: 6 ::: 7 ::: 8 ::: 9╮
        
┊ {' ::: '.join(slots)}    ┊

╰ -------------------------------------╯''',
        'color': 0x1400ff
        })
    return embed

'''async function addemojis
Input:
msg (discord.Message): the messages reactions should be added to

Returns:
Nothing

Purpose:
After my knowledge dpy doesn't have a add_reactions so I have to have 9 lines for 9 reactions,
to make it less messy I made it into a function
'''

async def addemojis(msg:discord.Message):
    await msg.add_reaction('1\N{variation selector-16}\N{combining enclosing keycap}')
    await msg.add_reaction('2\N{variation selector-16}\N{combining enclosing keycap}')
    await msg.add_reaction('3\N{variation selector-16}\N{combining enclosing keycap}')
    await msg.add_reaction('4\N{variation selector-16}\N{combining enclosing keycap}')
    await msg.add_reaction('5\N{variation selector-16}\N{combining enclosing keycap}')
    await msg.add_reaction('6\N{variation selector-16}\N{combining enclosing keycap}')
    await msg.add_reaction('7\N{variation selector-16}\N{combining enclosing keycap}')
    await msg.add_reaction('8\N{variation selector-16}\N{combining enclosing keycap}')
    await msg.add_reaction('9\N{variation selector-16}\N{combining enclosing keycap}')
    return 


Cog = Economy

'''function getuser
Input: 
user (discord.User): the user to get info about and return it

Returns:
embed: An embed with the users information

Purpose:
To have a function handle getting infos about a user for less messy code
'''

def getmember(user: discord.Member):
    av = user.avatar_url
    id = user.id 
    joined = (user.created_at).strftime("%b %d %Y %H:%M:%S")
    
    info = teams.find_one({'id': user.id})
    cooldown = ''

    f = []
    for flag in user.public_flags:
        if flag[1] is True:
            if flag[0] == 'hypesquad':
                f.append('hhypesquad')
            elif flag[0] == 'verified_bot':
                f.append('vb')
            else:
                f.append(flag[0])
    
    flags = (' '.join(f)).replace('staff', '<:DiscordStaff:788508648245952522>').replace('partner', '<a:PartnerBadgeShining:788508883144015892>').replace('hhypesquad', '<a:HypesquadShiny:788508580101488640>').replace('bug_hunter', '<:BugHunter:788508715241963570>').replace('hypesquad_bravery', '<:BraveryLogo:788509874085691415>').replace('hypesquad_brilliance', '<:BrillianceLogo:788509874517442590>').replace('hypesquad_balance', '<:BalanceLogo:788509874245074989>').replace('early_supporter', '<:EarlySupporter:788509000005451776>').replace('team_user', 'Contact Kile#0606').replace('system', 'Contact Kile#0606').replace('bug_hunter_level_2', '<:BugHunterGold:788508764339830805>').replace('vb', '<:verifiedBot:788508495846047765>').replace('verified_bot_developer', '<:EarlyBotDev:788508428779388940>')
    
    if info is None:
        points = 0
        badges = 'No badges'
        cooldown = 'Never claimed `k!daily`before'

    else:
        points = info['points']
        badges = ', '.join(info['badges']).replace('one_star_hunter', '<:badge_one_star_hunter:788935576836374548>').replace('two_star_hunter', '<:badge_double_star_hunter:788935576120066048>').replace('triple_star_hunter', '<:badge_triple_star_hunter:788935576925372417>')
        if str(datetime.now()) > str(info['cooldowndaily']):
            cooldown = 'Ready to claim!'
        else:
            cd = info['cooldowndaily'] -datetime.now()
            cooldown = f'{int((cd.seconds/60)/60)} hours, {int(cd.seconds/60)-(int((cd.seconds/60)/60)*60)} minutes and {int(cd.seconds)-(int(cd.seconds/60)*60)} seconds'
    embed = discord.Embed.from_dict({
            'title': f'Information about {user}',
            'description': f'{id}\n{flags}\n\n**Killua Badges**\n{badges or "No badges"}\n\n**Jenny**\n{points}\n\n**Account created at**\n{joined}\n\n**`k!daily` cooldown**\n{cooldown or "Never claimed `k!daily` before"}',
            'thumbnail': {'url': str(av)},
            'color': 0x1400ff
        })
    return embed

def setup(client):
  client.add_cog(Economy(client))

