from discord.ext import commands
import io
import aiohttp
import time
import discord
import random
import json
from random import randint
from datetime import datetime, date, timedelta
from discord.ext import tasks
import pymongo
from pymongo import MongoClient
from pprint import pprint
import asyncio
import inspect
from discord.utils import find
from discord import client
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from numpy import *
from matplotlib.pyplot import *
import matplotlib.pyplot as plt
import numpy as np
import numexpr as ne



cluster = MongoClient('mongodb+srv://Kile:Kile2-#2@cluster0.q9qss.mongodb.net/teams?retryWrites=true&w=majority')
db = cluster['Killua']
collection = db['teams']
top =db['teampoints']
server = db['guilds']



def get_prefix(bot, message):
    y = server.find({'id': message.guild.id})
    for x in y:
        prefix = x['prefix']
        return prefix
    return 'k!'
    
    

bot = commands.Bot(command_prefix= get_prefix, description="default prefix", case_insensitive=True, intents = discord.Intents.default())
bot.remove_command('help')
cogs = ['devstuff', 'prefixes', 'smallcommands', 'rps', 'api', 'events', 'help']

for cog in cogs:
    bot.load_extension(f"cogs.{cog}")


huggif = [f'https://i.pinimg.com/originals/66/9b/67/669b67ae57452f7afbbe5252b6230f85.gif', f'https://i.pinimg.com/originals/70/83/0d/70830dfba718d62e7af95e74955867ac.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/756945463432839168/image0.gif', 'https://cdn.discordapp.com/attachments/756945125568938045/756945308381872168/image0.gif', 'https://cdn.discordapp.com/attachments/756945125568938045/756945151191941251/image0.gif', 'https://pbs.twimg.com/media/Dl4PPE4UUAAsb7c.jpg', 'https://encrypted-tbn0.gstatic.com/images?q=tbn%3AANd9GcSJgTjRyQW3NzmDzlvskIS7GMjlFpyS7yt_SQ&usqp=CAU', 'https://static.zerochan.net/Hunter.x.Hunter.full.1426317.jpg', 'https://encrypted-tbn0.gstatic.com/images?q=tbn%3AANd9GcQJjVWplBdqrasz8Fh-7nDkxRjnnNBqk0bZlQ&usqp=CAU', 'https://i.pinimg.com/originals/75/2e/0a/752e0a5f813400dfebe322fc8b0ad0ae.jpg', 'https://thumbs.gfycat.com/IllfatedComfortableAplomadofalcon-small.gif', 'https://steamuserimages-a.akamaihd.net/ugc/492403625757327002/9B089509DDCB6D9F8E11446C7F1BC29B9BA57384/', f'https://cdn.discordapp.com/attachments/756945125568938045/758235270524698634/image0.gif', f'https://cdn.discordapp.com/attachments/756945125568938045/758236571974762547/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758236721216749638/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758237072975855626/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758237082484473856/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758237352756903936/image0.png', 'https://cdn.discordapp.com/attachments/756945125568938045/758237832954249216/image0.jpg']

        

@bot.command(aliases=['patreon'])
async def support(ctx):
    #c :3
    #t 30 minutes
    embed = discord.Embed.from_dict({
        'title': '**Support Killua**',
        'thumbnail':{
            'url': 'https://cdn.discordapp.com/avatars/758031913788375090/e44c0de4678c544e051be22e74bc502d.png?size=1024'},
        'description': 'Hey, do you have too much money? I have a solution for that! I now have a Patreon account where you can donate to support me and get special stuff, helping with building Killua. Not that I expect anyone to do this, but I have it set up now.\n\n https://www.patreon.com/KileAlkuri',
        'color': 0x1400ff
    })
    await ctx.send(embed=embed)


