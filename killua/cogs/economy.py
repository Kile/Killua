import discord
from discord.ext import commands
import pymongo
from pymongo import MongoClient
from killua.functions import custom_cooldown, blcheck
import json
from json import loads
import typing


with open('config.json', 'r') as config_file:
    config = json.loads(config_file.read())

cluster = MongoClient(config['mongodb'])
db = cluster['Killua']
collection = db['teams']
top = db['teampoints']
server = db['guilds']

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
		    await ctx.send(f'You can claim your points the next time in {cooldown}')    
	    else:
        
		    if str(result['cooldowndaily']) < str(now):
 
			    teams.update_many({'id': ctx.author.id},{'$set':{'cooldowndaily': later,'points': result['points'] + daily}}, upsert=True)

			    await ctx.send(f'You claimed your {daily} daily points and hold now on to {int(result["points"]) + int(daily)}')
		    else:

			    cd = result['cooldowndaily'] -datetime.now()
			    cooldown = f'{int((cd.seconds/60)/60)} hours, {int(cd.seconds/60)-(int((cd.seconds/60)/60)*60)} minutes and {int(cd.seconds)-(int(cd.seconds/60)*60)} seconds'
			    await ctx.send(f'You can claim your points the next time in {cooldown}')




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
            else:
                f.append(flag[0])
    
    flags = (' '.join(f)).replace('staff', '<:DiscordStaff:788508648245952522>').replace('partner', '<a:PartnerBadgeShining:788508883144015892>').replace('hhypesquad', '<a:HypesquadShiny:788508580101488640>').replace('bug_hunter', '<:BugHunter:788508715241963570>').replace('hypesquad_bravery', '<:BraveryLogo:788509874085691415>').replace('hypesquad_brilliance', '<:BrillianceLogo:788509874517442590>').replace('hypesquad_balance', '<:BalanceLogo:788509874245074989>').replace('early_supporter', '<:EarlySupporter:788509000005451776>').replace('team_user', 'Contact Kile#0606').replace('system', 'Contact Kile#0606').replace('bug_hunter_level_2', '<:BugHunterGold:788508764339830805>').replace('verified_bot', '<:verifiedBot:788508495846047765>').replace('early_bot_developer', '<:EarlyBotDev:788508428779388940>')
    
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

