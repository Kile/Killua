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

class economy(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command()
    @custom_cooldown(6)
    async def profile(self, ctx,user: typing.Union[discord.User, int]=None):
        #h Get infos about a certain discord user with ID or mention
        #t Around 2 hours
        if blcheck(ctx.author.id) is True:
            return
        if user is None:
            embed = getuser(ctx.author)
            return await ctx.send(embed=embed)
        else: 
            if isinstance(user, discord.User):
                embed = getuser(user)
                return await ctx.send(embed=embed)
            else:
                try:
                    newuser = await self.client.fetch_user(user)
                    embed = getuser(newuser)
                    return await ctx.send(embed=embed)
                except Exception as e:
                    await ctx.send(f'```diff\n-{e}\n```')

    @commands.command()
    async def daily(self, ctx):
	    if blcheck(ctx.author.id) is True:
		    return
	    #c I didn't know a daily command was that complicated
	    #t several hours
        #h Claim your daily point swith this command!
	    now = datetime.today()
	    later = datetime.now()+timedelta(hours=24)
	    result = teams.find_one({'id': ctx.author.id})
	    daily = randint(50, 100)

	    if result is None:
		    teams.insert_one({'id': ctx.author.id, 'points': daily, 'badges': [], 'cooldowndaily': later})
		    await ctx.send(f'You claimed your {daily} daily points and hold now on to {daily}')   
	    else:
		    if str(result['cooldowndaily']) < str(now):
 
			    teams.update_many({'id': ctx.author.id},{'$set':{'cooldowndaily': later,'points': result['points'] + daily}}, upsert=True)
			    await ctx.send(f'You claimed your {daily} daily points and hold now on to {int(result["points"]) + int(daily)}')
		    else:

			    cd = result['cooldowndaily'] -datetime.now()
			    cooldown = f'{int((cd.seconds/60)/60)} hours, {int(cd.seconds/60)-(int((cd.seconds/60)/60)*60)} minutes and {int(cd.seconds)-(int(cd.seconds/60)*60)} seconds'
			    await ctx.send(f'You can claim your points the next time in {cooldown}')

    @commands.command()
    async def give(self, ctx, user:discord.User, amount:int=None):
        if blcheck(ctx.author.id) is True:
            return
        if amount is None:
            amount = 100
        
        balance = teams.find_one({'id': ctx.author.id})
        if balance is None:
            return await ctx.send('You have not been registered in Killua\'s economy system. Do so with `k!daily`')
        if balance['points'] < amount:
            return await ctx.send(f'Nice of you to try and send {user.name} some points, sadly you don\'t have enough points for that. Your current balance is `{balance}`')

        otherguy = teams.find_one({'id': user.id})
        if otherguy is None:
            return ctx.send('The person you want to give points to is not yet registered. Tell them to do so with `k!daily`')

        teams.update_one({'id': ctx.author.id},{'$set':{'points': balance['points'] - amount}}, upsert=True)
        teams.update_one({'id': user.id},{'$set':{'points': otherguy['points'] + amount}}, upsert=True)
        await ctx.send(f'You gave {user} {amount} points! How very nice :3 Their new balance is `{otherguy["points"]+amount}`, yours `{balance["points"] - amount}`')

   @commands.command(aliases=['ghosthunter'])
    @custom_cooldown(240)
    async def gh(self, ctx):
        #h Catch the ghosts fast enough! The faster the more points you get! This command is restricted to premium guilds as it is not fully developed
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
Points added to your account: {score or 0}
Balance: {points+score}
-------------------------------------''',
                'color': 0xc21a1a
            })
            await msg.edit(embed=embed)
            



async def game(self, ctx, msg:discord.Message, score:int, later):

    if later < datetime.now():
        return score
    slots = ['o','o','o','o','o','o','o','o','o']

    await msg.edit(embed=embedgenerator(slots))
    await asyncio.sleep(randint(5, 20))
    ghost = randint(1,9)
    slots[ghost-1] = '<:ghosty:768253382665699329>'

    before = datetime.now()

    await msg.edit(embed=embedgenerator(slots))

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == numbers[ghost] and reaction.message.id == msg.id

    try:
        reaction, user = await self.client.wait_for('reaction_add', timeout=5, check=check)
    except asyncio.TimeoutError:
        await ctx.send('Sadly too late...', delete_after=2)
        await asyncio.sleep(2)
        s:int = await game(self, ctx, msg, score, later)
        return s
    else:
        afterwards = datetime.now()
        timetaken = afterwards-before
        points = int((5-timetaken.seconds)*15)
        slots[ghost-1] = ':x:'
        await msg.edit(embed=embedgenerator(slots))
        await asyncio.sleep(2)
        try:
            await msg.remove_reaction(numbers[ghost], ctx.author)
        except:
            pass
        s:int = await game(self, ctx, msg, score+(points or 0), later)
        return s

def embedgenerator(slots:list):
    embed = discord.Embed.from_dict({
        'title': f'Catch the ghost',
        'description': f'''
        ╭ 1 ::: 2 ::: 3 ::: 4 ::: 5 ::: 6 ::: 7 ::: 8 ::: 9╮
        
┊ {' ::: '.join(slots)}    ┊

╰ -------------------------------------╯''',
        'color': 0xc21a1a
        })
    return embed

sync def addemojis(msg:discord.Message):
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


Cog = economy

def getuser(user: discord.User):
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
    
    flags = (' '.join(f)).replace('staff', '<:DiscordStaff:788508648245952522>').replace('partner', '<a:PartnerBadgeShining:788508883144015892>').replace('hhypesquad', '<a:HypesquadShiny:788508580101488640>').replace('bug_hunter', '<:BugHunter:788508715241963570>').replace('hypesquad_bravery', '<:BraveryLogo:788509874085691415>').replace('hypesquad_brilliance', '<:BrillianceLogo:788509874517442590>').replace('hypesquad_balance', '<:BalanceLogo:788509874245074989>').replace('early_supporter', '<:EarlySupporter:788509000005451776>').replace('team_user', 'Contact Kile#0606').replace('system', 'Contact Kile#0606').replace('bug_hunter_level_2', '<:BugHunterGold:788508764339830805>').replace('vb', '<:verifiedBot:788508495846047765>').replace('early_bot_developer', '<:EarlyBotDev:788508428779388940>')
    
    if info is None:
        points = 0
        badges = 'No badges'
        cooldown = 'Never claimed `k!daily`before'

    else:
        points = info['points']
        badges = ' '.join(info['badges'])
        if str(datetime.now()) > str(info['cooldowndaily']):
            cooldown = 'Ready to claim!'
        else:
            cd = info['cooldowndaily'] -datetime.now()
            cooldown = f'{int((cd.seconds/60)/60)} hours, {int(cd.seconds/60)-(int((cd.seconds/60)/60)*60)} minutes and {int(cd.seconds)-(int(cd.seconds/60)*60)} seconds'
    embed = discord.Embed.from_dict({
            'title': f'Information about {user}',
            'description': f'{id}\n{flags}\n\n**Killua Badges**\n{badges or "No badges"}\n\n**Points**\n{points}\n\n**Account created at**\n{joined}\n\n**`k!daily` cooldown**\n{cooldown or "Never claimed `k!daily`before"}',
            'thumbnail': {'url': str(av)},
            'color': 0x1400ff
        })
    return embed

def setup(client):
  client.add_cog(economy(client))