@bot.command()
async def function(ctx, *, function):
    #t 1-2days (wtf)
    #r ID: 606162661184372736
    #c Could break Killua atm so restricted
    if ctx.author.id == 606162661184372736:
        try:
            x = np.linspace(-5,5,100)
            y = ne.evaluate(function)

            # setting the axes at the centre
            fig = plt.figure()
            ax = fig.add_subplot(1, 1, 1)
            ax.spines['left'].set_position('center')
            ax.spines['bottom'].set_position('center')
            ax.spines['right'].set_color('none')
            ax.spines['top'].set_color('none')
            ax.xaxis.set_ticks_position('bottom')
            ax.yaxis.set_ticks_position('left')

            # plot the function
            plt.plot(x,y, 'g')
            plt.title(str(function))
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
    
            graph = discord.File(buf, filename= 'graph.png')
    

    
            await ctx.send(file=graph)
        except Exception as e:
            await ctx.send(e)


@bot.command()
async def info(ctx):
    embed = discord.Embed(
        title = 'Info',
        description = ' This is Killua, Kile\'s bot version 0.4.1, the first features simply include ~this command, `k!ping`, `k!hi`, `k!invite`, `k!hug <user>` and `k!topic`, relatively self-explanatory, also a team mode already implemented but not yet finsihed\n I hope to be adding a lot more soon while I figure Python out on the go\n\n **Last time restarted:**\n '+ str(bot.startup_datetime.strftime('%Y-%m-%d-%H:%M:%S')),
        color = 0x1400ff
    )
    await ctx.send(embed=embed) 
    #c help command
    #t 20 minutes, constantly updating

@bot.command()
async def daily(ctx):
    #c I didn't know a daily command was that complicated
    #t one hour
    
    now = datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
    results = collection.find({'id': ctx.author.id})
    for result in results:
        nexttime = result['cooldowndaily']
        balance = result['points']
        team = result['team']
    results = top.find({'team': team})
    for result in results:
        points = result['points']
    if str(nexttime) < str(now):
        later = (datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d-%H:%M:%S')
        daily = randint(50, 100)
        collection.update_many({'id': ctx.author.id},{'$set':{'cooldowndaily':later, 'points': balance + daily}}, upsert=True)
        top.update_one({'team': team}, {'$set':{'points': points + daily}})
        await ctx.send(f'You claimed your {daily} daily points and hold now on to {int(balance) + int(daily)}')
    else:
        await ctx.send(f'You can claim your points the next time: {nexttime}')
    

@bot.command()
async def invite(ctx):
    #t 5 minutes
    embed = discord.Embed(
        title = 'Invite',
        description = 'Invite the bot to your server **today** [here](https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=1342531648)',
        color = 0x1400ff
    )
    await ctx.send(embed=embed) 

@bot.command()
async def guilds(ctx):
    #r user ID: 606162661184372736 or 383790610727043085
    #t 15 minutes
    if ctx.author.id == 606162661184372736 or ctx.author.id == 383790610727043085:
        embed = discord.Embed(
            title = 'Guilds',
            description = '\n'.join([guild.name for guild in bot.guilds]),
            color = 0x1400ff
        )
        await ctx.send(embed=embed) 

@bot.command()
async def hug(ctx,  *, content=None):
    #c Best hug command out there
    #t 1-3 hours
    if ctx.message.mentions:
        if ctx.author == ctx.message.mentions[0]:
            return await ctx.send(f'Someone hug {ctx.author.name}!')
        
        hugtext = [f'**{ctx.author.name}** hugs **{ctx.message.mentions[0].name}** as strong as they can', f'**{ctx.author.name}** hugs **{ctx.message.mentions[0].name}** and makes sure to not let go', f'**{ctx.author.name}** gives **{ctx.message.mentions[0].name}** the longest hug they have ever seen', f'**{ctx.author.name}** cuddles **{ctx.message.mentions[0].name}**', f'**{ctx.author.name}** uses **{ctx.message.mentions[0].name}** as a teddybear', f'**{ctx.author.name}** hugs **{ctx.message.mentions[0].name}** until all their worries are gone and 5 minutes longer',f'**{ctx.author.name}** clones themself and together they hug **{ctx.message.mentions[0].name}**', f'**{ctx.author.name}** jumps in **{ctx.message.mentions[0].name}**\'s arms', f'**{ctx.author.name}** gives **{ctx.message.mentions[0].name}** a bearhug', f'**{ctx.author.name}** finds a lamp with a Jinn and gets a wish. So they wish to hug **{ctx.message.mentions[0].name}**', f'**{ctx.author.name}** asks **{ctx.message.mentions[0].name}** for motivation and gets a hug']
        embed = discord.Embed.from_dict({
            'title': random.choice(hugtext),
            'image':{
                'url': random.choice(huggif)
            },
            'color': 0x1400ff
            })
        await ctx.send(embed=embed)
    else:
        await ctx.send('Invalid user.. Should- I hug you?')
        def check(m):
            return m.content.lower() == 'yes' and m.author == ctx.author

        msg = await bot.wait_for('message', check=check, timeout=60) 
        hugtextself = [f'**Killua** hugs **{ctx.author.name}** as strong as they can', f'**Killua** hugs **{ctx.author.name}** and makes sure to not let go', f'**Killua** gives **{ctx.author.name}** the longest hug they have ever seen', f'**Killua** cuddles **{ctx.author.name}**', f'**Killua** uses **{ctx.author.name}** as a teddybear', f'**Killua** hugs **{ctx.author.name}** until all their worries are gone and 5 minutes longer',f'**Killua** clones themself and together they hug **{ctx.author.name}**', f'**Killua** jumps in **{ctx.author.name}**\'s arms', f'**Killua** gives **{ctx.author.name}** a bearhug', f'**Killua** finds a lamp with a Jinn and gets a wish. So they wish to hug **{ctx.author.name}**', f'**Killua** asks **{ctx.author.name}** for motivation and gets a hug']
        embed = discord.Embed.from_dict({
            'title': random.choice(hugtextself),
            'image':{
                'url': random.choice(huggif)
            },
            'color': 0x1400ff
            })
        await ctx.send(embed=embed) 



@bot.group(name='team', invoke_without_command=True)
async def team(ctx):
    pass

@bot.command()
async def points(ctx):
    #t 5 minutes
    results = collection.find({'id': ctx.author.id})
    for result in results:
        p1 = result['points']
    await ctx.send(f'You currently hold on to {p1} points!')

@team.command(name="killua")
async def killua(ctx):
    pro = await procont('killua')
    if pro <= 0.35:
        points = collection.count_documents({"id": ctx.author.id})
        if points == 0:
            collection.update_many({'id': ctx.author.id},{'$set':{'team':'killua', 'points': 0, 'cooldowndaily': 0, 'cooldown': 0}}, upsert=True)
            await ctx.send("You sucessfully joined the `killua` team!")
        else:
            collection.update_one({'id': ctx.author.id},{'$set':{'team':'killua', 'points': 0}}, upsert=True)
            await ctx.send("You sucessfully joined the `killua` team! Your points from your previous team have been reset")     
    else:
        await ctx.send('The team currently has too many members, please join another team or wait for a spot to get free')

@team.command(name="gon")
async def gon(ctx):
    pro = await procont('gon')
    if pro <= 0.35:
        points = collection.count_documents({"id": ctx.author.id})
        if points == 0:
            collection.update_many({'id': ctx.author.id},{'$set':{'team':'gon', 'points': 0, 'cooldowndaily': 0, 'cooldown': 0}}, upsert=True)
            await ctx.send("You sucessfully joined the `gon` team!")
        else:
            collection.update_one({'id': ctx.author.id},{'$set':{'team':'gon', 'points': 0}}, upsert=True)
            await ctx.send("You sucessfully joined the `gon` team! Your points from your previous team have been reset")
    else:
        await ctx.send('The team currently has too many members, please join another team or wait for a spot to get free')

@team.command(name="kurapika")
async def kurapika(ctx):
    pro = await procont('kurapika')
    if pro <= 0.35:
        points = collection.count_documents({"id": ctx.author.id})
        if points == 0:
            collection.update_many({'id': ctx.author.id},{'$set':{'team':'kurapika', 'points': 0, 'cooldowndaily': 0, 'cooldown': 0}}, upsert=True)
        
            await ctx.send("You sucessfully joined the `kurapika` team!")
        else:
            collection.update_one({'id': ctx.author.id},{'$set':{'team':'kurapika', 'points': 0}}, upsert=True)
            await ctx.send("You sucessfully joined the `kurapika` team! Your points from your previous team have been reset")
    else:
        await ctx.send('The team currently has too many members, please join another team or wait for a spot to get free')

@team.command(name="leorio")
async def leorio(ctx):
    pro = await procont('leorio')
    if pro <= 0.35:
        points = collection.count_documents({"id": ctx.author.id})
        if points == 0:
            collection.update_many({'id': ctx.author.id},{'$set':{'team':'leorio', 'points': 0, 'cooldowndaily': 0, 'cooldown': 0}}, upsert=True)
            
            
            await ctx.send("You sucessfully joined the `leorio` team!")
        else:
            collection.update_one({'id': ctx.author.id},{'$set':{'team':'leorio', 'points': 0}}, upsert=True)
            await ctx.send("You sucessfully joined the `leorio` team! Your points from your previous team have been reset")
    else:
        await ctx.send('The team currently has too many members, please join another team or wait for a spot to get free')

@team.command(name="current")
async def current(ctx):
    results = collection.find({'id': ctx.author.id})
    for result in results:
        team = result['team']
    await ctx.send(f'You are currently member of the `{team}` team!')



@team.command(name="info")
async def info(ctx, text= None):
    #t 30 minutes
    if text:
        if text == 'Killua':
            embed = discord.Embed.from_dict({
            'title': 'Information about team Killua',
            'description': 'Hi, my name is Killua! I\'ve been trained by my family to be an assasin, long hard training, I\'ve killed lots of people already. When the only thing I want is being friends with Gon... I would be glad to so you in my team fighting by my side for the first place! \n\n Attributes: **power, intelligent, strong, putting friends always first**',
            'thumbnail':{
                'url': 'https://i.pinimg.com/474x/c8/15/e5/c815e5ea92cad30c6a6409dabf0358af.jpg'
            },
            'color': 0x1400ff
            })
            return await ctx.send(embed=embed)
        if text == 'Gon':
            embed = discord.Embed.from_dict({
            'title': 'Information about team Gon',
            'description': 'Hello, I am Gon! I am glad to be here, to have made so many friends on the search for my father and I love making more. I am kind to everyone unless someone hurts one of my friends, then I can get a bit... protective. Let\'s win this thing, together and make new friends on the way! \n\n Attributes: **kind, open hearted, protective**',
            'thumbnail':{
                'url': 'https://giantbomb1.cbsistatic.com/uploads/scale_medium/2/27436/2722697-gon_freecss_2617.jpg'
            },
            'color': 0x43AB15
            })
            return await ctx.send(embed=embed)
        if text == 'Leorio':
            embed = discord.Embed.from_dict({
            'title': 'Information about team Leorio',
            'description': 'Hi my name is Leorio! Originally I was planning to get my license to sell it, because as I say, money rules the world when all I want is being a doctor and able to help peoplle for free.. Then I met friends who helped my get my license and I love to spend time with them! For now I gotta learn for my exams though\n\n Attributes: **smart, money oriented**',
            'thumbnail':{
                'url': 'https://i.pinimg.com/736x/52/0e/b5/520eb54bcfe98466df902ad677d13b8e.jpg'
            },
            'color': 0x0D0293
            })
            return await ctx.send(embed=embed)
        if text == 'Kurapika':
            embed = discord.Embed.from_dict({
            'title': 'Information about team Kurapika',
            'description': 'Hello kind person, my name is Kurapika. I am the last surviving member of the Kurta-clan, the rest has been killed by a group called the Phantom Troupe and I\'ve made it my goal to ill every one of them. But unless I find one I am nice and kind but always searching for them \n\n Attributes: **excellent in cooking, experienced, powerfull, risiking everything**',
            'thumbnail':{
                'url': 'https://i.pinimg.com/originals/27/ca/b9/27cab9588503c762f88e6311751ebddf.jpg'
            },
            'color': 0xE8EB0B  
            })
            return await ctx.send(embed=embed)

        await ctx.send('Not an existing team')
    else:
        teaminfo = '\n'.join([f"{x['_id']}: {x['count']}" for x in list(collection.aggregate([{"$group": {"_id": "$team", "count": {"$sum": 1}}}]))])
        embed = discord.Embed(
            title = '**Teams info**',
            color = 0x00FF80,
            description = f'Introducing team mode!\n 4 teams are available to join\n Once you join a team, you collect points for it to get it on global rank 1!\n\n Join a team with `k!team <team name>`\n Teams: \n\nGon\n Killua\n Kurapika\n Leorio\n\n *For more info about each team and what it resembles, use `k!team info <team name>`*\n\nTeam ratio:\n {teaminfo}'
        )
        embed.set_thumbnail(url='https://imgix.ranker.com/user_node_img/3683/73654539/original/hunter-x-hunter-u47?fm=pjpg&q=80.img')
        await ctx.send(embed=embed)
                              
                              

@bot.command()
async def codeinfo(ctx, content):
    
    
    try:
        func = bot.get_command(content).callback
        code = inspect.getsource(func)
        linecount = code.splitlines()
        time= ''
        restricted = ''
        comment = ''

        for item in linecount:
            firstt, middlet, lastt = item.partition("#t")
            firstr, middler, lastr = item.partition("#r")
            firstc, middlec, lastc = item.partition("#c")
            if lastt == '':
                pass
            else:
                time = lastt
            if lastr == '':
                pass
            else:
                restricted = lastr
            if lastc == '':
                pass
            else:
                comment = lastc

            #c this very code
            #t 1-2 hours
        if restricted == '' or restricted is None or restricted == '")':
            realrestricted = ''
        else:
            realrestricted = f'**Restricted to:** {restricted}'

        embed= discord.Embed.from_dict({
            'title': f'Command **{content}**',
            'color': 0x1400ff,
            'description': f'''**Characters:** {len(code)}
            **Lines:**  {len(linecount)}

            **Time spend on code:** {time or 'No time provided'}
            **Comments:** {comment or 'No comment'}
            
            {realrestricted}'''
            })
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send('Invalid command')
                              
@bot.command()
async def permissions(ctx):
    #t 30 min
    perms = ctx.me.guild_permissions
    permissions = '\n'.join([f"{v} {n}" for n, v in perms])
    prettier = permissions.replace('_', ' ').replace('True', '<:CheckMark:771754620673982484>').replace('False', '<:x_:771754157623214080>')
    embed = discord.Embed.from_dict({
            'title': 'Bot permissions',
            'description': prettier,
            'color': 0x1400ff,
            'thumbnail': {'url': str(ctx.me.avatar_url)}
        })
    await ctx.send(embed=embed)
    
    
async def procont(team):
    amountteam = collection.count_documents({"team": team})
    amounttotal = collection.count_documents({})
    try:
        procentage = amountteam/amounttotal
        return procentage
    except Exception as e:
        return 0

bot.run('NzU2MjA2NjQ2Mzk2NDUyOTc1.X2OeUg.mt0HJ8nW3ADNMGz0xNAwhvsgJ-c')
